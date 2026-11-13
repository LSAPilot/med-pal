"use client";

import { useEffect, useState } from "react";
import type { Strings } from "@/lib/i18n";

/** After this long without a reply we assume the Space is waking up from sleep and say so. */
const COLD_START_AFTER_MS = 3000;

/**
 * Three pulsing dots plus a status line. Mounted only while a request is running. `coldStart` is true for the first
 * request of the page load: only then can a long wait mean a sleeping Space (later ones are just a slow answer).
 */
export function LoadingIndicator({ t, coldStart }: { t: Strings; coldStart: boolean }) {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (!coldStart) return;
    const timer = window.setTimeout(() => setSlow(true), COLD_START_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [coldStart]);

  return (
    <div role="status" className="animate-fade-in py-4">
      <div className="flex items-center gap-3 text-navy">
        <span aria-hidden="true" className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="animate-dot size-2 rounded-full bg-primary"
              style={{ animationDelay: `${i * 160}ms` }}
            />
          ))}
        </span>
        <span className="font-semibold">{slow ? t.loadingWarmup : t.loadingSearch}</span>
      </div>
      {slow && (
        <p className="animate-fade-in mt-1 pl-12 text-sm text-ink-muted">
          {t.loadingWarmupHint}
        </p>
      )}
    </div>
  );
}
