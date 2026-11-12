"""Section 3 tests. The Anthropic API is mocked: no network, no cost."""
import json
from types import SimpleNamespace

import pytest

from regulatory_helper import generate
from regulatory_helper.generate import Config, Turn
from tests.test_retrieval import fake_retriever


class FakeClient:
    """Stands in for anthropic.Anthropic. Replies are consumed in order; every request is recorded."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        text = self.replies.pop(0)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=100, output_tokens=20),
            stop_reason="end_turn",
        )


def ans_json(ids, found=True, answer="Software can be a device [c1]."):
    return json.dumps({"found": found, "answer": answer, "used_ids": ids})


CFG = Config(threshold=0.5)


def test_rewrite_without_history():
    c = FakeClient(["software classification rule", ans_json(["c1"])])
    a = generate.answer_question("Wie wird Software eingestuft?", [], "de", CFG, fake_retriever(), c)
    assert a.search_query == "software classification rule"
    assert "Latest question: Wie wird Software eingestuft?" in c.calls[0]["messages"][0]["content"]
    assert "Conversation so far" not in c.calls[0]["messages"][0]["content"]


def test_rewrite_and_answer_receive_history():
    hist = [Turn("Is my app a device?", "Possibly, see Article 2.")]
    c = FakeClient(["software classification class", ans_json(["c1"])])
    generate.answer_question("And which class?", hist, "en", CFG, fake_retriever(), c)
    for call in c.calls:
        assert "Is my app a device?" in call["messages"][0]["content"]
        assert "Possibly, see Article 2." in call["messages"][0]["content"]


def test_history_is_trimmed_to_three_rounds():
    hist = [Turn(f"q{i}", f"a{i}") for i in range(6)]
    assert [t.question for t in generate.trim_history(hist, 3)] == ["q3", "q4", "q5"]
    assert generate.trim_history(hist, 0) == [] and generate.trim_history(None, 3) == []
    c = FakeClient(["software classification", ans_json(["c1"])])
    generate.answer_question("next", hist, "en", CFG, fake_retriever(), c)
    sent = c.calls[0]["messages"][0]["content"]
    assert "q2" not in sent and "q3" in sent and "q5" in sent


def test_history_limit_is_configurable():
    hist = [Turn(f"q{i}", f"a{i}") for i in range(3)]
    c = FakeClient(["software classification", ans_json(["c1"])])
    generate.answer_question("next", hist, "en", Config(threshold=0.5, max_history_turns=1), fake_retriever(), c)
    sent = c.calls[0]["messages"][0]["content"]
    assert "q1" not in sent and "q2" in sent


def test_history_is_not_mutated():
    hist = [Turn("a", "b")]
    generate.answer_question("x", hist, "en", CFG, fake_retriever(), FakeClient(["software classification", ans_json(["c1"])]))
    assert len(hist) == 1


def test_no_rewrite_uses_raw_question_and_one_call():
    c = FakeClient([ans_json(["c1"])])
    a = generate.answer_question("software classification", [], "en", Config(threshold=0.5, rewrite=False), fake_retriever(), c)
    assert len(c.calls) == 1 and a.search_query == "software classification"


def test_answer_with_sources_from_chunks_not_from_model():
    c = FakeClient(["software classification", ans_json(["c1"])])
    a = generate.answer_question("q", [], "en", CFG, fake_retriever(), c)
    assert a.found and a.reason == "answered"
    assert [s.id for s in a.sources] == ["c1"]
    assert a.sources[0].quote == "software classification rule class IIa"  # original text from the store
    assert a.usage.calls == 2 and a.usage.input_tokens == 200 and a.usage.cost_usd > 0


def test_invalid_ids_are_dropped_and_logged(caplog):
    c = FakeClient(["software classification", ans_json(["c1", "MDR-999-9", "c1"])])
    with caplog.at_level("WARNING", logger="regulatory_helper"):
        a = generate.answer_question("q", [], "en", CFG, fake_retriever(), c)
    assert [s.id for s in a.sources] == ["c1"] and a.dropped_ids == ["MDR-999-9"]
    assert "MDR-999-9" in caplog.text


def test_id_not_among_delivered_hits_is_invalid():
    r = fake_retriever()
    hits = r.search("software classification", mode="bm25", k=1)  # only c1 delivered
    assert generate.validate_ids(["c1", "c3"], hits) == (["c1"], ["c3"])


def test_answer_with_only_invalid_ids_is_rejected():
    c = FakeClient(["software classification", ans_json(["nope"])])
    a = generate.answer_question("q", [], "en", CFG, fake_retriever(), c)
    assert not a.found and a.sources == [] and a.text == generate.NOT_FOUND["en"]


@pytest.mark.parametrize(
    "raw",
    [
        '{"found": true, "answer": "x", "used_ids": ["c1"]}',
        '```json\n{"found": true, "answer": "x", "used_ids": ["c1"]}\n```',
        'Here you go: {"found": true, "answer": "x", "used_ids": ["c1"]} done',
    ],
)
def test_json_parsing_tolerates_fences_and_prose(raw):
    assert generate.parse_answer_json(raw)["used_ids"] == ["c1"]


@pytest.mark.parametrize("raw", ["not json", "[]", '{"answer": 5}', '{"answer": "x", "used_ids": "c1"}'])
def test_json_parsing_rejects_garbage(raw):
    assert generate.parse_answer_json(raw) is None


def test_garbage_model_output_gives_error_message():
    c = FakeClient(["software classification", "I cannot do that"])
    a = generate.answer_question("q", [], "de", CFG, fake_retriever(), c)
    assert a.reason == "invalid_output" and a.text == generate.ERROR_MSG["de"] and not a.sources


def test_below_threshold_makes_no_answer_call():
    # cosine can never reach 1.5, so the threshold stops the pipeline after the rewriting call
    c = FakeClient(["completely unrelated query"])
    a = generate.answer_question("Wie wird das Wetter?", [], "de", Config(threshold=1.5), fake_retriever(), c)
    assert len(c.calls) == 1  # only the rewriting call, no answer call
    assert not a.found and a.reason == "below_threshold" and a.text == generate.NOT_FOUND["de"]


def test_below_threshold_without_rewrite_makes_no_api_call():
    c = FakeClient([])
    a = generate.answer_question("software classification", [], "en", Config(threshold=1.5, rewrite=False), fake_retriever(), c)
    assert c.calls == [] and a.reason == "below_threshold"


def test_bm25_mode_gets_cosine_for_threshold():
    r = fake_retriever()
    hits = r.search("software classification", mode="bm25", k=3)
    assert hits[0].cosine is None
    assert generate.best_cosine(r, "software classification", hits) == pytest.approx(1.0)


def test_model_says_not_found():
    c = FakeClient(["software classification", ans_json([], found=False, answer="")])
    a = generate.answer_question("q", [], "en", CFG, fake_retriever(), c)
    assert not a.found and a.reason == "model_no_answer" and a.text == generate.NOT_FOUND["en"]


def test_request_uses_configured_model_and_token_cap():
    c = FakeClient(["software classification", ans_json(["c1"])])
    generate.answer_question("q", [], "en", Config(threshold=0.5, model="m-x", answer_max_tokens=123), fake_retriever(), c)
    assert c.calls[1]["model"] == "m-x" and c.calls[1]["max_tokens"] == 123


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("software classification", "software classification"),
        ('Query: "software classification"', "software classification"),
        ("software classification\n\nExtra German line", "software classification"),
        ("  \n ", ""),
    ],
)
def test_clean_query(raw, expected):
    assert generate.clean_query(raw) == expected


def test_empty_rewrite_falls_back_to_question():
    c = FakeClient(["  ", ans_json(["c1"])])
    a = generate.answer_question("software classification", [], "en", CFG, fake_retriever(), c)
    assert a.search_query == "software classification"


def test_found_as_string_false_is_not_found():
    data = generate.parse_answer_json('{"found": "false", "answer": "x", "used_ids": []}')
    assert data["found"] is False


def test_unknown_language_is_rejected():
    with pytest.raises(ValueError):
        generate.answer_question("q", lang="fr", retriever=fake_retriever(), client=FakeClient([]))
