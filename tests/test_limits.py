"""Section 4: limits, cache and the service wrapper. The API is mocked; no network, no cost."""
import logging

import pytest

from regulatory_helper.generate import Config, Turn
from regulatory_helper.limits import AnswerCache, DailyLimit, LimitConfig, VisitorLimit
from regulatory_helper.service import Service, example_reply
from tests.test_generate import FakeClient, ans_json
from tests.test_retrieval import fake_retriever


class Clock:
    def __init__(self, t=1_700_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


# --- building blocks --------------------------------------------------------


def test_daily_limit_blocks_and_resets_next_utc_day():
    clock = Clock()
    d = DailyLimit(2, clock)
    for _ in range(2):
        assert d.allowed()
        d.record()
    assert not d.allowed()
    clock.t += 86400
    assert d.allowed() and d.count == 0


def test_visitor_limit_is_per_visitor_and_sliding():
    clock = Clock()
    v = VisitorLimit(2, 3600, clock)
    for _ in range(2):
        v.record("1.2.3.4")
    assert not v.allowed("1.2.3.4")
    assert v.allowed("5.6.7.8")  # other visitor unaffected
    assert 0 < v.retry_after_s("1.2.3.4") <= 3600
    clock.t += 3601
    assert v.allowed("1.2.3.4")


def test_visitor_key_is_a_hash_not_the_address():
    v = VisitorLimit(1, 60)
    v.record("1.2.3.4")
    assert "1.2.3.4" not in v._events and all("1.2.3.4" not in k for k in v._events)


def test_cache_is_lru_and_key_depends_on_all_inputs():
    c = AnswerCache(2)
    k = [AnswerCache.make_key(q, "de", "hybrid", []) for q in ("a", "b", "c")]
    c.put(k[0], 1), c.put(k[1], 2)
    c.get(k[0])  # refresh a
    c.put(k[2], 3)  # evicts b
    assert c.get(k[1]) is None and c.get(k[0]) == 1 and len(c) == 2
    base = AnswerCache.make_key("Q", "de", "hybrid", [])
    assert base == AnswerCache.make_key("  q ", "de", "hybrid", [])  # whitespace and case do not matter
    assert base != AnswerCache.make_key("Q", "en", "hybrid", [])
    assert base != AnswerCache.make_key("Q", "de", "bm25", [])
    assert base != AnswerCache.make_key("Q", "de", "hybrid", [Turn("x", "y")])


def test_limit_config_from_env(monkeypatch):
    monkeypatch.setenv("DAILY_LIMIT", "7")
    monkeypatch.setenv("VISITOR_LIMIT", "3")
    c = LimitConfig.from_env()
    assert (c.daily_limit, c.visitor_limit, c.visitor_window_s) == (7, 3, 3600)


# --- service ------------------------------------------------------------------


def make_service(replies, **limits):
    client = FakeClient(replies)
    svc = Service(Config(threshold=0.5), LimitConfig(**limits), fake_retriever(), client, Clock())
    return svc, client


def test_answer_has_sources_and_hits_for_the_ui():
    svc, c = make_service(["software class", ans_json(["c1"])])
    r = svc.ask("Wie wird Software eingestuft?", [], "de", "hybrid", "v1")
    assert r.status == "ok" and r.found and r.sources[0]["id"] == "c1"
    assert r.search_query == "software class" and r.hits and r.counted
    assert len(c.calls) == 2


def test_cache_hit_costs_no_api_call_and_no_limit():
    svc, c = make_service(["q", ans_json(["c1"])], visitor_limit=1)
    svc.ask("Same question", [], "en", "hybrid", "v1")
    r = svc.ask("same  question", [], "en", "hybrid", "v1")  # visitor limit is used up, cache still answers
    assert r.status == "cached" and r.sources and len(c.calls) == 2
    assert svc.stats.cache_hits == 1


def test_visitor_limit_gives_friendly_message_without_api_call():
    svc, c = make_service(["q1", ans_json(["c1"]), "q2", ans_json(["c1"])], visitor_limit=1)
    svc.ask("first question", [], "de", "hybrid", "v1")
    n = len(c.calls)
    r = svc.ask("second question", [], "de", "hybrid", "v1")
    assert r.status == "visitor_limit" and "Limit" in r.text and not r.counted
    assert len(c.calls) == n
    assert svc.ask("second question", [], "de", "hybrid", "other").status == "ok"  # other visitor is fine


def test_daily_limit_blocks_everyone_without_api_call():
    svc, c = make_service(["q", ans_json(["c1"])], daily_limit=1)
    svc.ask("first", [], "en", "hybrid", "v1")
    n = len(c.calls)
    r = svc.ask("second", [], "en", "hybrid", "v2")
    assert r.status == "daily_limit" and "daily" in r.text and len(c.calls) == n
    assert svc.stats.limited == 1


def test_empty_and_too_long_questions_make_no_call():
    svc, c = make_service([], max_question_chars=20)
    assert svc.ask("  ", [], "de", "hybrid", "v").status == "empty"
    assert svc.ask("x" * 21, [], "de", "hybrid", "v").status == "too_long"
    assert c.calls == []


def test_api_error_is_friendly_and_logs_no_question(caplog):
    class Boom(FakeClient):
        def create(self, **kw):
            raise RuntimeError("secret question text leaked here")

    svc = Service(Config(), LimitConfig(), fake_retriever(), Boom([]), Clock())
    with caplog.at_level(logging.INFO, logger="regulatory_helper"):
        r = svc.ask("My private question", [], "en", "hybrid", "1.2.3.4")
    assert r.status == "error" and "try again" in r.text and not r.counted
    assert svc.stats.errors == 1
    logged = caplog.text
    assert "private question" not in logged and "leaked" not in logged and "1.2.3.4" not in logged


def test_logs_contain_counters_but_no_question_or_address(caplog):
    svc, _ = make_service(["rewritten secret-topic query", ans_json(["c1"])])
    with caplog.at_level(logging.INFO, logger="regulatory_helper"):
        svc.ask("Meine vertrauliche Frage", [], "de", "hybrid", "9.9.9.9")
    assert "vertrauliche" not in caplog.text and "9.9.9.9" not in caplog.text and "secret-topic" not in caplog.text
    assert "tokens=" in caplog.text and "cost=" in caplog.text


def test_history_is_trimmed_and_mode_is_passed():
    svc, c = make_service(["q", ans_json(["c1"])])
    hist = [Turn(f"q{i}", f"a{i}") for i in range(5)]
    svc.ask("follow-up", hist, "en", "bm25", "v")
    prompt = c.calls[0]["messages"][0]["content"]
    assert "q4" in prompt and "q2" in prompt and "q1" not in prompt


def test_example_reply_needs_no_service():
    ex = {"id": "e", "question": {"de": "F", "en": "Q"},
          "replies": {"de": {"text": "A", "found": True, "sources": [{"id": "c1"}]}, "en": {"text": "B"}}}
    r = example_reply(ex, "de")
    assert r.status == "example" and r.text == "A" and r.counted


def test_shipped_examples_are_valid():
    from regulatory_helper.service import load_examples

    ex = load_examples()
    assert 4 <= len(ex) <= 5
    for e in ex:
        for lang in ("de", "en"):
            r = example_reply(e, lang)
            assert r.text and r.sources and r.hits and e["question"][lang]
