import type { Source } from "@/lib/api";
import type { Strings } from "@/lib/i18n";
import { ExternalLink } from "./Icons";
import { QuoteBlock } from "./QuoteBlock";

interface Props {
  t: Strings;
  /** Prefix for element ids, so the chat can scroll to a source. */
  idPrefix: string;
  sources: readonly Source[];
}

/** Sources of one answer: citation, original quote set like a statute excerpt, link to EUR-Lex. */
export function SourceList({ t, idPrefix, sources }: Props) {
  return (
    <ol className="space-y-6">
      {sources.map((s) => (
        <li key={s.id} id={sourceDomId(idPrefix, s)} className="scroll-mt-4">
          <p className="font-semibold text-navy">{s.citation}</p>
          {s.title && <p className="text-meta text-ink-muted">{s.title}</p>}
          <QuoteBlock t={t} id={`${sourceDomId(idPrefix, s)}-quote`} quote={s.quote} />
          <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-meta text-ink-muted">
            <span>{t.sourceOriginal}</span>
            {s.source_url && (
              <a
                href={s.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-semibold text-primary underline decoration-primary/40 underline-offset-2 transition-colors duration-150 hover:decoration-primary"
              >
                {t.sourceOpen}
                <ExternalLink className="size-3.5" />
                <span className="sr-only">{t.newWindow}</span>
              </a>
            )}
          </p>
        </li>
      ))}
    </ol>
  );
}

export function sourceDomId(idPrefix: string, source: Source): string {
  return `${idPrefix}-src-${source.id}`;
}
