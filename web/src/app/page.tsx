"use client";

import { useEffect, useRef, useState } from "react";
import type { Mode } from "@/lib/api";
import { STRINGS } from "@/lib/i18n";
import { useConversation } from "@/hooks/useConversation";
import { usePreferences } from "@/hooks/usePreferences";
import { ChatEntry } from "@/components/ChatEntry";
import { Composer } from "@/components/Composer";
import { EmptyState } from "@/components/EmptyState";
import { Header } from "@/components/Header";
import { LoadingIndicator } from "@/components/LoadingIndicator";

export default function Home() {
  const { entries, pending, send, reset } = useConversation();
  const { lang, mode, setLang, setMode } = usePreferences();
  const [asked, setAsked] = useState<string | null>(null);
  // Set once a request of this page load has come back without error; after that a slow reply is not a cold start.
  const [warm, setWarm] = useState(false);
  const t = STRINGS[lang];
  const lastRef = useRef<HTMLElement>(null);
  const pendingRef = useRef<HTMLDivElement>(null);

  // Keep document language and tab title in step with the switch (screen readers, hyphenation, tabs).
  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = t.documentTitle;
  }, [lang, t.documentTitle]);

  // A new question or reply brings the newest block to the top of the view.
  useEffect(() => {
    (pending ? pendingRef.current : lastRef.current)?.scrollIntoView({ block: "start" });
  }, [pending, entries.length]);

  // modeOverride: example questions always go out as "hybrid", the mode their answers are precomputed with, so a click is free.
  async function handleSubmit(question: string, modeOverride?: Mode) {
    setAsked(question);
    const reply = await send(question, lang, modeOverride ?? mode);
    // After an error the Space may still be waking up, so the next request keeps the cold-start text.
    if (reply.status !== "error") setWarm(true);
  }

  const empty = entries.length === 0 && !pending;

  return (
    <div className="flex min-h-dvh flex-col">
      <Header t={t} lang={lang} onLangChange={setLang} />

      <main className="mx-auto w-full max-w-reading flex-1 px-4 pb-10 sm:px-6">
        {empty ? (
          <EmptyState t={t} disabled={pending} onPick={(q) => void handleSubmit(q, "hybrid")} />
        ) : (
          <div role="log" aria-live="polite" aria-relevant="additions" className="space-y-10 pt-8">
            {entries.map((entry, i) => (
              <ChatEntry
                key={i}
                id={`e${i}`}
                t={t}
                entry={entry}
                ref={i === entries.length - 1 && !pending ? lastRef : undefined}
              />
            ))}
            {pending && asked && (
              <div ref={pendingRef} className="scroll-mt-4">
                <p className="break-words rounded-panel bg-surface px-4 py-3 text-base font-semibold text-navy">
                  {asked}
                </p>
                <LoadingIndicator t={t} coldStart={!warm} />
              </div>
            )}
          </div>
        )}
      </main>

      <Composer
        t={t}
        mode={mode}
        onModeChange={setMode}
        pending={pending}
        canReset={entries.length > 0}
        onReset={reset}
        onSubmit={(q) => void handleSubmit(q)}
      />
    </div>
  );
}
