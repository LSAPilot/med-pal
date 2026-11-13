"use client";

// Minimal unstyled test page for the API client (F2). Replaced by the real UI in F3.
import { useState } from "react";
import type { Lang, Mode } from "@/lib/api";
import { useConversation } from "@/hooks/useConversation";

export default function Home() {
  const { entries, history, pending, send, reset } = useConversation();
  const [question, setQuestion] = useState("");
  const [lang, setLang] = useState<Lang>("de");
  const [mode, setMode] = useState<Mode>("hybrid");

  return (
    <main style={{ padding: 16, maxWidth: 900 }}>
      <h1>API test page</h1>
      <p>
        mode: {process.env.NEXT_PUBLIC_API_MODE ?? "live"}, target: {process.env.NEXT_PUBLIC_SPACE_ID ?? "(unset)"}
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send(question, lang, mode);
          setQuestion("");
        }}
      >
        <input
          aria-label="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          style={{ width: "60%" }}
        />{" "}
        <select aria-label="lang" value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
          <option value="de">de</option>
          <option value="en">en</option>
        </select>{" "}
        <select aria-label="mode" value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
          <option value="bm25">bm25</option>
          <option value="vector">vector</option>
          <option value="hybrid">hybrid</option>
        </select>{" "}
        <button type="submit" disabled={pending}>
          {pending ? "..." : "ask"}
        </button>{" "}
        <button type="button" onClick={reset}>
          new conversation
        </button>
      </form>
      <p>history sent next: {history.length} round(s)</p>
      {entries.map((e, i) => (
        <section key={i}>
          <h3>{e.question}</h3>
          <pre data-testid="reply" style={{ whiteSpace: "pre-wrap" }}>
            {JSON.stringify(e.reply, null, 2)}
          </pre>
        </section>
      ))}
    </main>
  );
}
