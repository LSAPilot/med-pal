"""Section 4: the one narrow entry point the user interface calls.

`Service.ask(...)` wraps `generate.answer_question` with limits, cache, input checks and error handling and returns a plain,
JSON-serialisable `Reply`. The Gradio app (and a later custom frontend, see "Frontend Ausbau") contains no logic of its own.

Privacy: question texts are never logged. Only counters are kept: requests, outcomes, tokens, cost, errors.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import generate
from .chunking import ROOT
from .generate import Answer, Config, Turn
from .limits import AnswerCache, DailyLimit, LimitConfig, VisitorLimit
from .retrieval import Retriever

log = logging.getLogger("regulatory_helper")

EXAMPLES_PATH = ROOT / "data" / "examples.json"

MESSAGES = {
    "visitor_limit": {
        "de": "Du hast das Limit von {n} Fragen pro Stunde erreicht. Bitte versuche es in etwa {m} Minuten erneut. Die Beispielfragen funktionieren weiterhin.",
        "en": "You have reached the limit of {n} questions per hour. Please try again in about {m} minutes. The example questions still work.",
    },
    "daily_limit": {
        "de": "Das Tageslimit für Fragen ist erreicht (schützt das API-Budget dieses Demo-Projekts). Bitte morgen wieder oder die Beispielfragen nutzen.",
        "en": "The daily question limit has been reached (it protects the API budget of this demo). Please come back tomorrow or use the example questions.",
    },
    "too_long": {
        "de": "Die Frage ist zu lang (maximal {n} Zeichen). Bitte kürzer fassen.",
        "en": "The question is too long (at most {n} characters). Please shorten it.",
    },
    "empty": {"de": "Bitte stelle eine Frage.", "en": "Please enter a question."},
    "error": {
        "de": "Die Antwort konnte gerade nicht erzeugt werden. Bitte später erneut versuchen.",
        "en": "The answer could not be generated right now. Please try again later.",
    },
}


@dataclass
class Reply:
    text: str
    status: str = "ok"  # ok | cached | example | visitor_limit | daily_limit | too_long | empty | error
    found: bool = True
    reason: str = ""
    sources: list[dict] = field(default_factory=list)  # id, title, citation, quote, source_url
    search_query: str = ""
    hits: list[dict] = field(default_factory=list)  # rank, id, citation, score, cosine
    best_cosine: float | None = None

    @property
    def counted(self) -> bool:
        """Only real answers (also 'nothing found') become part of the conversation history."""
        return self.status in ("ok", "cached", "example")


def reply_from_answer(ans: Answer) -> Reply:
    return Reply(
        text=ans.text,
        found=ans.found,
        reason=ans.reason,
        sources=[asdict(s) for s in ans.sources],
        search_query=ans.search_query,
        hits=[
            {"rank": h.rank, "id": h.chunk.id, "citation": h.chunk.citation, "score": round(h.score, 4),
             "cosine": None if h.cosine is None else round(h.cosine, 3)}
            for h in ans.hits
        ],
        best_cosine=None if ans.best_cosine is None else round(ans.best_cosine, 3),
    )


@dataclass
class Stats:
    """Counters only. Never question text, never addresses."""

    requests: int = 0
    answered: int = 0
    not_found: int = 0
    cache_hits: int = 0
    limited: int = 0
    errors: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class Service:
    def __init__(
        self,
        cfg: Config | None = None,
        limits: LimitConfig | None = None,
        retriever: Retriever | None = None,
        client=None,
        clock=None,
    ):
        import time

        clock = clock or time.time
        self.cfg = cfg or Config()
        self.limits = limits or LimitConfig.from_env()
        self._retriever = retriever
        self._client = client
        self.daily = DailyLimit(self.limits.daily_limit, clock)
        self.visitors = VisitorLimit(self.limits.visitor_limit, self.limits.visitor_window_s, clock)
        self.cache = AnswerCache(self.limits.cache_size)
        self.stats = Stats()

    # lazy, so the app starts (and examples work) even when the key is missing
    @property
    def retriever(self) -> Retriever:
        if self._retriever is None:
            self._retriever = Retriever.load()
        return self._retriever

    @property
    def client(self):
        if self._client is None:
            self._client = generate.get_client()
        return self._client

    def warm_up(self) -> None:
        """Load index and embedding model at startup so the first visitor does not wait for it."""
        self.retriever.search("warm up", mode="vector", k=1)

    def _msg(self, key: str, lang: str, **kw) -> str:
        return MESSAGES[key][lang].format(**kw)

    def _refuse(self, status: str, lang: str, **kw) -> Reply:
        self.stats.limited += status in ("visitor_limit", "daily_limit")
        return Reply(text=self._msg(status, lang, **kw), status=status, found=False, reason=status)

    def ask(self, question: str, history: list[Turn] | None, lang: str, mode: str, visitor: str) -> Reply:
        """Answer one question for one visitor. Order of checks: input, cache, visitor limit, daily limit, API."""
        lang = lang if lang in ("de", "en") else "de"
        question = (question or "").strip()
        self.stats.requests += 1
        if not question:
            return self._refuse("empty", lang)
        if len(question) > self.limits.max_question_chars:
            return self._refuse("too_long", lang, n=self.limits.max_question_chars)

        hist = generate.trim_history(history, self.cfg.max_history_turns)
        key = AnswerCache.make_key(question, lang, mode, hist)
        cached = self.cache.get(key)
        if cached is not None:
            self.stats.cache_hits += 1
            log.info("request outcome=cache_hit")
            return Reply(**{**asdict(cached), "status": "cached"})

        if not self.visitors.allowed(visitor):
            wait = max(1, round(self.visitors.retry_after_s(visitor) / 60))
            log.info("request outcome=visitor_limit")
            return self._refuse("visitor_limit", lang, n=self.limits.visitor_limit, m=wait)
        if not self.daily.allowed():
            log.info("request outcome=daily_limit")
            return self._refuse("daily_limit", lang)

        self.visitors.record(visitor)
        self.daily.record()
        cfg = Config(**{**asdict(self.cfg), "mode": mode if mode in ("bm25", "vector", "hybrid") else self.cfg.mode})
        try:
            ans = generate.answer_question(question, hist, lang, cfg, self.retriever, self.client)
        except Exception as e:  # never show internals to visitors, never log the question or the exception message
            self.stats.errors += 1
            log.error("request outcome=error type=%s", type(e).__name__)
            return Reply(text=self._msg("error", lang), status="error", found=False, reason="error")

        u = ans.usage
        self.stats.input_tokens += u.input_tokens
        self.stats.output_tokens += u.output_tokens
        self.stats.cost_usd += u.cost_usd
        if ans.reason == "invalid_output":
            self.stats.errors += 1
        elif ans.found:
            self.stats.answered += 1
        else:
            self.stats.not_found += 1
        log.info(
            "request outcome=%s tokens=%d/%d cost=$%.5f | totals: requests=%d cost=$%.4f",
            ans.reason, u.input_tokens, u.output_tokens, u.cost_usd, self.stats.requests, self.stats.cost_usd,
        )
        reply = reply_from_answer(ans)
        if ans.reason != "invalid_output":  # do not cache failures
            self.cache.put(key, reply)
        return reply


# --------------------------------------------------------------------------
# precomputed example answers (cost nothing at runtime)
# --------------------------------------------------------------------------


def load_examples(path: Path = EXAMPLES_PATH) -> list[dict]:
    """[{"id": ..., "question": {"de": ..., "en": ...}, "replies": {"de": {...}, "en": {...}}}, ...]"""
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def example_reply(example: dict, lang: str) -> Reply:
    return Reply(**{**example["replies"][lang], "status": "example"})
