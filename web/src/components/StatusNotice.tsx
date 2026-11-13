import { cn } from "@/lib/cn";
import { Alert, InfoCircle } from "./Icons";

interface Props {
  /** "notice" is amber (honest refusal, limits, input problems), "error" is muted red (something failed). */
  tone: "notice" | "error";
  title: string;
  /** The backend's own text, shown when it carries specifics (limits). */
  body?: string;
  hint?: string;
}

/** A friendly message box. Never a raw status code. */
export function StatusNotice({ tone, title, body, hint }: Props) {
  const error = tone === "error";
  return (
    <div
      className={cn(
        "flex gap-3 rounded-panel border px-4 py-3.5",
        error
          ? "border-danger-line bg-danger-bg text-danger-ink"
          : "border-notice-line bg-notice-bg text-notice-ink",
      )}
    >
      <span className="mt-1 shrink-0 text-lg">{error ? <Alert /> : <InfoCircle />}</span>
      <div className="min-w-0 space-y-1.5 break-words">
        <p className="font-bold">{title}</p>
        {body && <p>{body}</p>}
        {hint && <p className="text-sm">{hint}</p>}
      </div>
    </div>
  );
}
