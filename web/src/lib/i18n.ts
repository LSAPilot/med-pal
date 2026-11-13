import type { Lang, Mode } from "./api";

/** Title and hint of a message box. */
export interface Message {
  title: string;
  hint?: string;
}

export interface Strings {
  appName: string;
  tagline: string;
  langLabel: string;
  notices: { advice: string; iec: string; privacy: string };
  noticesLabel: string;

  startTitle: string;
  startLead: string;
  examplesLabel: string;
  /** `corpus` is the short law name shown as a tag. */
  examples: { corpus: string; question: string }[];
  corpusNote: string;

  composerLabel: string;
  placeholder: string;
  send: string;
  sending: string;
  newConversation: string;
  counterOver: string;
  keyHint: string;
  modeLabel: string;
  modes: Record<Mode, { label: string; hint: string }>;

  yourQuestion: string;
  loadingSearch: string;
  loadingWarmup: string;
  loadingWarmupHint: string;
  cached: string;
  example: string;

  sources: string;
  sourceOriginal: string;
  sourceOpen: string;
  newWindow: string;
  showMore: string;
  showLess: string;
  underTheHood: string;
  hoodMode: string;
  hoodQuery: string;
  hoodQueryNone: string;
  hoodBest: string;
  hoodHits: string;
  hoodNoHits: string;
  hoodScoreNote: string;
  colRank: string;
  colCitation: string;
  colScore: string;
  colSimilarity: string;
  modeFull: Record<Mode, string>;

  /** found=false with reason below_threshold / model_no_answer (honest refusal, not an error). */
  belowThreshold: Message;
  modelNoAnswer: Message;
  /** reason invalid_output: the model's answer was unusable. */
  invalidOutput: Message;
  visitorLimit: Message;
  dailyLimit: Message;
  tooLong: Message;
  empty: Message;
  error: Message;
}

const de: Strings = {
  appName: "med-pal",
  tagline: "Antworten zu MDR, DSGVO und AI Act, belegt mit dem Originaltext",
  langLabel: "Sprache",
  noticesLabel: "Wichtige Hinweise",
  notices: {
    advice: "Keine Rechtsberatung",
    iec: "IEC 62304 nicht enthalten",
    privacy: "Fragen werden nicht gespeichert",
  },

  startTitle: "Was möchtest du zur Regulierung wissen?",
  startLead:
    "Jede Antwort stützt sich auf den Wortlaut der Verordnungen und nennt die Fundstelle. Findet sich dort nichts Belastbares, antwortet med-pal nicht.",
  examplesLabel: "Beispielfragen",
  examples: [
    { corpus: "MDR", question: "In welche Risikoklasse fällt Software, die Entscheidungen für Diagnose oder Therapie unterstützt?" },
    { corpus: "MDR", question: "Welche allgemeinen Pflichten haben Hersteller von Medizinprodukten nach der MDR?" },
    { corpus: "DSGVO", question: "Darf ich Gesundheitsdaten für das Training eines Modells verwenden?" },
    { corpus: "AI Act", question: "Welche Pflichten habe ich, wenn mein Produkt ein KI-Modell zur Diagnoseunterstützung enthält?" },
  ],
  corpusNote:
    "Wissensbasis: MDR (EU 2017/745, konsolidiert, Stand 1.1.2026), DSGVO (EU 2016/679) und AI Act (EU 2024/1689), jeweils im englischen Originaltext von EUR-Lex.",

  composerLabel: "Deine Frage",
  placeholder: "Frage zu MDR, DSGVO oder AI Act",
  send: "Frage stellen",
  sending: "Suche läuft",
  newConversation: "Neues Gespräch",
  counterOver: "Zu lang, bitte kürzen",
  keyHint: "Enter sendet, Umschalt+Enter macht eine neue Zeile",
  modeLabel: "Suchmodus",
  modes: {
    bm25: { label: "BM25", hint: "Stichwortsuche" },
    vector: { label: "Vektor", hint: "Suche nach Bedeutung" },
    hybrid: { label: "Hybrid", hint: "Stichwort und Bedeutung kombiniert" },
  },

  yourQuestion: "Deine Frage",
  loadingSearch: "Suche in den Quellen …",
  loadingWarmup: "Backend wird geweckt …",
  loadingWarmupHint: "Nach einer Pause braucht der erste Aufruf etwas länger.",
  cached: "Aus dem Zwischenspeicher",
  example: "Vorbereitete Beispielantwort",

  sources: "Quellen",
  sourceOriginal: "Originaltext, Englisch",
  sourceOpen: "Auf EUR-Lex lesen",
  newWindow: "(öffnet in neuem Fenster)",
  showMore: "Mehr anzeigen",
  showLess: "Weniger anzeigen",
  underTheHood: "Blick unter die Haube",
  hoodMode: "Suchmodus",
  hoodQuery: "Umformulierte Suchanfrage",
  hoodQueryNone: "keine",
  hoodBest: "Beste Ähnlichkeit",
  hoodHits: "Treffer",
  hoodNoHits: "Keine Treffer.",
  hoodScoreNote: "Der Score hängt vom Modus ab: BM25-Wert, Cosinus-Ähnlichkeit oder Rangwert der Hybrid-Suche.",
  colRank: "Rang",
  colCitation: "Fundstelle",
  colScore: "Score",
  colSimilarity: "Ähnlichkeit",
  modeFull: {
    bm25: "BM25 (Stichwortsuche)",
    vector: "Vektorsuche (Bedeutung)",
    hybrid: "Hybrid (BM25 und Vektor)",
  },

  belowThreshold: {
    title: "Dazu stehen keine belastbaren Aussagen in den Quellen",
    hint: "Die Suche hat keine ausreichend passende Stelle gefunden. Das ist kein Fehler: med-pal antwortet nur, wenn der Wortlaut es trägt. Unter der Haube siehst du, was die Suche geliefert hat.",
  },
  modelNoAnswer: {
    title: "Die gefundenen Stellen beantworten die Frage nicht",
    hint: "Die Suche hat Passagen gefunden, aber keine davon trägt eine belegte Antwort. Das ist kein Fehler. Formuliere die Frage konkreter oder wähle einen anderen Suchmodus.",
  },
  invalidOutput: {
    title: "Die Antwort konnte nicht erzeugt werden",
    hint: "Das Modell hat keine auswertbare Antwort geliefert. Versuche es noch einmal.",
  },
  visitorLimit: {
    title: "Du hast das Fragenlimit erreicht",
    hint: "Das Limit gilt pro Stunde. Versuche es später noch einmal.",
  },
  dailyLimit: {
    title: "Das Tageslimit ist erreicht",
    hint: "Es schützt das Budget dieser Demo. Morgen geht es weiter.",
  },
  tooLong: {
    title: "Die Frage ist zu lang",
    hint: "Fasse sie auf höchstens 500 Zeichen zusammen.",
  },
  empty: {
    title: "Keine Frage eingegeben",
    hint: "Schreibe eine Frage oder wähle ein Beispiel.",
  },
  error: {
    title: "Das hat nicht geklappt",
    hint: "Prüfe die Verbindung und versuche es gleich noch einmal.",
  },
};

