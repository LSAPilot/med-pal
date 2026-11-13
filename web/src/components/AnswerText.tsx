import type { Source } from "@/lib/api";

interface Props {
  text: string;
  sources: readonly Source[];
  /** Called when a citation that matches a source is activated. */
  onCite: (source: Source) => void;
}

const CITATION = /\[([^[\]]+)\]/g;

/**
 * The answer text. Paragraphs are split on blank lines; `[MDR Art. 2(1)]`-style citations become small chips.
 * A chip whose text equals a source's citation is a button that opens that source.
 */
export function AnswerText({ text, sources, onCite }: Props) {
  const paragraphs = text.split(/\n{2,}/).filter((p) => p.trim());
  return (
    <div className="max-w-[68ch] space-y-4 text-ink">
      {paragraphs.map((p, i) => (
        <p key={i} className="whitespace-pre-line break-words">
          {renderCitations(p, sources, onCite)}
        </p>
      ))}
    </div>
  );
}

const chipBase =
  "inline-block whitespace-nowrap rounded-chip bg-surface px-1.5 align-baseline text-meta font-semibold leading-[1.5] text-primary";

function renderCitations(paragraph: string, sources: readonly Source[], onCite: (s: Source) => void) {
  const nodes: React.ReactNode[] = [];
  let last = 0;
  for (const match of paragraph.matchAll(CITATION)) {
    const start = match.index ?? 0;
    if (start > last) nodes.push(paragraph.slice(last, start));
    const label = match[1];
    const source = sources.find((s) => s.citation === label);
    nodes.push(
      source ? (
        <button
          key={start}
          type="button"
          onClick={() => onCite(source)}
          className={`${chipBase} transition-colors duration-150 ease-standard hover:bg-primary hover:text-white`}
        >
          {label}
        </button>
      ) : (
        <span key={start} className={chipBase}>
          {label}
        </span>
      ),
    );
    last = start + match[0].length;
  }
  if (last < paragraph.length) nodes.push(paragraph.slice(last));
  return nodes;
}
