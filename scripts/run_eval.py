"""Section 5b: answer runs (RAG, Haiku, Sonnet without RAG), cost estimate, search metrics.

Usage (from repo root):
  uv run python scripts/run_eval.py estimate     # prints the cost estimate, no API call
  uv run python scripts/run_eval.py answers      # the three API runs, cached per question in eval/answers/*.jsonl
  uv run python scripts/run_eval.py search       # Hit@6 / MRR per mode -> eval/search-metrics.json (no LLM, needs rag.jsonl for rewrites)
Answers already present in the jsonl files are never requested again (cache).
"""
from __future__ import annotations

import json
import sys

from eval_data import EVAL, read_jsonl
from eval_queries import is_hit

from regulatory_helper import generate as g
from regulatory_helper.retrieval import MODES, Retriever

ANS = EVAL / "answers"
SYSTEMS = {
    "rag": ("claude-haiku-5-5", "rag.jsonl"),
    "haiku-no-rag": ("claude-haiku-5-5", "haiku-no-rag.jsonl"),
    "sonnet-no-rag": ("claude-sonnet-5-5", "sonnet-no-rag.jsonl"),
}
# USD per 1M tokens. Haiku: from Config. Sonnet 5.5: price could not be looked up in this offline run, so a deliberately
# conservative assumption (classic Sonnet tier) is used; the real invoice may be lower. Adjust here if the real price differs.
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (3.00, 15.00)}

NO_RAG_SYSTEM = """You answer questions about EU regulations for medical device software (MDR, GDPR, AI Act). You give no legal advice.
Rules:
- Keep the answer short and concrete (typically 2 to 6 sentences). Mention the relevant article/annex in the text where useful.
- Write the answer in the language requested by the user.
- A conversation history may be given only to understand follow-up questions.
Respond with the answer text only."""


def load_questions() -> list[dict]:
    return read_jsonl(EVAL / "questions.jsonl")


def read_cache(name: str) -> dict[str, dict]:
    p = ANS / SYSTEMS[name][1]
    return {r["id"]: r for r in read_jsonl(p)} if p.exists() else {}


