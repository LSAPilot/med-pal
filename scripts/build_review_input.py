"""Build the reviewer packet: question, reference answer and original text of the gold chunks only."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(ids_filter: set[str] | None, out: Path) -> int:
    chunks = {}
    for line in (ROOT / "data/processed/chunks.jsonl").open(encoding="utf-8"):
        c = json.loads(line)
        chunks[c["id"]] = c
    qs = [json.loads(line) for line in (ROOT / "eval/questions.jsonl").open(encoding="utf-8")]
    packet = []
    for q in qs:
        if ids_filter and q["id"] not in ids_filter:
            continue
        item = {"id": q["id"], "type": q["type"], "question": q["question"], "reference_answer": q["reference_answer"],
                "passages": [{"id": g, "citation": chunks[g]["citation"], "text": chunks[g]["text"]} for g in q["gold_ids"]]}
        if q["type"] == "followup":  # earlier turns are needed to resolve the question
            item["earlier_turns"] = [p["question"] for p in qs if p.get("session") == q["session"] and p["turn"] < q["turn"]]
        packet.append(item)
    out.write_text(json.dumps(packet, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(packet)


if __name__ == "__main__":
    only = set(sys.argv[2:]) or None
    print(build(only, Path(sys.argv[1])))
