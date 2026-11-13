import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { ChevronDown } from "./Icons";

interface Props {
  /** Unique within the page; used to link button and panel. */
  id: string;
  title: string;
  /** Short note right of the title, e.g. the number of sources. */
  badge?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}

/** Element id of the panel of the Disclosure with this `id`. */
export function disclosurePanelId(id: string): string {
  return `${id}-panel`;
}

/**
 * Collapsible section: a button with `aria-expanded` and a panel that animates its height (200 ms, CSS grid
 * rows trick). A collapsed panel is `inert`, so its content cannot be focused or read.
 */
export function Disclosure({ id, title, badge, open, onOpenChange, children }: Props) {
  const buttonId = `${id}-button`;
  const panelId = disclosurePanelId(id);
  return (
    <section className="border-t border-line">
      <h3 className="m-0 text-base font-semibold">
        <button
          type="button"
          id={buttonId}
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => onOpenChange(!open)}
          className="group -mx-2 flex w-[calc(100%+1rem)] items-center gap-2 rounded-control px-2 py-3 text-left text-navy transition-colors duration-150 ease-standard hover:bg-surface"
        >
          <ChevronDown
            className={cn("size-4 shrink-0 text-primary transition-transform duration-200 ease-standard", open && "rotate-180")}
          />
          <span>{title}</span>
          {badge && <span className="rounded-chip bg-surface px-1.5 text-meta font-semibold text-ink-muted group-hover:bg-white">{badge}</span>}
        </button>
      </h3>
      <div
        id={panelId}
        role="region"
        aria-labelledby={buttonId}
        inert={!open}
        className={cn(
          "grid transition-[grid-template-rows,opacity] duration-200 ease-standard",
          open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
        )}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="pb-4 pt-1">{children}</div>
        </div>
      </div>
    </section>
  );
}
