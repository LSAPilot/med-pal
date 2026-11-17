"""Precompute the example answers shown in the app (section 4). Calls the Claude API once per example and language.

    uv run python scripts/precompute_examples.py

Output: data/examples.json (tracked in git, shipped to the Space by scripts/build_space.py).
Re-run after changing the prompt, the model or the index. Costs well below one US cent in total.
"""
import json
import logging
from dataclasses import asdict

from regulatory_helper.generate import Config
from regulatory_helper.limits import LimitConfig
from regulatory_helper.service import EXAMPLE_MODE, EXAMPLES_PATH, Service

EXAMPLES = [
    ("lab-values", "Muss meine Software, die Laborwerte nur anzeigt, nach MDR als Medizinprodukt eingestuft werden?",
     "Does my software that only displays laboratory values have to be qualified as a medical device under the MDR?"),
    ("ai-diagnosis", "Welche Pflichten habe ich, wenn mein Produkt ein KI-Modell zur Diagnoseunterstützung enthält?",
     "What obligations do I have if my product contains an AI model for diagnostic support?"),
    ("health-data-training", "Darf ich Gesundheitsdaten für das Training eines Modells verwenden?",
     "May I use health data to train a model?"),
    ("rule-11", "In welche Risikoklasse fällt Software, die Entscheidungen für Diagnose oder Therapie unterstützt?",
     "Which risk class does software that supports diagnostic or therapeutic decisions fall into?"),
    ("manufacturer-duties", "Welche allgemeinen Pflichten haben Hersteller von Medizinprodukten nach der MDR?",
     "What are the general obligations of manufacturers of medical devices under the MDR?"),
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    svc = Service(Config(), LimitConfig(daily_limit=10**6, visitor_limit=10**6, cache_size=0), examples=[])
    out = []
    for ex_id, de, en in EXAMPLES:
        replies = {}
        for lang, q in (("de", de), ("en", en)):
            r = svc.ask(q, [], lang, EXAMPLE_MODE, "precompute")
            assert r.status == "ok" and r.sources, f"example {ex_id}/{lang} did not produce a sourced answer: {r.status}"
            replies[lang] = {k: v for k, v in asdict(r).items() if k != "status"}
        out.append({"id": ex_id, "question": {"de": de, "en": en}, "replies": replies})
    EXAMPLES_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} examples to {EXAMPLES_PATH}; total cost ${svc.stats.cost_usd:.4f}")


if __name__ == "__main__":
    main()
