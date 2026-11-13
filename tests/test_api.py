"""Section F1: the public JSON endpoint /ask (`app.make_api_ask`). Service and API are mocked; no network, no cost."""
import json
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from regulatory_helper.app import MAX_HISTORY_ANSWER_CHARS, build_demo, make_api_ask
from regulatory_helper.generate import Config
from regulatory_helper.limits import LimitConfig
from regulatory_helper.service import Reply, Service
from tests.test_generate import FakeClient, ans_json
from tests.test_limits import Clock
from tests.test_retrieval import fake_retriever

REPLY_KEYS = {"text", "status", "found", "reason", "sources", "search_query", "hits", "best_cosine"}
SOURCE_KEYS = {"id", "title", "citation", "quote", "source_url"}
HIT_KEYS = {"rank", "id", "citation", "score", "cosine"}


def make_api(replies=(), **limits):
    client = FakeClient(replies)
    svc = Service(Config(threshold=0.5), LimitConfig(**limits), fake_retriever(), client, Clock())
    return make_api_ask(svc), svc, client


def req(ip="1.2.3.4"):
    """Stands in for gr.Request: only what visitor_id reads."""
    return SimpleNamespace(headers={"x-forwarded-for": ip}, client=SimpleNamespace(host="10.0.0.1"), session_hash="s")


def turn(q="Was ist ein Medizinprodukt?", a="Ein Produkt mit Zweckbestimmung [c1]."):
    return {"question": q, "answer": a}


# --- success path and JSON shape ------------------------------------------------


def test_answer_is_json_serialisable_with_the_full_reply_shape():
    api, _, _ = make_api(["software class", ans_json(["c1"])])
    r = api("Wie wird Software eingestuft?", [], "de", "hybrid", req())
    json.dumps(r)  # must not raise
    assert isinstance(r, dict) and set(r) == REPLY_KEYS
    assert r["status"] == "ok" and r["found"] is True and r["reason"] == "answered"
    assert r["search_query"] == "software class" and isinstance(r["best_cosine"], float)
    assert r["sources"] and set(r["sources"][0]) == SOURCE_KEYS and r["sources"][0]["id"] == "c1"
    assert r["hits"] and set(r["hits"][0]) == HIT_KEYS


def test_dict_has_exactly_the_fields_of_the_reply_dataclass():
    assert set(Reply.__dataclass_fields__) == REPLY_KEYS  # contract guard: a new field must be a conscious decision


def test_history_is_passed_on_to_the_model():
    api, _, client = make_api(["q", ans_json(["c1"])])
    r = api("Und bei Klasse IIa?", [turn(), turn("Zweite Frage", "Zweite Antwort")], "de", "bm25", req())
    assert r["status"] == "ok"
    prompt = client.calls[0]["messages"][0]["content"]
    assert "Conversation so far" in prompt and "Was ist ein Medizinprodukt?" in prompt and "Zweite Antwort" in prompt


def test_history_none_and_three_rounds_are_accepted():
    api, _, _ = make_api(["q", ans_json(["c1"]), "q", ans_json(["c1"])])
    assert api("one", None, "en", "vector", req())["status"] == "ok"
    assert api("two", [turn()] * 3, "en", "vector", req())["status"] == "ok"


def test_second_identical_request_is_cached():
    api, _, client = make_api(["q", ans_json(["c1"])])
    api("Same question", [], "en", "hybrid", req())
    r = api("Same question", [], "en", "hybrid", req())
    assert r["status"] == "cached" and r["sources"] and len(client.calls) == 2


@pytest.mark.parametrize("mode", ["bm25", "vector", "hybrid"])
@pytest.mark.parametrize("lang", ["de", "en"])
def test_all_allowed_lang_and_mode_values(lang, mode):
    api, _, _ = make_api(["q", ans_json(["c1"])])
    assert api("A question", [], lang, mode, req())["status"] == "ok"


# --- service statuses are passed through ---------------------------------------------


def test_empty_and_too_long_questions_keep_their_service_status():
    api, _, client = make_api([], max_question_chars=20)
    assert api("   ", [], "de", "hybrid", req())["status"] == "empty"
    r = api("x" * 21, [], "en", "hybrid", req())
    assert r["status"] == "too_long" and "20" in r["text"] and r["found"] is False
    assert client.calls == []