const en: Strings = {
  appName: "med-pal",
  tagline: "Answers on the MDR, GDPR and AI Act, backed by the original text",
  langLabel: "Language",
  noticesLabel: "Important notices",
  notices: {
    advice: "Not legal advice",
    iec: "IEC 62304 not included",
    privacy: "Questions are not stored",
  },

  startTitle: "What would you like to know about the regulations?",
  startLead:
    "Every answer rests on the wording of the regulations and names where it was found. If nothing reliable turns up, med-pal does not answer.",
  examplesLabel: "Example questions",
  examples: [
    { corpus: "MDR", question: "Which risk class does software that supports diagnostic or therapeutic decisions fall into?" },
    { corpus: "MDR", question: "What are the general obligations of manufacturers of medical devices under the MDR?" },
    { corpus: "GDPR", question: "May I use health data to train a model?" },
    { corpus: "AI Act", question: "What obligations do I have if my product contains an AI model for diagnostic support?" },
  ],
  corpusNote:
    "Knowledge base: MDR (EU 2017/745, consolidated, as of 1 Jan 2026), GDPR (EU 2016/679) and AI Act (EU 2024/1689), each in the English original from EUR-Lex.",

  composerLabel: "Your question",
  placeholder: "Ask about MDR, GDPR or AI Act",
  send: "Ask question",
  sending: "Searching",
  newConversation: "New conversation",
  counterOver: "Too long, please shorten",
  keyHint: "Enter sends, Shift+Enter adds a line",
  modeLabel: "Search mode",
  modes: {
    bm25: { label: "BM25", hint: "Keyword search" },
    vector: { label: "Vector", hint: "Search by meaning" },
    hybrid: { label: "Hybrid", hint: "Keywords and meaning combined" },
  },

  yourQuestion: "Your question",
  loadingSearch: "Searching the sources …",
  loadingWarmup: "Waking up the backend …",
  loadingWarmupHint: "After a pause the first request takes a little longer.",
  cached: "From cache",
  example: "Prepared example answer",

  sources: "Sources",
  sourceOriginal: "Original text, English",
  sourceOpen: "Read on EUR-Lex",
  newWindow: "(opens in a new window)",
  showMore: "Show more",
  showLess: "Show less",
  underTheHood: "Under the hood",
  hoodMode: "Search mode",
  hoodQuery: "Rewritten search query",
  hoodQueryNone: "none",
  hoodBest: "Best similarity",
  hoodHits: "Hits",
  hoodNoHits: "No hits.",
  hoodScoreNote: "The score depends on the mode: BM25 value, cosine similarity or rank value of the hybrid search.",
  colRank: "Rank",
  colCitation: "Citation",
  colScore: "Score",
  colSimilarity: "Similarity",
  modeFull: {
    bm25: "BM25 (keyword search)",
    vector: "Vector search (meaning)",
    hybrid: "Hybrid (BM25 and vector)",
  },

  belowThreshold: {
    title: "The sources contain nothing reliable on this",
    hint: "The search found no passage that fits well enough. This is not an error: med-pal only answers when the wording supports it. Under the hood you can see what the search returned.",
  },
  modelNoAnswer: {
    title: "The passages found do not answer the question",
    hint: "The search found passages, but none of them supports a sourced answer. This is not an error. Make the question more specific or try another search mode.",
  },
  invalidOutput: {
    title: "The answer could not be generated",
    hint: "The model did not return a usable answer. Please try again.",
  },
  visitorLimit: {
    title: "You have reached the question limit",
    hint: "The limit applies per hour. Please try again later.",
  },
  dailyLimit: {
    title: "The daily limit is reached",
    hint: "It protects the budget of this demo. Come back tomorrow.",
  },
  tooLong: {
    title: "The question is too long",
    hint: "Shorten it to 500 characters or fewer.",
  },
  empty: {
    title: "No question entered",
    hint: "Type a question or pick an example.",
  },
  error: {
    title: "That did not work",
    hint: "Check your connection and try again in a moment.",
  },
};

export const STRINGS: Record<Lang, Strings> = { de, en };
