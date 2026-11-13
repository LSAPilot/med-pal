"use client";

import { useEffect, useId, useRef, useState } from "react";
import { MAX_QUESTION_CHARS, type Mode } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { Strings } from "@/lib/i18n";
import { ArrowUp, NewChat } from "./Icons";
import { SegmentedControl } from "./SegmentedControl";

interface Props {
  t: Strings;
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  pending: boolean;
  /** Show "new conversation" only when there is something to clear. */
  canReset: boolean;
  onReset: () => void;
  onSubmit: (question: string) => void;
}

const WARN_AT = Math.floor(MAX_QUESTION_CHARS * 0.9);

/** Sticky bottom bar: search mode, "new conversation", question field with counter, send button. */
export function Composer({ t, mode, onModeChange, pending, canReset, onReset, onSubmit }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const counterId = useId();
  const fieldId = useId();
  const hintId = useId();

  // Grow with the text up to about six lines.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const length = value.length;
  const over = length > MAX_QUESTION_CHARS;
  const blank = value.trim() === "";
  const canSend = !pending && !blank && !over;

  function submit() {
    if (!canSend) return;
    onSubmit(value.trim());
    setValue("");
  }

  return (
    <div className="sticky bottom-0 z-10 border-t border-line bg-white shadow-composer">
      <form
        className="mx-auto max-w-reading px-4 pb-3 pt-3 sm:px-6 sm:pb-4"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <div className="mb-2.5 flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="hidden text-sm font-semibold text-navy sm:inline">{t.modeLabel}</span>
            <SegmentedControl
              size="sm"
              name="mode"
              legend={t.modeLabel}
              value={mode}
              onChange={onModeChange}
              options={(["bm25", "vector", "hybrid"] as const).map((m) => ({ value: m, label: t.modes[m].label }))}
            />
            <span className="hidden min-w-0 truncate text-meta text-ink-muted md:inline">{t.modes[mode].hint}</span>
          </div>
          {canReset && (
            <button
              type="button"
              onClick={onReset}
              disabled={pending}
              aria-label={t.newConversation}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-control px-2 py-1.5 text-sm font-semibold text-primary transition-colors duration-150 ease-standard hover:bg-surface disabled:text-ink-muted disabled:hover:bg-transparent"
            >
              <NewChat className="size-4" />
              <span className="hidden sm:inline">{t.newConversation}</span>
            </button>
          )}
        </div>

        <div
          className={cn(
            "flex items-end gap-2 rounded-panel border bg-white p-2 transition-shadow duration-150 ease-standard",
            "focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-primary",
            over ? "border-danger-ink" : "border-line-strong",
          )}
        >
          <label htmlFor={fieldId} className="sr-only">
            {t.composerLabel}
          </label>
          <textarea
            id={fieldId}
            ref={ref}
            rows={1}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder={t.placeholder}
            aria-describedby={`${counterId} ${hintId}`}
            aria-invalid={over}
            className="max-h-40 min-h-[2.5rem] flex-1 resize-none self-center bg-transparent px-2 py-1.5 text-base text-ink outline-none placeholder:text-ink-muted"
          />
          <button
            type="submit"
            disabled={!canSend}
            className="inline-flex h-10 shrink-0 items-center gap-2 rounded-control bg-primary px-3.5 font-semibold text-on-primary transition-colors duration-150 ease-standard hover:bg-primary-strong disabled:bg-line disabled:text-ink-muted sm:px-4"
          >
            <ArrowUp className="size-4" />
            <span className="hidden sm:inline">{pending ? t.sending : t.send}</span>
            <span className="sr-only sm:hidden">{t.send}</span>
          </button>
        </div>

        <div className="mt-1.5 flex items-center justify-between gap-3 text-meta">
          <p id={hintId} className="hidden text-ink-muted sm:block">
            {t.keyHint}
          </p>
          <p
            id={counterId}
            className={cn(
              "ml-auto tabular-nums",
              over ? "font-bold text-danger-ink" : length >= WARN_AT ? "font-semibold text-notice-ink" : "text-ink-muted",
            )}
          >
            {over && <span className="mr-2 font-semibold">{t.counterOver}</span>}
            {length} / {MAX_QUESTION_CHARS}
          </p>
        </div>
      </form>
    </div>
  );
}
