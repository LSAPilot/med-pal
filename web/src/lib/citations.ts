/**
 * Inline source markers in an answer text. The backend (`link_citations` in `src/regulatory_helper/generate.py`)
 * writes `[n]`, where n is the 1-based position in the reply's `sources`: `[2]` means `sources[1]`.
 */

export type Segment =
  | { type: "text"; text: string }
  | { type: "cite"; /** 1-based number as written in the text */ n: number };

const MARKER = /\[(\d{1,3})\]/g;

/**
 * Split one piece of answer text into plain text and citation markers. Only `[n]` with 1 <= n <= sourceCount is a
 * citation; every other bracket (`[7]` without a seventh source, `[...]`, old-style `[MDR Art. 2(1)]`) stays plain
 * text, so the text itself is never changed or lost.
 */
export function splitCitations(text: string, sourceCount: number): Segment[] {
  const out: Segment[] = [];
  let last = 0;
  for (const m of text.matchAll(MARKER)) {
    const n = Number(m[1]);
    if (n < 1 || n > sourceCount) continue;
    const start = m.index ?? 0;
    if (start > last) out.push({ type: "text", text: text.slice(last, start) });
    out.push({ type: "cite", n });
    last = start + m[0].length;
  }
  if (last < text.length) out.push({ type: "text", text: text.slice(last) });
  return out;
}
