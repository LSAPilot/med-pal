/**
 * Client for the Regulatory Copilot backend (`/ask` endpoint of the Gradio Space, see
 * `src/regulatory_helper/app.py` and `service.py` in the repo root).
 *
 * Config (build-time, see `.env.example`):
 *   NEXT_PUBLIC_SPACE_ID  HF space id ("owner/name") or a URL such as "http://127.0.0.1:7860"
 *   NEXT_PUBLIC_API_MODE  "mock" returns canned replies (see mock.ts), anything else talks to the Space
 */
import { Client } from "@gradio/client";

export type Lang = "de" | "en";
export type Mode = "bm25" | "vector" | "hybrid";

export const MODES: readonly Mode[] = ["bm25", "vector", "hybrid"];
export const isLang = (v: unknown): v is Lang => v === "de" || v === "en";
export const isMode = (v: unknown): v is Mode => MODES.includes(v as Mode);

export type Status =
  | "ok"
  | "cached"
  | "example"
  | "visitor_limit"
  | "daily_limit"
  | "too_long"
  | "empty"
  | "error";
export type Reason =
  | "answered"
  | "below_threshold"
  | "model_no_answer"
  | "invalid_output"
  | "visitor_limit"
  | "daily_limit"
  | "too_long"
  | "empty"
  | "error"
  | "invalid_input";

export interface Source {
  id: string;
  title: string;
  citation: string;
  /** English original text of the passage. */
  quote: string;
  source_url: string;
}

export interface Hit {
  rank: number;
  id: string;
  citation: string;
  score: number;
  cosine: number | null;
}

export interface Reply {
  text: string;
  status: Status;
  /** true = answered from the sources; false with status ok/cached = honest "not in the sources". */
  found: boolean;
  reason: Reason;
  sources: Source[];
  search_query: string;
  hits: Hit[];
  best_cosine: number | null;
}

/** One finished round of the conversation, as the backend expects it in `history`. */
export interface Turn {
  question: string;
  answer: string;
}

// Mirror the backend: Config.max_history_turns, LimitConfig.max_question_chars (default; the Space can override it
// with MAX_QUESTION_CHARS, then the backend's too_long reply still applies) and app.MAX_HISTORY_ANSWER_CHARS.
export const MAX_HISTORY_TURNS = 3;
export const MAX_QUESTION_CHARS = 500;
const MAX_HISTORY_ANSWER_CHARS = 12_000;

export const STATUSES: readonly Status[] = [
  "ok", "cached", "example", "visitor_limit", "daily_limit", "too_long", "empty", "error",
];
const REASONS: readonly Reason[] = [
  "answered", "below_threshold", "model_no_answer", "invalid_output", "visitor_limit", "daily_limit",
  "too_long", "empty", "error", "invalid_input",
];

/** Statuses that are real answers (also "not in the sources") and therefore belong in the history. */
export function isAnswerStatus(status: Status): boolean {
  return status === "ok" || status === "cached" || status === "example";
}

/** Keep only the last `MAX_HISTORY_TURNS` rounds and clamp lengths; the backend rejects more. */
export function trimHistory(history: readonly Turn[]): Turn[] {
  return history.slice(-MAX_HISTORY_TURNS).map((t) => ({
    question: t.question.slice(0, MAX_QUESTION_CHARS),
    answer: t.answer.slice(0, MAX_HISTORY_ANSWER_CHARS),
  }));
}

const FALLBACK_TEXT: Record<Lang, string> = {
  de: "Die Anfrage konnte nicht verarbeitet werden. Bitte versuche es später erneut.",
  en: "The request could not be processed. Please try again later.",
};

/** A Reply with status "error", used for network problems and unusable responses. */
export function errorReply(lang: Lang = "de"): Reply {
  return {
    text: FALLBACK_TEXT[lang],
    status: "error",
    found: false,
    reason: "error",
    sources: [],
    search_query: "",
    hits: [],
    best_cosine: null,
  };
}

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const str = (v: unknown): string => (typeof v === "string" ? v : "");
const numOrNull = (v: unknown): number | null =>
  typeof v === "number" && Number.isFinite(v) ? v : null;
