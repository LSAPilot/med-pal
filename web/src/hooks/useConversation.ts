"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ask, normalizeReply, type Lang, type Mode, type Reply } from "@/lib/api";
import { turnsFromEntries, type Entry } from "@/lib/history";

const STORAGE_KEY = "med-pal:conversation";
const MAX_STORED_ENTRIES = 30;

function load(): Entry[] {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((e): e is { question: string; reply: unknown; mode?: unknown } => typeof e?.question === "string")
      .map((e) => ({
        question: e.question,
        reply: normalizeReply(e.reply),
        mode: e.mode === "bm25" || e.mode === "vector" || e.mode === "hybrid" ? e.mode : undefined,
      }));
  } catch {
    return []; // sessionStorage unavailable (private mode, blocked) or corrupted: start empty
  }
}

function save(entries: Entry[]) {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(-MAX_STORED_ENTRIES)));
  } catch {
    /* storage unavailable or full: the conversation just lives in memory */
  }
}

/**
 * Conversation state in the browser only. The history sent to the backend (last 3 real answers) is derived from
 * the entries; the entries are mirrored to sessionStorage so a reload keeps the chat, if storage is available.
 */
export function useConversation() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    // sessionStorage only exists in the browser, so it is read after hydration (not during the static prerender)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEntries(load());
  }, []);

  const history = useMemo(() => turnsFromEntries(entries), [entries]);

  const send = useCallback(
    async (question: string, lang: Lang, mode: Mode): Promise<Reply> => {
      setPending(true);
      try {
        const reply = await ask(question, history, lang, mode);
        setEntries((prev) => {
          const next = [...prev, { question, reply, mode }];
          save(next);
          return next;
        });
        return reply;
      } finally {
        setPending(false);
      }
    },
    [history],
  );

  const reset = useCallback(() => {
    setEntries([]);
    save([]);
  }, []);

  return { entries, pending, send, reset };
}
