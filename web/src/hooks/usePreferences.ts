"use client";

import { useCallback, useEffect, useState } from "react";
import { isLang, isMode, type Lang, type Mode } from "@/lib/api";

const STORAGE_KEY = "med-pal:preferences";

interface Preferences {
  lang: Lang;
  mode: Mode;
}

function load(): Preferences {
  const fallback: Preferences = {
    // Start in the browser's language, German unless it is English.
    lang: typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("en") ? "en" : "de",
    mode: "hybrid",
  };
  try {
    const raw: unknown = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "null");
    if (typeof raw === "object" && raw !== null) {
      const r = raw as Record<string, unknown>;
      return { lang: isLang(r.lang) ? r.lang : fallback.lang, mode: isMode(r.mode) ? r.mode : fallback.mode };
    }
  } catch {
    /* storage unavailable or corrupted: use the defaults */
  }
  return fallback;
}

function save(p: Preferences) {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(p));
  } catch {
    /* storage unavailable: preferences just live in memory */
  }
}

/**
 * Language and search mode. Defaults to the browser language and hybrid search; the choice is kept for the
 * browser session only (sessionStorage, if available). The static prerender always shows German, the stored or
 * detected value is applied after hydration.
 */
export function usePreferences() {
  const [prefs, setPrefs] = useState<Preferences>({ lang: "de", mode: "hybrid" });

  useEffect(() => {
    // sessionStorage and navigator only exist in the browser, so they are read after hydration
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPrefs(load());
  }, []);

  const setLang = useCallback((lang: Lang) => {
    setPrefs((p) => {
      const next = { ...p, lang };
      save(next);
      return next;
    });
  }, []);

  const setMode = useCallback((mode: Mode) => {
    setPrefs((p) => {
      const next = { ...p, mode };
      save(next);
      return next;
    });
  }, []);

  return { lang: prefs.lang, mode: prefs.mode, setLang, setMode };
}
