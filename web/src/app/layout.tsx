import type { Metadata, Viewport } from "next";
import { Source_Sans_3, Source_Serif_4 } from "next/font/google";
import "./globals.css";

// Self-hosted at build time by next/font, so it works with the static export and sends no request to Google.
const sans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source-sans",
  display: "swap",
});
const serif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "med-pal: Fragen zu MDR, DSGVO und AI Act",
  description: "Antworten zu MDR, DSGVO und AI Act, mit Quellenangabe und Originalzitat.",
};

export const viewport: Viewport = {
  themeColor: "#0e3a68",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // `lang` is kept in sync with the language switch on the client (see page.tsx).
    <html lang="de" className={`${sans.variable} ${serif.variable}`}>
      <body>{children}</body>
    </html>
  );
}
