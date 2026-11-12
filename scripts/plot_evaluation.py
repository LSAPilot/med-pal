"""Plot the RAG vs. no-RAG evaluation from eval/ into eval/plots/ (no API, deterministic).

Usage: uv run python scripts/plot_evaluation.py
Complements scripts/build_evaluation.py (which writes the two charts embedded in docs/evaluation.md).
"""
import json
from collections import Counter
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
OUT = EVAL / "plots"
SYSTEMS = ["rag", "haiku-no-rag", "sonnet-no-rag"]
LABEL = {"rag": "RAG (Haiku + search)", "haiku-no-rag": "Haiku, no RAG", "sonnet-no-rag": "Sonnet, no RAG"}
COLOR = {"rag": "#2a78d6", "haiku-no-rag": "#eb6834", "sonnet-no-rag": "#1baf7a"}  # fixed categorical order
MODE_COLOR = {"bm25": "#2a78d6", "vector": "#eb6834", "hybrid": "#1baf7a"}
SCORE_COLOR = {0: "#c5d9f4", 1: "#6ea4e6", 2: "#1c5cad"}  # one-hue ramp for ordinal 0-2
REFUSAL = [  # status colours, always shown with a text label
    ("correctly_refused", "correctly refused", "#0ca30c"),
    ("partial_with_named_gap", "partial, gap named", "#fab219"),
    ("hallucinated", "hallucinated", "#d03b3b"),
]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
    "axes.edgecolor": MUTED, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False,
})


def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


qs = {q["id"]: q for q in jl(EVAL / "questions.jsonl")}
judg = {j["id"]: j["scores"] for j in jl(EVAL / "judgements-resolved.jsonl")}
ans = {s: {r["id"]: r for r in jl(EVAL / "answers" / f"{s}.jsonl")} for s in SYSTEMS}
sm = json.loads((EVAL / "search-metrics.json").read_text())
has_answer = [i for i, q in qs.items() if q["type"] != "no_answer"]
no_answer = [i for i, q in qs.items() if q["type"] == "no_answer"]


def sc(s, ids, key):
    return [judg[i][s][key] for i in ids]


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print("wrote", (OUT / name).relative_to(ROOT))


def quality():
    """Grouped bars: correctness, grounding, usefulness (mean 0-2) per system."""
    metrics = [("correctness", "Correctness", has_answer), ("grounding", "Grounding", has_answer),
               ("usefulness", "Brevity/usefulness", list(qs))]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    w = 0.26
    for k, s in enumerate(SYSTEMS):
        xs = [m + (k - 1) * (w + 0.02) for m in range(len(metrics))]
        bars = ax.bar(xs, [mean(sc(s, ids, key)) for key, _, ids in metrics], w, color=COLOR[s], label=LABEL[s])
        ax.bar_label(bars, fmt="%.2f", fontsize=8, color=INK, padding=2)
    ax.set_xticks(range(len(metrics)), [f"{t}\n(n={len(ids)})" for _, t, ids in metrics])
    ax.set_ylim(0, 2.2)
    ax.set_ylabel("Mean judge score (0-2)")
    ax.grid(axis="x", visible=False)
    ax.set_title("Answer quality per system")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    save(fig, "01-answer-quality.png")


def correctness_distribution():
    """Stacked horizontal bars: how many answerable questions scored 0 / 1 / 2."""
    fig, ax = plt.subplots(figsize=(7, 2.6))
    for y, s in enumerate(reversed(SYSTEMS)):
        c, left = Counter(sc(s, has_answer, "correctness")), 0
        for v in (2, 1, 0):
            if c[v]:
                ax.barh(y, c[v], left=left, color=SCORE_COLOR[v], edgecolor="#fcfcfb", linewidth=2)
                ax.text(left + c[v] / 2, y, str(c[v]), ha="center", va="center", fontsize=8,
                        color="white" if v == 2 else INK)
                left += c[v]
    ax.set_yticks(range(len(SYSTEMS)), [LABEL[s] for s in reversed(SYSTEMS)])
    ax.set_xlim(0, len(has_answer))
    ax.set_xlabel(f"Answerable questions (n={len(has_answer)})")
    ax.grid(axis="y", visible=False)
    ax.set_title("Correctness distribution")
    handles = [plt.Rectangle((0, 0), 1, 1, color=SCORE_COLOR[v]) for v in (2, 1, 0)]
    ax.legend(handles, ["2 = correct", "1 = partly", "0 = wrong"], loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3)
    save(fig, "02-correctness-distribution.png")


