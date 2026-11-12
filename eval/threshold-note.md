**Proposal: 0.70** (current provisional value: 0.60). Not applied to `Config`, not synced to the Space.

Reasoning:
- With-answer questions have a best cosine of at least 0.77 (median 0.84); without-answer questions reach 0.65 to 0.76. The ranges touch (gap of only 0.014 between q29 at 0.770 and q27 at 0.755). A threshold of 0.76 would separate all 30 questions perfectly, but it is fitted to this set and leaves no margin: a slightly weaker real question would be blocked wrongly.
- 0.70 blocks no answerable question (margin 0.07 below the weakest one) and stops clear off-topic queries (q25 DiGA at 0.654) before the LLM call. Near-miss questions (0.73 to 0.76: IEC 62304, FDA, Cyber Resilience Act, VAT) pass the threshold and are left to the model, which refused or named the gap correctly in 5/5 cases here.
- 0.60 (current) blocked none of the five, so it only protects against nonsense; raising to 0.70 costs nothing on this set.
- The threshold is a cheap pre-filter, not the main protection against hallucination. The model's `found` decision and the ID check did that work in this run. Re-check with more near-miss questions before moving higher.
