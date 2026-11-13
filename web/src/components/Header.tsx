import type { Lang } from "@/lib/api";
import type { Strings } from "@/lib/i18n";
import { Logo } from "./Logo";
import { NoticeBar } from "./NoticeBar";
import { SegmentedControl } from "./SegmentedControl";

interface Props {
  t: Strings;
  lang: Lang;
  onLangChange: (lang: Lang) => void;
}

/**
 * One composed unit: a navy masthead rule, the wordmark with its tagline and the language switch, and below a
 * hairline the fixed notices. White, calm, aligned to the reading column.
 */
export function Header({ t, lang, onLangChange }: Props) {
  return (
    <header className="border-b border-line border-t-4 border-t-navy bg-white">
      <div className="mx-auto max-w-reading px-4 sm:px-6">
        <div className="flex items-center justify-between gap-4 py-3.5 sm:py-4">
          <div className="flex min-w-0 items-center gap-3.5">
            <Logo className="size-8 shrink-0 text-navy" />
            <h1 className="text-[1.625rem] font-bold leading-none tracking-[-0.02em] text-navy">{t.appName}</h1>
            <p className="hidden border-l border-line pl-3.5 text-sm leading-snug text-ink-muted md:block">
              {t.tagline}
            </p>
          </div>
          <SegmentedControl
            tone="outline"
            size="sm"
            name="lang"
            legend={t.langLabel}
            value={lang}
            onChange={onLangChange}
            options={[
              { value: "de", label: "DE" },
              { value: "en", label: "EN" },
            ]}
          />
        </div>
        <div className="border-t border-line py-2.5">
          <NoticeBar t={t} />
        </div>
      </div>
    </header>
  );
}
