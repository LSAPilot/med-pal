"""Build eval/README.md and its two charts (eval/plots/) from the data in eval/ (no API, deterministic).

Usage: uv run python scripts/build_evaluation.py
Needs eval/judgements-resolved.jsonl (scripts/judge_packet.py resolve). Hand-written examples live in eval/examples.md,
the hand-written threshold reasoning in THRESHOLD_NOTE below.
"""
from collections import Counter
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from eval_data import EVAL, LABEL, SYSTEMS, load  # noqa: E402

COLOR = {"rag": "#1f77b4", "haiku-no-rag": "#aaaaaa", "sonnet-no-rag": "#555555"}

THRESHOLD_NOTE = """\
**Proposal: 0.70** (current provisional value: 0.60). Not applied to `Config`, not synced to the Space.

Reasoning:
- With-answer questions have a best cosine of at least 0.77 (median 0.84); without-answer questions reach 0.65 to 0.76. The ranges touch (gap of only 0.014 between q29 at 0.770 and q27 at 0.755). A threshold of 0.76 would separate all 30 questions perfectly, but it is fitted to this set and leaves no margin: a slightly weaker real question would be blocked wrongly.
- 0.70 blocks no answerable question (margin 0.07 below the weakest one) and stops clear off-topic queries (q25 DiGA at 0.654) before the LLM call. Near-miss questions (0.73 to 0.76: IEC 62304, FDA, Cyber Resilience Act, VAT) pass the threshold and are left to the model, which refused or named the gap correctly in 5/5 cases here.
- 0.60 (current) blocked none of the five, so it only protects against nonsense; raising to 0.70 costs nothing on this set.
- The threshold is a cheap pre-filter, not the main protection against hallucination. The model's `found` decision and the ID check did that work in this run. Re-check with more near-miss questions before moving higher.
"""

data = load()
qs, ans, sm = data.questions, data.answers, data.search
has_answer, no_answer, followups = data.has_answer, data.no_answer, data.followups
sc = data.scores


def table_main():
    rows = ["| Metric | " + " | ".join(LABEL[s] for s in SYSTEMS) + " |", "|---|" + "---|" * len(SYSTEMS)]

    def row(name, f):
        rows.append(f"| {name} | " + " | ".join(f(s) for s in SYSTEMS) + " |")

    row(f"Correctness, mean 0-2 ({len(has_answer)} questions with answer)", lambda s: f"{mean(sc(s, has_answer, 'correctness')):.2f}")
    row("  of which fully correct (2)", lambda s: f"{sum(v == 2 for v in sc(s, has_answer, 'correctness'))}/{len(has_answer)}")
    row("Grounding, mean 0-2 (with answer)", lambda s: f"{mean(sc(s, has_answer, 'grounding')):.2f}")
    def cit(s):
        c = Counter(sc(s, has_answer, "citation"))
        return f"{c['yes']} yes / {c['partly']} partly / {c['no']} no / {c['none']} none"
    row("Citation correctness (with answer)", cit)
    def ref(s):
        c = Counter(sc(s, no_answer, "refusal"))
        return f"{c['correctly_refused']} refused / {c['partial_with_named_gap']} partial+gap / {c['hallucinated']} hallucinated"
    row(f"No-answer questions ({len(no_answer)})", ref)
    row(f"Follow-up resolved ({len(followups)} turns)", lambda s: f"{sum(bool(v) for v in sc(s, followups, 'followup_resolved'))}/{len(followups)}")
    row("Brevity/usefulness, mean 0-2 (all 30)", lambda s: f"{mean(sc(s, list(qs), 'usefulness')):.2f}")
    row("Correctness on no-answer questions, mean 0-2", lambda s: f"{mean(sc(s, no_answer, 'correctness')):.2f}")
    return "\n".join(rows)


def table_cost():
    rows = ["| System | Model | Input tokens | Output tokens | Cost (USD) | per question |", "|---|---|---|---|---|---|"]
    model = {"rag": "claude-haiku-5-5", "haiku-no-rag": "claude-haiku-5-5", "sonnet-no-rag": "claude-sonnet-5-5"}
    for s in SYSTEMS:
        r = list(ans[s].values())
        c = sum(x["cost_usd"] for x in r)
        rows.append(f"| {LABEL[s]} | {model[s]} | {sum(x['input_tokens'] for x in r)} | {sum(x['output_tokens'] for x in r)} | {c:.3f} | {c / len(r):.4f} |")
    total = sum(x["cost_usd"] for s in SYSTEMS for x in ans[s].values())
    rows.append(f"| **Total** | | | | **{total:.3f}** | |")
    return "\n".join(rows), total