def refusals():
    """Stacked bars: behaviour on the questions without an answer in the sources."""
    fig, ax = plt.subplots(figsize=(7, 2.6))
    for y, s in enumerate(reversed(SYSTEMS)):
        c, left = Counter(sc(s, no_answer, "refusal")), 0
        for key, lab, col in REFUSAL:
            if c[key]:
                ax.barh(y, c[key], left=left, color=col, edgecolor="#fcfcfb", linewidth=2)
                ax.text(left + c[key] / 2, y, str(c[key]), ha="center", va="center", fontsize=8,
                        color="white" if key != "partial_with_named_gap" else INK)
                left += c[key]
    ax.set_yticks(range(len(SYSTEMS)), [LABEL[s] for s in reversed(SYSTEMS)])
    ax.set_xlim(0, len(no_answer))
    ax.set_xticks(range(len(no_answer) + 1))
    ax.set_xlabel(f"Questions without an answer in the sources (n={len(no_answer)})")
    ax.grid(axis="y", visible=False)
    ax.set_title("Refusal vs. hallucination")
    handles = [plt.Rectangle((0, 0), 1, 1, color=col) for _, _, col in REFUSAL]
    ax.legend(handles, [lab for _, lab, _ in REFUSAL], loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3)
    save(fig, "03-no-answer-behaviour.png")


def cost_vs_correctness():
    """Scatter: cost per question (log) against mean correctness."""
    fig, ax = plt.subplots(figsize=(6, 3.8))
    for s in SYSTEMS:
        cost = mean(r["cost_usd"] for r in ans[s].values())
        corr = mean(sc(s, has_answer, "correctness"))
        ax.scatter(cost, corr, s=90, color=COLOR[s], edgecolor="#fcfcfb", linewidth=2, zorder=3)
        ax.annotate(f"{LABEL[s]}\n${cost:.4f} / {corr:.2f}", (cost, corr), xytext=(8, -4),
                    textcoords="offset points", fontsize=8, va="top")
    ax.set_xscale("log")
    ax.set_xlim(1e-4, 3e-2)
    ax.set_ylim(1.0, 2.05)
    ax.set_xlabel("Mean cost per question in USD (log scale; Sonnet price assumed)")
    ax.set_ylabel("Mean correctness (0-2)")
    ax.set_title("Cost vs. correctness")
    save(fig, "04-cost-vs-correctness.png")


def search_ranks():
    """Dot plot: rank of the first gold chunk per question and search mode."""
    ids = list(next(iter(sm["modes"].values()))["first_rank"])
    cap = 25  # ranks beyond the cap or misses are drawn at the cap
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for k, (mode, v) in enumerate(sm["modes"].items()):
        xs = [i + (k - 1) * 0.22 for i in range(len(ids))]
        ys = [min(v["first_rank"][q] or cap, cap) for q in ids]
        ax.scatter(xs, ys, s=28, color=MODE_COLOR[mode], edgecolor="#fcfcfb", linewidth=1, zorder=3,
                   label=f"{mode} (Hit@6 {v['hit@6']:.2f}, MRR {v['mrr']:.2f})")
    ax.axhspan(0.5, 6.5, color="#2a78d6", alpha=0.06, zorder=0)
    ax.axhline(6.5, color=MUTED, linewidth=1, linestyle="--")
    ax.text(-0.6, 6.3, "top 6 = passed to the LLM", ha="left", va="bottom", fontsize=8, color=MUTED)
    ax.set_yscale("log")
    ax.set_yticks([1, 2, 3, 6, 10, cap], ["1", "2", "3", "6", "10", f"≥{cap} / miss"])
    ax.minorticks_off()
    ax.invert_yaxis()
    ax.set_xticks(range(len(ids)), ids, rotation=90, fontsize=7)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Rank of first gold chunk")
    ax.set_title(f"Retrieval rank per question ({sm['n']} questions with gold chunks)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=8)
    save(fig, "05-search-ranks.png")


def threshold():
    """Strip plot: best cosine of answerable vs. no-answer questions with threshold candidates."""
    rag = ans["rag"]
    groups = [("With answer", has_answer, "#2a78d6"), ("Without answer", no_answer, "#eb6834")]
    fig, ax = plt.subplots(figsize=(7, 2.6))
    for y, (lab, ids, col) in enumerate(groups):
        xs = [rag[i]["best_cosine"] for i in ids]
        jitter = [((int(i[1:]) % 7) - 3) * 0.04 for i in ids]
        ax.scatter(xs, [y + j for j in jitter], s=32, color=col, edgecolor="#fcfcfb", linewidth=1, zorder=3)
    for t, style in ((0.60, ":"), (0.70, "--")):
        ax.axvline(t, color=MUTED, linestyle=style, linewidth=1)
        ax.text(t, 1.45, f"{t:.2f}" + (" (current)" if t == 0.60 else " (proposed)"),
                ha="center", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(groups)), [f"{lab} (n={len(ids)})" for lab, ids, _ in groups])
    ax.set_ylim(-0.5, 1.7)
    ax.set_xlabel("Best cosine of the retrieved top 6")
    ax.grid(axis="y", visible=False)
    ax.set_title("Similarity threshold for “nothing found”")
    save(fig, "06-threshold.png")


OUT.mkdir(exist_ok=True)
for plot in (quality, correctness_distribution, refusals, cost_vs_correctness, search_ranks, threshold):
    plot()
