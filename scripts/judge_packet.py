"""Build the blind judge input (answers as A/B/C in random order) and resolve the judgements afterwards.

  uv run python scripts/judge_packet.py build     -> eval/judge-input.jsonl (for the judge) + eval/judge-mapping.json (judge must not see it)
  uv run python scripts/judge_packet.py resolve   -> eval/judgements-resolved.jsonl (judgements.jsonl with real system names)
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
SYSTEMS = ["rag", "haiku-no-rag", "sonnet-no-rag"]
SEED = 5150


def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def build():
    qs = jl(EVAL / "questions.jsonl")
    chunks = {c["id"]: c for c in jl(ROOT / "data/processed/chunks.jsonl")}
    ans = {s: {r["id"]: r for r in jl(EVAL / "answers" / f"{s}.jsonl")} for s in SYSTEMS}
    rnd = random.Random(SEED)
    inputs, mapping = [], {}
    for q in qs:
        order = SYSTEMS[:]
        rnd.shuffle(order)
        letters = dict(zip("ABC", order))
        mapping[q["id"]] = letters
        history = [
            {"question": p["question"], "reference_answer": p["reference_answer"]}
            for p in qs if q["session"] and p["session"] == q["session"] and p["turn"] < q["turn"]
        ]
        inputs.append({
            "id": q["id"], "type": q["type"], "lang": q["lang"], "question": q["question"],
            "earlier_turns_of_session": history,
            "reference_answer": q["reference_answer"],
            "source_text": [{"id": i, "citation": chunks[i].get("citation"), "text": chunks[i]["text"]} for i in q["gold_ids"]],
            "answers": {L: ans[s][q["id"]]["answer"] for L, s in letters.items()},
        })
    (EVAL / "judge-input.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in inputs) + "\n", encoding="utf-8")
    (EVAL / "judge-mapping.json").write_text(json.dumps(mapping, indent=1) + "\n", encoding="utf-8")


def resolve():
    mapping = json.loads((EVAL / "judge-mapping.json").read_text())
    out = []
    for j in jl(EVAL / "judgements.jsonl"):
        m = mapping[j["id"]]
        res = dict(j)
        res["scores"] = {m[L]: v for L, v in j["scores"].items()}
        out.append(res)
    (EVAL / "judgements-resolved.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in out) + "\n", encoding="utf-8")


{"build": build, "resolve": resolve}[sys.argv[1]]()
