"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import type { Strings } from "@/lib/i18n";

interface Props {
  t: Strings;
  /** Unique id; links the "show more" button to the quote. */
  id: string;
  quote: string;
}

/**
 * A quote from the law text, set in serif with a blue rule. Long quotes are clamped to 8 lines with a soft fade
 * and a "show more" button (`aria-expanded`). Whether it needs clamping is measured, so short quotes get no button.
 */
export function QuoteBlock({ t, id, quote }: Props) {
  const ref = useRef<HTMLQuoteElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [clampable, setClampable] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || expanded) return;
    // Measured while clamped; re-measured when the width changes (rotation, resize). Once expanded we keep
    // the earlier result, because an unclamped quote cannot be measured.
    const observer = new ResizeObserver(() => setClampable(el.scrollHeight > el.clientHeight + 1));
    observer.observe(el);
    return () => observer.disconnect();
  }, [expanded, quote]);

  return (
    <div className="mt-2">
      <blockquote
        ref={ref}
        id={id}
        lang="en"
        className={cn(
          "break-words border-l-[3px] border-accent bg-surface/60 py-2 pl-4 pr-3 font-serif text-[1.0625rem] leading-[1.7] text-ink",
          !expanded && "line-clamp-8",
          !expanded && clampable && "[mask-image:linear-gradient(to_bottom,black_75%,transparent)]",
        )}
      >
        {quote}
      </blockquote>
      {clampable && (
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={id}
          onClick={() => setExpanded((v) => !v)}
          className="mt-1.5 rounded-control px-1 py-0.5 text-meta font-semibold text-primary underline decoration-primary/40 underline-offset-2 transition-colors duration-150 hover:decoration-primary"
        >
          {expanded ? t.showLess : t.showMore}
        </button>
      )}
    </div>
  );
}
