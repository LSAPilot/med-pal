import type { Strings } from "@/lib/i18n";
import { InfoCircle, Lock, Scale } from "./Icons";

/** The three fixed notices. Part of the header unit, always visible. */
export function NoticeBar({ t }: { t: Strings }) {
  const items = [
    { icon: <Scale />, text: t.notices.advice },
    { icon: <InfoCircle />, text: t.notices.iec },
    { icon: <Lock />, text: t.notices.privacy },
  ];
  return (
    <ul aria-label={t.noticesLabel} className="flex flex-wrap gap-x-5 gap-y-1 text-meta font-medium text-ink">
      {items.map((item) => (
        <li key={item.text} className="flex items-center gap-1.5">
          <span className="text-base text-primary">{item.icon}</span>
          {item.text}
        </li>
      ))}
    </ul>
  );
}
