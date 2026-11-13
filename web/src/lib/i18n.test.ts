import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { STRINGS } from "./i18n";

/** Like `normalize_question` in `src/regulatory_helper/service.py` (whitespace collapsed, lower case). */
const normalize = (q: string) => q.split(/\s+/).filter(Boolean).join(" ").toLowerCase();

interface Example {
  question: Record<string, string>;
  replies: Record<string, unknown>;
}

const examples: Example[] = JSON.parse(
  readFileSync(new URL("../../../data/examples.json", import.meta.url), "utf8"),
);

describe("example questions", () => {
  // A start-view example is only free (no API call, no limit) if the backend has a precomputed reply for exactly
  // that text; otherwise every click on it would cost money.
  for (const lang of ["de", "en"] as const) {
    it(`every ${lang} example has a precomputed reply in data/examples.json`, () => {
      const known = new Set(
        examples.filter((e) => lang in e.replies && e.question[lang]).map((e) => normalize(e.question[lang])),
      );
      for (const ex of STRINGS[lang].examples) expect(known).toContain(normalize(ex.question));
    });
  }
});
