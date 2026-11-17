"""Shared paths, system names and loaders for the evaluation data in eval/ (no API, no project imports).

Used by run_eval.py, judge_packet.py, build_evaluation.py and plot_evaluation.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
SYSTEMS = ["rag", "haiku-no-rag", "sonnet-no-rag"]
LABEL = {"rag": "RAG (Haiku + search)", "haiku-no-rag": "Haiku, no RAG", "sonnet-no-rag": "Sonnet, no RAG"}


def read_jsonl(path: Path | str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


@dataclass
class EvalData:
    questions: dict[str, dict]  # id -> question record
    judgements: dict[str, dict]  # id -> {system: scores}
    answers: dict[str, dict[str, dict]]  # system -> id -> answer record
    search: dict  # eval/search-metrics.json

    @property
    def has_answer(self) -> list[str]:
        return [i for i, q in self.questions.items() if q["type"] != "no_answer"]

    @property
    def no_answer(self) -> list[str]:
        return [i for i, q in self.questions.items() if q["type"] == "no_answer"]

    @property
    def followups(self) -> list[str]:
        return [i for i, q in self.questions.items() if q["type"] == "followup"]

    def scores(self, system: str, ids: list[str], key: str) -> list:
        return [self.judgements[i][system][key] for i in ids]


def load() -> EvalData:
    """Questions, resolved blind judgements, answers of all systems and search metrics."""
    return EvalData(
        questions={q["id"]: q for q in read_jsonl(EVAL / "questions.jsonl")},
        judgements={j["id"]: j["scores"] for j in read_jsonl(EVAL / "judgements-resolved.jsonl")},
        answers={s: {r["id"]: r for r in read_jsonl(EVAL / "answers" / f"{s}.jsonl")} for s in SYSTEMS},
        search=json.loads((EVAL / "search-metrics.json").read_text(encoding="utf-8")),
    )
