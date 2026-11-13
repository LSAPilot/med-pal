"""The one narrow entry point the user interface calls.

`Service.ask(...)` wraps `generate.answer_question` with limits, cache, input checks and error handling and returns a plain,
JSON-serialisable `Reply`. The Gradio app contains no logic of its own.

Privacy: question texts are never logged. Only counters are kept: requests, outcomes, tokens, cost, errors.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from . import generate
from .chunking import ROOT
from .generate import LANGS, Answer, Config, Turn
from .limits import AnswerCache, Clock, DailyLimit, LimitConfig, VisitorLimit
from .retrieval import MODES, Retriever

log = logging.getLogger(__name__)

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
# search mode the shipped examples were precomputed with (scripts/precompute_examples.py); other modes go the normal path
EXAMPLE_MODE = "hybrid"
LIMIT_STATUSES = ("visitor_limit", "daily_limit")


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


def _round(x: float | None, digits: int) -> float | None:
    return None if x is None else round(x, digits)


def reply_from_answer(ans: Answer) -> Reply:
    return Reply(
        text=ans.text,
        found=ans.found,
        reason=ans.reason,
        sources=[asdict(s) for s in ans.sources],
        search_query=ans.search_query,
        hits=[
            {"rank": h.rank, "id": h.chunk.id, "citation": h.chunk.citation, "score": round(h.score, 4), "cosine": _round(h.cosine, 3)}
            for h in ans.hits
        ],
        best_cosine=_round(ans.best_cosine, 3),
    )


@dataclass
class Stats:
    """Counters only. Never question text, never addresses."""

    requests: int = 0
    answered: int = 0
    not_found: int = 0
    cache_hits: int = 0
    example_hits: int = 0
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
        clock: Clock = time.time,
        examples: list[dict] | None = None,
    ):
        self.cfg = cfg or Config()
        self.limits = limits or LimitConfig.from_env()
        self._retriever = retriever
        self._client = client
        self.daily = DailyLimit(self.limits.daily_limit, clock)
        self.visitors = VisitorLimit(self.limits.visitor_limit, self.limits.visitor_window_s, clock)
        self.cache = AnswerCache(self.limits.cache_size)
        self.stats = Stats()
        self._examples = index_examples(load_examples() if examples is None else examples)

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

    def _refuse(self, status: str, lang: str, **kw) -> Reply:
        if status in LIMIT_STATUSES:
            self.stats.limited += 1
        log.info("request outcome=%s", status)
        return Reply(text=MESSAGES[status][lang].format(**kw), status=status, found=False, reason=status)

    def ask(self, question: str, history: list[Turn] | None, lang: str, mode: str, visitor: str) -> Reply:
        """Answer one question for one visitor. Order of checks: input, precomputed example, cache, visitor limit, daily limit, API."""
        lang = lang if lang in LANGS else "de"
        mode = mode if mode in MODES else self.cfg.mode
        question = (question or "").strip()
        self.stats.requests += 1
        if not question:
            return self._refuse("empty", lang)
        if len(question) > self.limits.max_question_chars:
            return self._refuse("too_long", lang, n=self.limits.max_question_chars)

        # a precomputed example is free: no limits, no cache, no API. Only for a fresh conversation in the mode it was computed with
        if not history and mode == EXAMPLE_MODE:
            ex = self._examples.get((lang, normalize_question(question)))
            if ex is not None:
                self.stats.example_hits += 1
                log.info("request outcome=example_hit")
                return example_reply(ex, lang)

        hist = generate.trim_history(history, self.cfg.max_history_turns)
        key = AnswerCache.make_key(question, lang, mode, hist)
        cached = self.cache.get(key)
        if cached is not None:
            self.stats.cache_hits += 1
            log.info("request outcome=cache_hit")
            return replace(cached, status="cached")

        if not self.visitors.allowed(visitor):
            wait = max(1, round(self.visitors.retry_after_s(visitor) / 60))
            return self._refuse("visitor_limit", lang, n=self.limits.visitor_limit, m=wait)
        if not self.daily.allowed():
            return self._refuse("daily_limit", lang)

        self.visitors.record(visitor)
        self.daily.record()
        try:
            ans = generate.answer_question(question, hist, lang, replace(self.cfg, mode=mode), self.retriever, self.client)
        except Exception as e:  # never show internals to visitors, never log the question or the exception message
            self.stats.errors += 1
            log.error("request outcome=error type=%s", type(e).__name__)
            return Reply(text=MESSAGES["error"][lang], status="error", found=False, reason="error")

        self._count(ans)
        reply = reply_from_answer(ans)
        if ans.reason != "invalid_output":  # do not cache failures
            self.cache.put(key, reply)
        return reply

    def _count(self, ans: Answer) -> None:
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


def normalize_question(q: str) -> str:
    """Whitespace collapsed and case-folded: trivial typing differences still match an example, nothing fuzzier."""
    return " ".join(q.split()).casefold()


def index_examples(examples: list[dict]) -> dict[tuple[str, str], dict]:
    """(lang, normalised question) -> example, for the exact-match shortcut in `Service.ask`."""
    return {(lang, normalize_question(q)): ex for ex in examples for lang, q in ex["question"].items() if lang in ex["replies"]}
