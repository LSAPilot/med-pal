"""Validate eval/questions.jsonl against data/processed/chunks.jsonl (no API, no LLM)."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ["id", "question", "lang", "type", "session", "turn", "gold_ids", "reference_answer"]


def check(questions_path: Path, chunks_path: Path) -> list[str]:
    errors: list[str] = []
    chunk_ids = {json.loads(line)["id"] for line in chunks_path.open(encoding="utf-8")}
    qs = [json.loads(line) for line in questions_path.open(encoding="utf-8") if line.strip()]
    ids = [q.get("id") for q in qs]
    errors += [f"duplicate question id: {i}" for i, n in Counter(ids).items() if n > 1]
    for q in qs:
        qid = q.get("id")
        for field in REQUIRED:
            if field not in q:
                errors.append(f"{qid}: missing field {field}")
        if q.get("type") not in ("answerable", "no_answer", "followup"):
            errors.append(f"{qid}: bad type {q.get('type')}")
        if q.get("lang") not in ("de", "en"):
            errors.append(f"{qid}: bad lang {q.get('lang')}")
        if not q.get("question") or not q.get("reference_answer"):
            errors.append(f"{qid}: empty question or reference_answer")
        gold = q.get("gold_ids") or []
        if len(gold) != len(set(gold)):
            errors.append(f"{qid}: duplicate gold_ids")
        if q.get("type") == "no_answer" and gold:
            errors.append(f"{qid}: no_answer must have empty gold_ids")
        if q.get("type") != "no_answer" and not gold:
            errors.append(f"{qid}: gold_ids empty")
        errors += [f"{qid}: gold id not in chunks.jsonl: {g}" for g in gold if g not in chunk_ids]
        if q.get("type") == "followup" and (not q.get("session") or not q.get("turn")):
            errors.append(f"{qid}: followup needs session and turn")
    types = Counter(q.get("type") for q in qs)
    if dict(types) != {"answerable": 22, "no_answer": 5, "followup": 3}:
        errors.append(f"unexpected type distribution: {dict(types)}")
    if sum(1 for q in qs if q.get("near_miss")) < 3:
        errors.append("fewer than 3 near-miss no_answer questions")
    turns = sorted(q["turn"] for q in qs if q.get("type") == "followup")
    if turns != [1, 2, 3]:
        errors.append(f"follow-up turns are {turns}, expected [1, 2, 3]")
    return errors


if __name__ == "__main__":
    errs = check(ROOT / "eval/questions.jsonl", ROOT / "data/processed/chunks.jsonl")
    for e in errs:
        print("ERROR:", e)
    if not errs:
        print("OK: questions.jsonl is consistent")
    sys.exit(1 if errs else 0)
