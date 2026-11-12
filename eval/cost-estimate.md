# Cost estimate for section 5b (3 answer runs)

Questions: 30. Effort `low`, `max_tokens` 2000 (rewrite 400) for all systems.

| System | Model | Input tok/question | Output tok/question (incl. thinking) | Expected USD | Worst case USD (all at max_tokens) |
|---|---|---|---|---|---|
| rag | claude-haiku-5-5 | 3800 | 1300 | 0.031 | 0.048 |
| haiku-no-rag | claude-haiku-5-5 | 400 | 1200 | 0.019 | 0.032 |
| sonnet-no-rag | claude-sonnet-5-5 | 400 | 1200 | 0.576 | 0.963 |
| **Total** | | | | **0.626** | 1.043 |

Prices (USD per 1M tokens, input/output): claude-haiku-5-5 0.1/0.5, claude-sonnet-5-5 3.0/15.0.

**Assumption:** Haiku prices come from `Config` (0.10/0.50). The Sonnet 5.5 price could not be looked up (no web access in the headless run), so the classic Sonnet tier 3/15 is assumed as a conservative figure. Output tokens per question (~1200-1300) follow the section 3 measurement (Haiku 750-1000 incl. internal thinking) plus margin; Sonnet at effort `low` should be in the same range.

**Approval rule:** expected total <= 1.00 USD counts as approved. Expected total: 0.626 USD -> approved, runs start.
The worst case (1.04 USD) assumes every answer uses the full `max_tokens` and is not realistic.
