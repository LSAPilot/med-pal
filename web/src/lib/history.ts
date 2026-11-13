import { isAnswerStatus, trimHistory, type Mode, type Reply, type Turn } from "./api";

/** One question with its reply, as shown in the chat. */
export interface Entry {
  question: string;
  reply: Reply;
  /** Search mode this question was asked with (shown under the hood). Optional for entries stored earlier. */
  mode?: Mode;
}

/** The history to send with the next question: real answers only (also "not in the sources"), last 3 rounds. */
export function turnsFromEntries(entries: readonly Entry[]): Turn[] {
  const turns = entries
    .filter((e) => isAnswerStatus(e.reply.status))
    .map((e) => ({ question: e.question, answer: e.reply.text }));
  return trimHistory(turns);
}