def test_visitor_limit_uses_the_forwarded_address():
    api, _, client = make_api(["q1", ans_json(["c1"]), "q2", ans_json(["c1"])], visitor_limit=1)
    assert api("first question", [], "de", "hybrid", req("5.5.5.5"))["status"] == "ok"
    n = len(client.calls)
    assert api("second question", [], "de", "hybrid", req("5.5.5.5"))["status"] == "visitor_limit"
    assert len(client.calls) == n
    assert api("second question", [], "de", "hybrid", req("6.6.6.6"))["status"] == "ok"


def test_without_a_request_object_the_visitor_is_local():
    api, _, _ = make_api(["q", ans_json(["c1"])], visitor_limit=1)
    assert api("first", [], "en", "hybrid", None)["status"] == "ok"
    assert api("second", [], "en", "hybrid", None)["status"] == "visitor_limit"


def test_daily_limit_status():
    api, _, _ = make_api(["q", ans_json(["c1"])], daily_limit=1)
    api("first", [], "en", "hybrid", req("1.1.1.1"))
    r = api("second", [], "en", "hybrid", req("2.2.2.2"))
    assert r["status"] == "daily_limit" and r["found"] is False


def test_model_failure_becomes_an_error_reply_not_an_exception():
    class Boom(FakeClient):
        def create(self, **kw):
            raise RuntimeError("boom")

    svc = Service(Config(), LimitConfig(), fake_retriever(), Boom([]), Clock())
    r = make_api_ask(svc)("A question", [], "en", "hybrid", req())
    assert r["status"] == "error" and r["reason"] == "error" and "boom" not in r["text"]


# --- input validation -------------------------------------------------------------------

BAD_INPUTS = {
    "question_not_text": (123, [], "de", "hybrid"),
    "question_none": (None, [], "de", "hybrid"),
    "question_list": (["a"], [], "de", "hybrid"),
    "lang_unknown": ("hi", [], "fr", "hybrid"),
    "lang_none": ("hi", [], None, "hybrid"),
    "mode_unknown": ("hi", [], "de", "dense"),
    "mode_case": ("hi", [], "de", "BM25"),
    "mode_not_text": ("hi", [], "de", ["bm25"]),
    "history_not_list": ("hi", "nope", "de", "hybrid"),
    "history_dict": ("hi", {"question": "a", "answer": "b"}, "de", "hybrid"),
    "history_too_long": ("hi", [turn()] * 4, "de", "hybrid"),
    "history_item_not_dict": ("hi", ["text"], "de", "hybrid"),
    "history_missing_answer": ("hi", [{"question": "a"}], "de", "hybrid"),
    "history_wrong_types": ("hi", [{"question": 1, "answer": 2}], "de", "hybrid"),
    "history_question_too_long": ("hi", [turn("x" * 501)], "de", "hybrid"),
    "history_answer_too_long": ("hi", [turn(a="x" * (MAX_HISTORY_ANSWER_CHARS + 1))], "de", "hybrid"),
}


@pytest.mark.parametrize("args", BAD_INPUTS.values(), ids=BAD_INPUTS.keys())
def test_invalid_input_gives_error_reply_without_cost(args):
    api, svc, client = make_api(["unused"])
    r = api(*args, req())
    json.dumps(r)
    assert set(r) == REPLY_KEYS
    assert r["status"] == "error" and r["reason"] == "invalid_input" and r["found"] is False
    assert r["sources"] == [] and r["hits"] == [] and r["best_cosine"] is None
    assert client.calls == [] and svc.daily.count == 0  # no API call, no budget used


def test_invalid_input_message_follows_a_valid_language():
    api, _, _ = make_api()
    assert api("hi", [], "en", "nope", req())["text"].startswith("Invalid request")
    assert api("hi", [], "de", "nope", req())["text"].startswith("Ungültige Anfrage")
    assert api("hi", [], "xx", "hybrid", req())["text"].startswith("Ungültige Anfrage")  # unknown lang falls back to German


# --- registration: only /ask is public ------------------------------------------------------


def test_only_ask_is_public_in_the_api_docs():
    svc = Service(Config(threshold=0.5), LimitConfig(), fake_retriever(), FakeClient([]), Clock())
    demo = build_demo(svc)
    public = [d for d in demo.config["dependencies"] if d.get("api_visibility") == "public"]
    assert [d["api_name"] for d in public] == ["ask"]  # exactly one, and not renamed to ask_1 / ask_2 by a name clash
    assert all(d["api_visibility"] == "private" for d in demo.config["dependencies"] if d not in public)


