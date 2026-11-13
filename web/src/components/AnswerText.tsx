import type { Source } from "@/lib/api";
import { splitCitations } from "@/lib/citations";
import type { Strings } from "@/lib/i18n";
import { citationChip } from "./SourceList";

interface Props {
  t: Strings;
  text: string;
  sources: readonly Source[];
  /** Called when a citation marker is activated. */
  onCite: (source: Source) => void;
}

/**
 * The answer text. Paragraphs are split on blank lines; `[n]` markers (n = position in `sources`, see
 * `lib/citations.ts`) become small numbered chips that open that source. Anything else stays plain text.
 */
export function AnswerText({ t, text, sources, onCite }: Props) {
  const paragraphs = text.split(/\n{2,}/).filter((p) => p.trim());
  return (
    <div className="max-w-[68ch] space-y-4 text-ink">
      {paragraphs.map((p, i) => (
        <p key={i} className="whitespace-pre-line break-words">
          {splitCitations(p, sources.length).map((seg, j) => {
            if (seg.type === "text") return seg.text;
            const source = sources[seg.n - 1];
            return (
              <button
                key={j}
                type="button"
                onClick={() => onCite(source)}
                title={source.citation}
                aria-label={`${t.sourceRef} ${seg.n}: ${source.citation}`}
                className={`${citationChip} ml-0.5 transition-colors duration-150 ease-standard hover:bg-primary hover:text-on-primary`}
              >
                {seg.n}
              </button>
            );
          })}
        </p>
      ))}
    </div>
  );
}
