"""Small hand-made query set (English, as produced by query rewriting) with the chunks that should be found.

A hit counts if the chunk ID equals a gold ID or starts with it followed by '-' or '.'
(so "GDPR-9" covers GDPR-9-1, GDPR-9-2, ... and "MDR-ANNEX-I-17" covers its sub points).
This set is only for choosing the embedding model and for the examples in docs/search-examples.md.
It is NOT the validation set of section 5.
"""

QUERIES = [
    # exact / reference style
    ("Rule 11 software classification", ["MDR-ANNEX-VIII-6.3"]),
    ("Article 10 general obligations of manufacturers", ["MDR-10"]),
    ("GDPR Article 9 special categories of personal data", ["GDPR-9"]),
    ("Annex IV technical documentation high-risk AI system", ["AIACT-ANNEX-IV"]),
    # content style
    ("which class is software that provides information for diagnosis or therapeutic decisions", ["MDR-ANNEX-VIII-6.3"]),
    ("definition of medical device including software", ["MDR-2-1"]),
    ("processing of data concerning health is prohibited unless explicit consent", ["GDPR-9"]),
    ("right of the data subject to erasure of personal data", ["GDPR-17"]),
    ("when is an AI system considered high-risk", ["AIACT-6"]),
    ("transparency obligations for AI systems that interact with natural persons", ["AIACT-50"]),
    ("automated individual decision-making including profiling", ["GDPR-22"]),
    ("manufacturer must establish a risk management system", ["MDR-10-2", "MDR-ANNEX-I-3"]),
    ("safety requirements for electronic programmable systems and software", ["MDR-ANNEX-I-17"]),
    ("UDI assignment criteria for device software", ["MDR-ANNEX-VI-6.5"]),
    ("safeguards for processing personal data for scientific research", ["GDPR-89"]),
    ("clinical evaluation of a medical device", ["MDR-61"]),
]


def is_hit(chunk_id: str, gold: list[str]) -> bool:
    return any(chunk_id == g or chunk_id.startswith(g + "-") or chunk_id.startswith(g + ".") for g in gold)
