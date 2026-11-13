import { afterEach, describe, expect, it, vi } from "vitest";
import { STATUSES, ask, normalizeReply, trimHistory, type Reply, type Turn } from "./api";
import { turnsFromEntries } from "./history";

const KEYS = ["text", "status", "found", "reason", "sources", "search_query", "hits", "best_cosine"];

afterEach(() => vi.unstubAllEnvs());

describe("trimHistory", () => {
  it("keeps only the last 3 rounds", () => {
    const h: Turn[] = Array.from({ length: 5 }, (_, i) => ({ question: `q${i}`, answer: `a${i}` }));
    expect(trimHistory(h).map((t) => t.question)).toEqual(["q2", "q3", "q4"]);
  });
});

describe("normalizeReply", () => {
  it("turns garbage into an error reply with all 8 keys", () => {
    for (const bad of [null, undefined, 42, "x", [], {}, { status: "weird" }, { data: [] }]) {
      const r = normalizeReply(bad);
      expect(Object.keys(r).sort()).toEqual([...KEYS].sort());
      expect(r.status).toBe("error");
      expect(r.found).toBe(false);
    }
  });
  it("unwraps the gradio envelope and repairs bad fields", () => {
    const r = normalizeReply({
      data: [{ status: "ok", text: "hi", found: true, sources: [null, { id: "a" }], hits: "nope", best_cosine: "x" }],
    });
    expect(r.status).toBe("ok");
    expect(r.sources).toHaveLength(1);
    expect(r.sources[0].quote).toBe("");
    expect(r.hits).toEqual([]);
    expect(r.best_cosine).toBeNull();
  });
  it("keeps every reason the backend can send", () => {
    for (const reason of ["below_threshold", "model_no_answer", "invalid_output"]) {
      expect(normalizeReply({ status: "ok", found: false, reason }).reason).toBe(reason);
    }
  });
});

describe("turnsFromEntries", () => {
  const entry = (status: Reply["status"], i: number) => ({
    question: `q${i}`,
    reply: { ...normalizeReply({ status, text: `a${i}` }) },
  });
  it("skips non-answers and keeps the last 3", () => {
    const turns = turnsFromEntries([entry("ok", 1), entry("error", 2), entry("cached", 3), entry("ok", 4), entry("ok", 5)]);
    expect(turns.map((t) => t.question)).toEqual(["q3", "q4", "q5"]);
  });
});

describe("ask in mock mode", () => {
  const cases: [string, string, Partial<Reply>][] = [
    ["Wie wird Software klassifiziert?", "ok", { found: true, reason: "answered" }],
    ["mock:cached", "cached", { found: true }],
    ["mock:example", "example", { found: true }],
    ["mock:notfound", "ok", { found: false, reason: "below_threshold" }],
    ["mock:invalid", "ok", { found: false, reason: "invalid_output" }],
    ["mock:visitor", "visitor_limit", { found: false }],
    ["mock:daily", "daily_limit", { found: false }],
    ["x".repeat(501), "too_long", { found: false }],
    ["   ", "empty", { found: false }],
    ["mock:error", "error", { found: false }],
  ];
  it.each(cases)("%s -> %s", async (q, status, extra) => {
    vi.stubEnv("NEXT_PUBLIC_API_MODE", "mock");
    for (const lang of ["de", "en"] as const) {
      const r = await ask(q, [], lang, "hybrid");
      expect(Object.keys(r).sort()).toEqual([...KEYS].sort());
      expect(r.status).toBe(status);
      expect(r).toMatchObject(extra);
      expect(r.text.length).toBeGreaterThan(0);
    }
  });
  it("covers every status", () => {
    expect(new Set(cases.map((c) => c[1]))).toEqual(new Set(STATUSES));
  });
  it("returns an error reply instead of throwing in live mode without a target", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_MODE", "live");
    vi.stubEnv("NEXT_PUBLIC_SPACE_ID", "");
    expect((await ask("q", [], "en", "bm25")).status).toBe("error");
  });
});
