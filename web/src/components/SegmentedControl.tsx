import { cn } from "@/lib/cn";

interface Option<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  /** Accessible name of the group (visually hidden). */
  legend: string;
  name: string;
  value: T;
  options: readonly Option<T>[];
  onChange: (value: T) => void;
  /** "track": tinted track with a white active segment. "outline": hairline frame with a navy active segment. */
  tone?: "track" | "outline";
  size?: "sm" | "md";
}

/**
 * A radio group drawn as a segmented control. Real radio inputs give arrow-key navigation and screen reader
 * semantics for free; the visible segment is the label.
 */
export function SegmentedControl<T extends string>({
  legend,
  name,
  value,
  options,
  onChange,
  tone = "track",
  size = "md",
}: Props<T>) {
  const outline = tone === "outline";
  return (
    <fieldset
      className={cn(
        "m-0 inline-flex min-w-0 gap-0.5 rounded-control p-0.5",
        outline ? "border border-line-strong bg-white" : "border-0 bg-surface",
      )}
    >
      <legend className="sr-only">{legend}</legend>
      {options.map((o) => (
        <label
          key={o.value}
          className={cn(
            "relative cursor-pointer select-none rounded-chip font-semibold transition-colors duration-150 ease-standard",
            "has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-primary",
            size === "sm" ? "px-2.5 py-1 text-meta" : "px-3 py-1.5 text-sm",
            outline
              ? "tracking-wide text-ink-muted hover:bg-surface hover:text-navy has-checked:bg-navy has-checked:text-on-navy has-checked:hover:bg-navy has-checked:hover:text-on-navy"
              : "text-ink-muted hover:text-navy has-checked:bg-white has-checked:text-navy has-checked:shadow-segment",
          )}
        >
          <input
            type="radio"
            name={name}
            value={o.value}
            checked={value === o.value}
            onChange={() => onChange(o.value)}
            className="absolute inset-0 m-0 cursor-pointer appearance-none opacity-0"
          />
          {o.label}
        </label>
      ))}
    </fieldset>
  );
}
