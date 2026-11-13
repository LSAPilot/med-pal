"use client";

import { forwardRef, useCallback, useState } from "react";
import { isAnswerStatus, type Reply, type Source } from "@/lib/api";
import type { Entry } from "@/lib/history";
import type { Strings } from "@/lib/i18n";
import { AnswerText } from "./AnswerText";
import { Disclosure, disclosurePanelId } from "./Disclosure";
import { SourceList, sourceDomId } from "./SourceList";
import { StatusNotice } from "./StatusNotice";
import { UnderTheHood } from "./UnderTheHood";

interface Props {
  t: Strings;
  /** Unique per entry (used for element ids). */
  id: string;
  entry: Entry;
}

interface Notice {
  tone: "notice" | "error";
  title: string;
  /** Backend text, shown only where it carries specifics (limits). */
  body?: string;
  hint?: string;
}

/** Map a reply that is not a sourced answer to a friendly message. */
function describeReply(t: Strings, reply: Reply): Notice {
  switch (reply.reason) {
    case "invalid_output":
      return { tone: "error", ...t.invalidOutput };
    case "model_no_answer":
      return { tone: "notice", ...t.modelNoAnswer };
    case "visitor_limit":
      return { tone: "notice", title: t.visitorLimit.title, body: reply.text || t.visitorLimit.hint };
    case "daily_limit":
      return { tone: "notice", title: t.dailyLimit.title, body: reply.text || t.dailyLimit.hint };
    case "too_long":
      return { tone: "notice", ...t.tooLong };
    case "empty":
      return { tone: "notice", ...t.empty };
    case "below_threshold":
      return { tone: "notice", ...t.belowThreshold };
    default:
      // "error", "invalid_input", or an answer status with found=false and an unexpected reason
      return isAnswerStatus(reply.status)
        ? { tone: "notice", ...t.belowThreshold }
        : { tone: "error", ...t.error };
  }
}

/** Upper bound for the panel's 200 ms height transition, in case no `transitionend` arrives. */
const PANEL_SETTLE_MS = 400;

/**
 * Run `fn` once a Disclosure panel has its final height: right away if it is already open, otherwise after its
 * opening transition (scrolling earlier would measure the collapsed panel). With reduced motion the transition
 * is nearly instant, so `transitionend` comes at once.
 */
function afterPanelOpens(panel: HTMLElement | null, fn: () => void) {
  if (!panel || !panel.inert) {
    fn();
    return;
  }
  let done = false;
  const onEnd = (e: TransitionEvent) => {
    if (e.target === panel) finish();
  };
  const timer = window.setTimeout(() => finish(), PANEL_SETTLE_MS);
  function finish() {
    if (done) return;
    done = true;
    panel?.removeEventListener("transitionend", onEnd);
    window.clearTimeout(timer);
    fn();
  }
  panel.addEventListener("transitionend", onEnd);
}

/** One question and its reply: a sourced answer, an honest "not in the sources", or a friendly status message. */
export const ChatEntry = forwardRef<HTMLElement, Props>(function ChatEntry({ t, id, entry }, ref) {
  const { question, reply, mode } = entry;
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [hoodOpen, setHoodOpen] = useState(false);

  const sourcesId = `${id}-sources`;
  const openSource = useCallback(
    (source: Source) => {
      // Read before the state change: is the panel still collapsed (inert) and about to animate open?
      const panel = document.getElementById(disclosurePanelId(sourcesId));
      setSourcesOpen(true);
      afterPanelOpens(panel, () => {
        const target = document.getElementById(sourceDomId(id, source));
        if (!target) return;
        // Source to the top of the view (scroll-mt-4): "nearest" would align a source further down with the bottom
        // edge, where the sticky composer covers it. Instant, like every other scroll on the page.
        target.scrollIntoView({ block: "start" });
        target.focus({ preventScroll: true });
      });
    },
    [id, sourcesId],
  );

  const answered = isAnswerStatus(reply.status) && reply.found;
  const notice = answered ? null : describeReply(t, reply);
  // The search details are worth showing whenever the search ran and returned something, also for a refusal.
  const showHood = isAnswerStatus(reply.status);

  return (
    <article ref={ref} aria-label={question} className="scroll-mt-4">
      <h2 className="m-0 break-words rounded-panel bg-surface px-4 py-3 text-base font-semibold text-navy">
        <span className="sr-only">{t.yourQuestion}: </span>
        {question}
      </h2>

      <div className="animate-fade-in mt-5">
        {answered && (
          <>
            <AnswerText t={t} text={reply.text} sources={reply.sources} onCite={openSource} />
            {(reply.status === "cached" || reply.status === "example") && (
              <p className="mt-3 text-meta text-ink-muted">{reply.status === "cached" ? t.cached : t.example}</p>
            )}
          </>
        )}

        {notice && <StatusNotice tone={notice.tone} title={notice.title} body={notice.body} hint={notice.hint} />}

        {showHood && (
          <div className="mt-5">
            {reply.sources.length > 0 && (
              <Disclosure
                id={sourcesId}
                title={t.sources}
                badge={String(reply.sources.length)}
                open={sourcesOpen}
                onOpenChange={setSourcesOpen}
              >
                <SourceList t={t} idPrefix={id} sources={reply.sources} />
              </Disclosure>
            )}
            <div className="border-b border-line">
              <Disclosure id={`${id}-hood`} title={t.underTheHood} open={hoodOpen} onOpenChange={setHoodOpen}>
                <UnderTheHood t={t} reply={reply} mode={mode} />
              </Disclosure>
            </div>
          </div>
        )}
      </div>
    </article>
  );
});