def append(name: str, rec: dict) -> None:
    with open(ANS / SYSTEMS[name][1], "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def history_for(q: dict, cache: dict[str, dict], questions: list[dict]) -> list[g.Turn]:
    """Follow-ups get the system's OWN earlier answers of the same session as history."""
    if not q.get("session"):
        return []
    prev = [p for p in questions if p.get("session") == q["session"] and p["turn"] < q["turn"]]
    prev.sort(key=lambda p: p["turn"])
    return [g.Turn(p["question"], cache[p["id"]]["answer"]) for p in prev]


def cost(model: str, i: int, o: int) -> float:
    pi, po = PRICES[model]
    return (i * pi + o * po) / 1e6


def estimate() -> None:
    qs = load_questions()
    n = len(qs)
    # token assumptions from section 3 (Haiku ~750-1000 output tokens incl. thinking) with margin; worst case = max_tokens
    rag_in, rag_out = 3500 + 300, 1300
    nr_in, nr_out = 400, 1200
    cfg = g.Config()
    rows, total, worst_total = [], 0.0, 0.0
    for name, (model, _) in SYSTEMS.items():
        i, o = (rag_in, rag_out) if name == "rag" else (nr_in, nr_out)
        exp = n * cost(model, i, o)
        wi, wo = (rag_in + 300, cfg.answer_max_tokens + cfg.rewrite_max_tokens) if name == "rag" else (nr_in + 300, cfg.answer_max_tokens)
        worst = n * cost(model, wi, wo)
        rows.append((name, model, i, o, exp, worst))
        total += exp
        worst_total += worst
    lines = [
        "# Cost estimate for section 5b (3 answer runs)", "",
        f"Questions: {n}. Effort `{cfg.effort}`, `max_tokens` {cfg.answer_max_tokens} (rewrite {cfg.rewrite_max_tokens}) for all systems.", "",
        "| System | Model | Input tok/question | Output tok/question (incl. thinking) | Expected USD | Worst case USD (all at max_tokens) |",
        "|---|---|---|---|---|---|",
    ]
    for name, model, i, o, exp, worst in rows:
        lines.append(f"| {name} | {model} | {i} | {o} | {exp:.3f} | {worst:.3f} |")
    lines += [
        f"| **Total** | | | | **{total:.3f}** | {worst_total:.3f} |", "",
        "Prices (USD per 1M tokens, input/output): " + ", ".join(f"{m} {a}/{b}" for m, (a, b) in PRICES.items()) + ".", "",
        "**Assumption:** Haiku prices come from `Config` (0.10/0.50). The Sonnet 5.5 price could not be looked up (no web access in the headless run), "
        "so the classic Sonnet tier 3/15 is assumed as a conservative figure. Output tokens per question (~1200-1300) follow the section 3 measurement "
        "(Haiku 750-1000 incl. internal thinking) plus margin; Sonnet at effort `low` should be in the same range.", "",
        f"**Approval rule:** expected total <= 1.00 USD counts as approved. Expected total: {total:.3f} USD -> "
        + ("approved, runs start." if total <= 1.0 else "NOT approved, no API run."),
        f"The worst case ({worst_total:.2f} USD) assumes every answer uses the full `max_tokens` and is not realistic.",
    ]
    print("\n".join(lines))
    if total > 1.0:
        sys.exit(2)


def run_answers() -> None:
    ANS.mkdir(exist_ok=True)
    qs = load_questions()
    client = g.get_client()
    retriever = Retriever.load()
    for name, (model, _) in SYSTEMS.items():
        cache = read_cache(name)
        cfg = g.Config(model=model)
        for q in qs:
            if q["id"] in cache:
                continue
            hist = history_for(q, cache, qs)
            if name == "rag":
                a = g.answer_question(q["question"], hist, q["lang"], cfg, retriever, client)
                rec = {
                    "id": q["id"], "answer": a.text, "found": a.found, "reason": a.reason, "search_query": a.search_query,
                    "best_cosine": a.best_cosine, "cited_ids": [s.id for s in a.sources], "dropped_ids": a.dropped_ids,
                    "retrieved_ids": [h.chunk.id for h in a.hits],
                    "calls": a.usage.calls, "input_tokens": a.usage.input_tokens, "output_tokens": a.usage.output_tokens,
                    "cost_usd": cost(model, a.usage.input_tokens, a.usage.output_tokens),
                }
            else:
                parts = []
                if hist:
                    parts.append("Conversation so far (for follow-up context only):\n" + g.history_text(hist))
                parts.append(f"Question: {q['question']}\nAnswer language: {g.LANG_NAME[q['lang']]}")
                resp = client.messages.create(
                    model=model, max_tokens=cfg.answer_max_tokens, system=NO_RAG_SYSTEM,
                    messages=[{"role": "user", "content": "\n\n".join(parts)}], output_config={"effort": cfg.effort},
                )
                text = g.response_text(resp)
                rec = {
                    "id": q["id"], "answer": text, "stop_reason": resp.stop_reason, "calls": 1,
                    "input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens,
                    "cost_usd": cost(model, resp.usage.input_tokens, resp.usage.output_tokens),
                }
            append(name, rec)
            cache[q["id"]] = rec
            print(name, q["id"], f"${rec['cost_usd']:.4f}", flush=True)


def search_metrics() -> None:
    qs = [q for q in load_questions() if q["gold_ids"]]
    rag = read_cache("rag")
    retriever = Retriever.load()
    out = {"n": len(qs), "queries": "rewritten by the RAG run (Haiku), as in production", "modes": {}}
    for mode in MODES:
        hit = rr = 0.0
        per = {}
        for q in qs:
            query = rag[q["id"]]["search_query"]
            ranked = [h.chunk.id for h in retriever.search(query, mode=mode, k=50)]
            ranks = [r for r, cid in enumerate(ranked, 1) if is_hit(cid, q["gold_ids"])]
            first = ranks[0] if ranks else None
            hit += bool(first and first <= 6)
            rr += 1 / first if first else 0
            per[q["id"]] = first
        out["modes"][mode] = {"hit@6": hit / len(qs), "mrr": rr / len(qs), "first_rank": per}
    (EVAL / "search-metrics.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    for m, v in out["modes"].items():
        print(m, f"hit@6={v['hit@6']:.3f} mrr={v['mrr']:.3f}")


if __name__ == "__main__":
    {"estimate": estimate, "answers": run_answers, "search": search_metrics}[sys.argv[1]]()
