import type { Strings } from "@/lib/i18n";
import { ChevronRight } from "./Icons";

interface Props {
  t: Strings;
  disabled: boolean;
  onPick: (question: string) => void;
}

/** Start view: what this is, and four example questions as a plain list (one per law). */
export function EmptyState({ t, disabled, onPick }: Props) {
  return (
    <section aria-labelledby="start-title" className="animate-fade-in pt-8 sm:pt-10">
      <h2 id="start-title" className="max-w-[34ch] text-balance text-title font-bold tracking-tight text-navy sm:text-[2rem]">
        {t.startTitle}
      </h2>
      <p className="mt-3 max-w-[60ch] text-ink-muted">{t.startLead}</p>

      <h3 className="mb-2 mt-7 text-sm font-semibold text-navy">{t.examplesLabel}</h3>
      <ul className="border-t border-line">
        {t.examples.map((ex) => (
          <li key={ex.question} className="border-b border-line">
            <button
              type="button"
              disabled={disabled}
              onClick={() => onPick(ex.question)}
              className="group -mx-3 flex w-[calc(100%+1.5rem)] items-center gap-3 rounded-control px-3 py-3 text-left transition-colors duration-150 ease-standard hover:bg-surface disabled:opacity-60 disabled:hover:bg-transparent"
            >
              <span className="flex min-w-0 flex-1 flex-col items-start gap-1 sm:flex-row sm:items-center sm:gap-3">
                <span className="shrink-0 rounded-chip bg-surface px-1.5 py-0.5 text-center text-meta font-semibold text-primary transition-colors duration-150 group-hover:bg-white sm:w-[3.75rem]">
                  {ex.corpus}
                </span>
                <span className="min-w-0 font-medium">{ex.question}</span>
              </span>
              <ChevronRight className="size-4 shrink-0 text-primary transition-transform duration-150 ease-standard group-hover:translate-x-0.5" />
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-5 max-w-[62ch] text-meta text-ink-muted">{t.corpusNote}</p>
    </section>
  );
}