/** Only absolute http(s) links are rendered; anything else (e.g. `javascript:`) becomes "". */
const httpUrl = (v: unknown): string => {
  const s = str(v).trim();
  return /^https?:\/\//i.test(s) ? s : "";
};

function normalizeSource(v: unknown): Source | null {
  if (!isRecord(v)) return null;
  return {
    id: str(v.id),
    title: str(v.title),
    citation: str(v.citation),
    quote: str(v.quote),
    source_url: httpUrl(v.source_url),
  };
}

function normalizeHit(v: unknown, i: number): Hit | null {
  if (!isRecord(v)) return null;
  return {
    rank: numOrNull(v.rank) ?? i + 1,
    id: str(v.id),
    citation: str(v.citation),
    score: numOrNull(v.score) ?? 0,
    cosine: numOrNull(v.cosine),
  };
}

/**
 * Turn whatever came back from the backend into a well-formed Reply. Never throws.
 * Accepts the bare reply object or Gradio's `{ data: [reply] }` envelope; anything else becomes an error reply.
 */
export function normalizeReply(value: unknown, lang: Lang = "de"): Reply {
  let raw: unknown = value;
  if (isRecord(raw) && Array.isArray(raw.data) && !("status" in raw)) raw = raw.data[0];
  if (!isRecord(raw) || typeof raw.status !== "string" || !STATUSES.includes(raw.status as Status)) {
    return errorReply(lang);
  }
  const status = raw.status as Status;
  const reason = REASONS.includes(raw.reason as Reason)
    ? (raw.reason as Reason)
    : status === "error"
      ? "error"
      : "answered";
  const text = str(raw.text);
  return {
    text: text || (status === "error" ? FALLBACK_TEXT[lang] : ""),
    status,
    found: raw.found === true,
    reason,
    sources: Array.isArray(raw.sources)
      ? raw.sources.map(normalizeSource).filter((s): s is Source => s !== null)
      : [],
    search_query: str(raw.search_query),
    hits: Array.isArray(raw.hits) ? raw.hits.map(normalizeHit).filter((h): h is Hit => h !== null) : [],
    best_cosine: numOrNull(raw.best_cosine),
  };
}

// --- live mode -------------------------------------------------------------------------------------------

let clientPromise: Promise<Client> | null = null;

/** One shared connection, created on first use. A failed connect or call is not cached, so the next call retries. */
function getClient(): Promise<Client> {
  const target = process.env.NEXT_PUBLIC_SPACE_ID;
  if (!target) return Promise.reject(new Error("NEXT_PUBLIC_SPACE_ID is not set"));
  if (!clientPromise) {
    clientPromise = Client.connect(target).catch((e: unknown) => {
      clientPromise = null;
      throw e;
    });
  }
  return clientPromise;
}

/**
 * Ask one question. Resolves with a Reply in every case: network/connect problems and malformed responses
 * come back as status "error". `history` is trimmed to the last 3 rounds.
 */
export async function ask(
  question: string,
  history: readonly Turn[],
  lang: Lang,
  mode: Mode,
): Promise<Reply> {
  try {
    if (process.env.NEXT_PUBLIC_API_MODE === "mock") {
      const { mockAsk } = await import("./mock");
      return normalizeReply(await mockAsk(question, lang), lang);
    }
    const client = await getClient();
    const result = await client.predict("/ask", {
      question,
      history: trimHistory(history),
      lang,
      mode,
    });
    const data: unknown = result.data;
    return normalizeReply(Array.isArray(data) ? data[0] : data, lang);
  } catch {
    // Drop the shared connection, so the next question connects afresh (e.g. after the Space restarted).
    clientPromise = null;
    return errorReply(lang);
  }
}
