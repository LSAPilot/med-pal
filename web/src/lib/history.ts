import { isAnswerStatus, trimHistory, type Mode, type Reply, type Turn } from "./api";

/** One question with its reply, as shown in the chat. */
export interface Entry {
  question: string;
  reply: Reply;
  /** Search mode this question was asked with (shown under the hood). Optional for entries stored earlier. */
  mode?: Mode;
}

/**
 * The history to send with the next question: real answers only (also "not in the sources"), last 3 rounds.
 * An `invalid_output` reply carries only the error message, not an answer, so it is left out.
 */
export function turnsFromEntries(entries: readonly Entry[]): Turn[] {
  const turns = entries
    .filter((e) => isAnswerStatus(e.reply.status) && e.reply.reason !== "invalid_output")
    .map((e) => ({ question: e.question, answer: e.reply.text }));
  return trimHistory(turns);
}
