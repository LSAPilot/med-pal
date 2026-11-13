import { describe, expect, it } from "vitest";
import { splitCitations } from "./citations";

describe("splitCitations", () => {
  it("returns plain text as one segment", () => {
    expect(splitCitations("no markers", 2)).toEqual([{ type: "text", text: "no markers" }]);
    expect(splitCitations("", 2)).toEqual([]);
  });

  it("splits at markers that match a source", () => {
    expect(splitCitations("A [1]. B [2][1].", 2)).toEqual([
      { type: "text", text: "A " },
      { type: "cite", n: 1 },
      { type: "text", text: ". B " },
      { type: "cite", n: 2 },
      { type: "cite", n: 1 },
      { type: "text", text: "." },
    ]);
  });

  it("leaves unknown markers and other brackets as text", () => {
    const text = "A [0] B [3] C [...] D [MDR Art. 2(1)] E [recital of the original 2017 text] F [1234]";
    expect(splitCitations(text, 2)).toEqual([{ type: "text", text }]);
  });

  it("keeps every character: segments joined give the original text", () => {
    const text = "Is [1] and [9] and [2].";
    const joined = splitCitations(text, 2)
      .map((s) => (s.type === "text" ? s.text : `[${s.n}]`))
      .join("");
    expect(joined).toBe(text);
  });

  it("treats every marker as unknown when there are no sources", () => {
    expect(splitCitations("A [1]", 0)).toEqual([{ type: "text", text: "A [1]" }]);
  });
});