# --- precomputed examples are free on /ask ----------------------------------------


def exhausted_api(examples=None):
    """/ask with visitor and daily limit of 0 (everything paid is refused) and a client that must never be called."""
    client = FakeClient([])
    svc = Service(Config(threshold=0.5), LimitConfig(visitor_limit=0, daily_limit=0), fake_retriever(), client, Clock(), examples=examples)
    return make_api_ask(svc), svc, client


@pytest.mark.parametrize("lang", ["de", "en"])
def test_example_question_is_free_even_when_limits_are_exhausted(lang):
    from regulatory_helper.service import example_reply, load_examples

    api, svc, client = exhausted_api()
    ex = load_examples()[0]
    r = api(ex["question"][lang], [], lang, "hybrid", req())
    assert r == asdict(example_reply(ex, lang)) and r["status"] == "example" and r["sources"] and r["hits"]
    assert client.calls == [] and svc.stats.limited == 0 and svc.stats.example_hits == 1
    assert svc.daily.count == 0


def test_every_shipped_example_matches_in_both_languages():
    from regulatory_helper.service import load_examples

    api, _, client = exhausted_api()
    for ex in load_examples():
        for lang in ("de", "en"):
            assert api(ex["question"][lang], [], lang, "hybrid", req())["status"] == "example"
    assert client.calls == []


def test_example_match_ignores_whitespace_and_case_only():
    from regulatory_helper.service import load_examples

    api, _, _ = exhausted_api()
    q = load_examples()[0]["question"]["en"]
    assert api("  " + q.upper().replace(" ", "  ") + "\n", [], "en", "hybrid", req())["status"] == "example"
    assert api(q[:-1], [], "en", "hybrid", req())["status"] == "visitor_limit"  # anything fuzzier is a normal question


def test_example_text_in_the_other_language_is_not_an_example():
    from regulatory_helper.service import load_examples

    api, _, _ = exhausted_api()
    assert api(load_examples()[0]["question"]["de"], [], "en", "hybrid", req())["status"] == "visitor_limit"


def test_example_with_history_or_other_mode_takes_the_normal_path():
    from regulatory_helper.service import load_examples

    api, _, client = exhausted_api()
    q = load_examples()[0]["question"]["de"]
    assert api(q, [turn()], "de", "hybrid", req())["status"] == "visitor_limit"
    assert api(q, [], "de", "bm25", req())["status"] == "visitor_limit"
    assert api(q, [], "de", "vector", req())["status"] == "visitor_limit"
    assert client.calls == []


def test_example_with_history_or_other_mode_reaches_the_api_when_allowed():
    from regulatory_helper.service import load_examples

    q = load_examples()[0]["question"]["de"]
    api, _, client = make_api(["q", ans_json(["c1"]), "q", ans_json(["c1"])])
    assert api(q, [turn()], "de", "hybrid", req())["status"] == "ok"
    n = len(client.calls)
    assert n > 0  # the follow-up reached the API
    assert api(q, [], "de", "bm25", req())["status"] == "ok"
    assert len(client.calls) > n  # so did the other mode


def test_non_example_question_counts_against_limits_as_before():
    api, svc, client = make_api(["q", ans_json(["c1"])], visitor_limit=5)
    assert api("Some other question", [], "de", "hybrid", req())["status"] == "ok"
    assert svc.stats.example_hits == 0 and len(client.calls) == 2


def test_empty_and_too_long_still_win_over_examples():
    api, _, _ = exhausted_api(examples=[{"id": "x", "question": {"de": "A B"}, "replies": {"de": {"text": "t"}}}])
    assert api("A B", [], "de", "hybrid", req())["status"] == "example"
    assert api("   ", [], "de", "hybrid", req())["status"] == "empty"
    assert api("A" + " " * 600 + "B", [], "de", "hybrid", req())["status"] == "too_long"  # would normalise to the example


def test_examples_do_not_consume_the_budget_of_a_real_question():
    from regulatory_helper.service import load_examples

    api, svc, _ = make_api(["q", ans_json(["c1"])], visitor_limit=1, daily_limit=1)
    q = load_examples()[0]["question"]["de"]
    for _ in range(3):
        assert api(q, [], "de", "hybrid", req())["status"] == "example"
    assert api("A real question", [], "de", "hybrid", req())["status"] == "ok"
    assert svc.daily.count == 1
