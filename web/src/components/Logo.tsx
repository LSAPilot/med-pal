import type { SVGProps } from "react";

/**
 * The med-pal mark: a document page with a folded corner (the legal text) carrying a medical cross.
 * Drawn on a 32px grid with a 1.75 stroke so it stays crisp at 24 to 32 px. The page takes `currentColor`
 * (navy by default), the cross is `primary`.
 */
export function Logo(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 32 32"
      width="1em"
      height="1em"
      fill="none"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {/* page with folded corner */}
      <path
        d="M9 3.75h10.25L25.5 10v16.25a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V5.75a2 2 0 0 1 2-2Z"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path d="M19.25 3.75V8a2 2 0 0 0 2 2h4.25" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
      {/* medical cross */}
      <path
        d="M14.85 13.4h2.3v3.45h3.45v2.3h-3.45v3.45h-2.3v-3.45h-3.45v-2.3h3.45Z"
        fill="var(--color-primary)"
        stroke="var(--color-primary)"
        strokeWidth="0.6"
        strokeLinejoin="round"
      />
      {/* a line of text under the cross */}
      <path d="M11.5 24.1h9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.55" />
    </svg>
  );
}