def threshold_section():
    rag = ans["rag"]
    pos = sorted((rag[i]["best_cosine"], i) for i in has_answer)
    neg = sorted((rag[i]["best_cosine"], i) for i in no_answer)
    lo_pos, hi_neg = pos[0], neg[-1]
    gap = lo_pos[0] - hi_neg[0]
    mid = round((lo_pos[0] + hi_neg[0]) / 2, 2)
    lines = [
        "| Group | n | min | median | max |", "|---|---|---|---|---|",
        f"| With answer | {len(pos)} | {pos[0][0]:.3f} ({pos[0][1]}) | {pos[len(pos)//2][0]:.3f} | {pos[-1][0]:.3f} |",
        f"| Without answer | {len(neg)} | {neg[0][0]:.3f} ({neg[0][1]}) | {neg[len(neg)//2][0]:.3f} | {neg[-1][0]:.3f} ({neg[-1][1]}) |",
        "", "Best cosine of the hybrid top-6 for the rewritten query (as in production). Without-answer questions: "
        + ", ".join(f"{i} {c:.3f}" for c, i in neg) + ".", "",
        "| Threshold | with-answer questions wrongly blocked | no-answer questions blocked before the LLM |", "|---|---|---|",
    ]
    for t in (0.60, 0.70, 0.75, mid, 0.78):
        lines.append(f"| {t:.2f} | {sum(c < t for c, _ in pos)}/{len(pos)} | {sum(c < t for c, _ in neg)}/{len(neg)} |")
    return "\n".join(lines), mid, gap, lo_pos, hi_neg


def charts():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    vals = [mean(sc(s, has_answer, "correctness")) / 2 * 100 for s in SYSTEMS]
    bars = ax.bar([LABEL[s].replace(" (", "\n(").replace(", no", ",\nno") for s in SYSTEMS], vals, color=[COLOR[s] for s in SYSTEMS])
    ax.bar_label(bars, fmt="%.0f%%")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Correctness (share of max. score)")
    ax.set_title(f"Correctness on {len(has_answer)} answerable questions", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(EVAL / "plots/eval-correctness.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3.6))
    modes = list(sm["modes"])
    x = range(len(modes))
    w = 0.38
    b1 = ax.bar([i - w / 2 for i in x], [sm["modes"][m]["hit@6"] for m in modes], w, label="Hit@6", color="#1f77b4")
    b2 = ax.bar([i + w / 2 for i in x], [sm["modes"][m]["mrr"] for m in modes], w, label="MRR", color="#aaaaaa")
    ax.bar_label(b1, fmt="%.2f")
    ax.bar_label(b2, fmt="%.2f")
    ax.set_xticks(list(x), modes)
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Search quality per mode ({sm['n']} questions with gold chunks)", fontsize=10)
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(EVAL / "plots/eval-search.png", dpi=160)
    plt.close(fig)


charts()
cost_tbl, total = table_cost()
thr_tbl, mid, gap, lo_pos, hi_neg = threshold_section()
search_tbl = "\n".join(
    ["| Mode | Hit@6 | MRR |", "|---|---|---|"]
    + [f"| {m} | {v['hit@6']:.2f} | {v['mrr']:.3f} |" for m, v in sm["modes"].items()]
)
examples = (EVAL / "examples.md").read_text(encoding="utf-8") if (EVAL / "examples.md").exists() else "_(none yet)_"

doc = f"""# Evaluation: does RAG help?

30 questions ([`questions.jsonl`](questions.jsonl): 22 answerable, 5 without answer in the sources, 1 follow-up session with 3 turns; German and English). Three systems answered every question in the same setup (same answer instruction, effort `low`, `max_tokens` 2000, follow-ups with the system's own earlier answers as history):

1. **RAG**: our system (`answer_question`: query rewriting, hybrid search, threshold, Haiku with JSON, ID check),
2. **Haiku without RAG** (`claude-haiku-5-5`),
3. **Sonnet without RAG** (`claude-sonnet-5-5`).

A judge (Claude subagent with fresh context, no API) rated the answers blind: answers appeared as A/B/C in random order per question, system names were hidden. Everything is reproducible from this folder (`scripts/run_eval.py`, `scripts/judge_packet.py`, `scripts/build_evaluation.py`); more charts in [`plots/`](plots/).

![Correctness per system](plots/eval-correctness.png)

## Answer quality

{table_main()}

Scales: correctness, grounding, usefulness 0 to 2 (judge schema). The judge saw the RAG answer text only, not its source list, so grounding is judged against the original text for all systems alike.

## Search (no LLM)

Hit@6 and MRR on the {sm['n']} questions that have gold chunks (22 answerable + 3 follow-ups). A hit means a gold chunk (or a sub-chunk `-sN` of it) is in the top 6. The query is the English rewrite that Haiku produced in the RAG run, as in production.

{search_tbl}

![Search per mode](plots/eval-search.png)

## Cost

{cost_tbl}

**Caveat:** The Sonnet 5.5 price could not be looked up in the headless run. 3/15 USD per million tokens (input/output) was assumed as a conservative figure, so the real Sonnet cost may be lower. Haiku uses the prices from `Config`. Estimate before the run: `uv run python scripts/run_eval.py estimate`.

## Threshold for "nothing found" (proposal, not applied)

{thr_tbl}

{THRESHOLD_NOTE}

## Examples

{examples}

## Limits of the study
- Small set (30 questions, only 5 without answer, one follow-up session of 3 turns). Results are tendencies, not statistically sound differences; one question changes a percentage by 3 to 4 points.
- Claude generates the questions and judges Claude's answers. Mitigated by a separate reviewer, binding to the original text and blind judging, but not ruled out (a judge may favour its own style or share blind spots with the generator).
- No human experts with legal training rated anything.
- The judge's grounding score for the no-RAG systems is relative to the supplied source text, not to the full law. The Sonnet price is an assumption (see Cost).
- The threshold was calibrated on the same 30 questions it is evaluated on (see above).
"""
(EVAL / "README.md").write_text(doc, encoding="utf-8")
print("written", total, "threshold mid", mid, "gap", round(gap, 3))
