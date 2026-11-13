/**
 * Mock backend for UI development without API cost (NEXT_PUBLIC_API_MODE=mock). Only loaded via dynamic import.
 *
 * Deterministic triggers: put one of these keywords anywhere in the question to get that status
 * (case-insensitive). Without a keyword the reply is a normal answer (status "ok").
 *
 *   mock:ok            answered, with sources and hits (default)
 *   mock:cached        same answer, status "cached"
 *   mock:example       answered, status "example" (curated example question)
 *   mock:notfound      status ok, found=false, reason below_threshold (honest "not in the sources")
 *   mock:invalid       status ok, found=false, reason invalid_output
 *   mock:visitor       status visitor_limit
 *   mock:daily         status daily_limit
 *   mock:error         status error
 *
 * "empty" (blank question) and "too_long" (more than 500 characters) are triggered by the input itself.
 * Texts follow `lang` ("de" | "en").
 */
import type { Hit, Lang, Reply, Source } from "./api";

const DELAY_MS = 600;
const MAX_QUESTION_CHARS = 500;

const SOURCES: Source[] = [
  {
    id: "mdr-art-2-1",
    title: "Regulation (EU) 2017/745 (MDR), Article 2: Definitions",
    citation: "MDR Art. 2(1)",
    quote:
      "'medical device' means any instrument, apparatus, appliance, software, implant, reagent, material or other article intended by the manufacturer to be used, alone or in combination, for human beings for one or more of the following specific medical purposes: diagnosis, prevention, monitoring, prediction, prognosis, treatment or alleviation of disease [...]",
    source_url: "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R0745",
  },
  {
    id: "mdr-annex-viii-r11",
    title: "Regulation (EU) 2017/745 (MDR), Annex VIII: Classification rules",
    citation: "MDR Annex VIII, Rule 11",
    quote:
      "Software intended to provide information which is used to take decisions with diagnosis or therapeutic purposes is classified as class IIa, except if such decisions have an impact that may cause death or an irreversible deterioration of a person's state of health, in which case it is in class III [...]",
    source_url: "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R0745",
  },
];

const HITS: Hit[] = [
  { rank: 1, id: "mdr-annex-viii-r11", citation: "MDR Annex VIII, Rule 11", score: 0.0328, cosine: 0.71 },
  { rank: 2, id: "mdr-art-2-1", citation: "MDR Art. 2(1)", score: 0.031, cosine: 0.64 },
  { rank: 3, id: "mdr-annex-viii-r10", citation: "MDR Annex VIII, Rule 10", score: 0.0156, cosine: 0.52 },
];

const TEXT = {
  ok: {
    de: "Software, die Informationen für diagnostische oder therapeutische Entscheidungen liefert, gehört nach Regel 11 in Anhang VIII der MDR in der Regel zur Klasse IIa. Können solche Entscheidungen zum Tod oder zu einer irreversiblen Verschlechterung des Gesundheitszustands führen, gilt Klasse III [MDR Annex VIII, Rule 11]. Ob eine Software überhaupt ein Medizinprodukt ist, richtet sich nach der Definition in Art. 2 Nr. 1 [MDR Art. 2(1)].",
    en: "Software that provides information used for diagnostic or therapeutic decisions is generally class IIa under Rule 11 of Annex VIII MDR. If such decisions can cause death or an irreversible deterioration of health, it is class III [MDR Annex VIII, Rule 11]. Whether software is a medical device at all depends on the definition in Article 2(1) [MDR Art. 2(1)].",
  },
  notfound: {
    de: "Dazu finde ich in den hinterlegten Quellen (MDR und IVDR) nichts Belastbares, deshalb beantworte ich die Frage nicht.",
    en: "I cannot find anything reliable on this in the indexed sources (MDR and IVDR), so I will not answer the question.",
  },
  visitor_limit: {
    de: "Du hast das Limit für Fragen erreicht. Bitte versuche es später erneut.",
    en: "You have reached the question limit. Please try again later.",
  },
  daily_limit: {
    de: "Das Tagesbudget ist aufgebraucht. Bitte versuche es morgen erneut.",
    en: "The daily budget is used up. Please try again tomorrow.",
  },
  too_long: {
    de: "Die Frage ist zu lang (maximal 500 Zeichen).",
    en: "The question is too long (500 characters at most).",
  },
  empty: {
    de: "Bitte stelle eine Frage.",
    en: "Please ask a question.",
  },
  error: {
    de: "Es ist ein Fehler aufgetreten. Bitte versuche es später erneut.",
    en: "Something went wrong. Please try again later.",
  },
} as const;

function base(partial: Partial<Reply>): Reply {
  return {
    text: "",
    status: "ok",
    found: false,
    reason: "answered",
    sources: [],
    search_query: "",
    hits: [],
    best_cosine: null,
    ...partial,
  };
}

function answered(lang: Lang, status: "ok" | "cached" | "example"): Reply {
  return base({
    text: TEXT.ok[lang],
    status,
    found: true,
    reason: "answered",
    sources: SOURCES,
    search_query: "classification of software as medical device Rule 11 Annex VIII",
    hits: HITS,
    best_cosine: 0.71,
  });
}

export function mockReply(question: string, lang: Lang): Reply {
  const q = question.trim().toLowerCase();
  if (!q) return base({ text: TEXT.empty[lang], status: "empty", reason: "empty" });
  if (question.length > MAX_QUESTION_CHARS) {
    return base({ text: TEXT.too_long[lang], status: "too_long", reason: "too_long" });
  }
  if (q.includes("mock:visitor")) {
    return base({ text: TEXT.visitor_limit[lang], status: "visitor_limit", reason: "visitor_limit" });
  }
  if (q.includes("mock:daily")) {
    return base({ text: TEXT.daily_limit[lang], status: "daily_limit", reason: "daily_limit" });
  }
  if (q.includes("mock:error")) {
    return base({ text: TEXT.error[lang], status: "error", reason: "error" });
  }
  if (q.includes("mock:notfound") || q.includes("mock:invalid")) {
    return base({
      text: TEXT.notfound[lang],
      status: "ok",
      found: false,
      reason: q.includes("mock:invalid") ? "invalid_output" : "below_threshold",
      search_query: "iec 62304 software lifecycle requirements",
      hits: HITS.slice(2).map((h) => ({ ...h, rank: 1, cosine: 0.31 })),
      best_cosine: 0.31,
    });
  }
  if (q.includes("mock:cached")) return answered(lang, "cached");
  if (q.includes("mock:example")) return answered(lang, "example");
  return answered(lang, "ok");
}

/** Same call shape as the live `ask` minus history and mode, which do not change mock replies. */
export async function mockAsk(question: string, lang: Lang): Promise<Reply> {
  await new Promise((resolve) => setTimeout(resolve, DELAY_MS));
  return mockReply(question, lang);
}
