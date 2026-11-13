# med-pal web frontend

Static Next.js site (App Router, TypeScript, Tailwind CSS v4, `output: "export"`) that talks to the Gradio Space
backend (`/ask` endpoint) directly from the browser via `@gradio/client`. Hosted on Cloudflare Workers Static Assets
(`wrangler.jsonc`, worker name `med-pal`). Node 22 (`.node-version`).

```bash
npm install
cp .env.example .env.local   # then edit
npm run dev                  # http://localhost:3000
npm run build                # static export to out/
npm run lint && npm run typecheck && npm test
```

## Configuration (build-time, no secrets)

| Variable | Meaning |
|---|---|
| `NEXT_PUBLIC_SPACE_ID` | HF Space id (`owner/name`) or a URL such as `http://127.0.0.1:7860` for a local backend |
| `NEXT_PUBLIC_API_MODE` | `mock` = canned replies, no network; anything else (or unset) = live |

## Code

- `src/lib/api.ts`: types (`Reply`, `Source`, `Hit`, `Status`, `Lang`, `Mode`, `Turn`) and `ask(question, history, lang, mode)`.
  Always resolves with a `Reply`; network errors and malformed responses become status `error`. History is trimmed to 3 rounds.
- `src/lib/citations.ts`: splits answer text at `[n]` markers (n = 1-based position in `sources`, written by the backend).
  Only `[n]` with an existing source n counts; every other bracket stays plain text.
- `src/lib/mock.ts`: mock backend, loaded only in mock mode.
- `src/hooks/useConversation.ts`: chat entries plus derived history (last 3 real answers), mirrored to `sessionStorage` when available.
- `src/hooks/usePreferences.ts`: language (browser language by default) and search mode, kept per browser session.
- `src/lib/i18n.ts`: all UI texts in German and English.
- `src/app/page.tsx`: the single page. Holds the state and arranges the components below.
- `src/app/globals.css`: design tokens (Tailwind v4 `@theme`: colours with measured contrast ratios, type scale, radii,
  shadows, motion) and the reduced-motion rule.
- `src/app/layout.tsx`: fonts (Source Sans 3 and Source Serif 4 via `next/font`, self-hosted at build time) and metadata.
  `src/app/icon.svg` is the favicon.

## Mock triggers

In mock mode put a keyword anywhere in the question (case-insensitive). Default is a normal answer with sources and hits.

| Keyword | Reply |
|---|---|
| (none) or `mock:ok` | status `ok`, found, sources and hits |
| `mock:cached` | status `cached` |
| `mock:example` | status `example` |
| `mock:notfound` | status `ok`, `found: false`, reason `below_threshold` |
| `mock:noanswer` | status `ok`, `found: false`, reason `model_no_answer` |
| `mock:invalid` | status `ok`, `found: false`, reason `invalid_output` |
| `mock:long` | normal answer plus one very long source quote (tests the "show more" clamp) |
| `mock:visitor` | `visitor_limit` |
| `mock:daily` | `daily_limit` |
| `mock:error` | `error` |
| `mock:slow` | normal answer after 8 s (shows the cold-start loading text) |
| blank question | `empty` |
| more than 500 characters | `too_long` |

Texts follow the selected language (`de`/`en`). Every mock reply takes about 600 ms (`mock:slow`: 8 s).

## Components (`src/components/`)

| Component | Job |
|---|---|
| `Header`, `Logo`, `NoticeBar` | Masthead with wordmark, tagline, DE/EN switch and the three fixed notices as one unit |
| `SegmentedControl` | Radio group drawn as segments (language, search mode); arrow keys come from native radios |
| `EmptyState` | Start view: lead text, example questions, knowledge-base note |
| `Composer` | Sticky input: search mode, "new conversation", textarea with 500-character counter, send button |
| `ChatEntry` | One question with its reply; picks the right message for each status and reason |
| `AnswerText` | Answer paragraphs; `[n]` markers become numbered chips that open source n (the source list is numbered the same way) |
| `Disclosure` | Collapsible section (`aria-expanded`, 200 ms height transition, `inert` when closed) |
| `SourceList`, `QuoteBlock` | Sources with the original quote in serif (clamped to 8 lines with "show more"), EUR-Lex link |
| `UnderTheHood` | Search mode, rewritten query, hit table with scores and similarity bars |
| `LoadingIndicator` | Pulsing dots; if the first request of the page load takes over 3 s, the "waking up the backend" text (cold start) |
| `StatusNotice` | Amber (refusal, limits, input problems) or muted red (errors) message box |

## Design rules

- Colours, type, radii and motion come from the tokens in `globals.css`; do not hard-code hex values in components.
- `accent` (#4BA3E3) is decoration only. It has too little contrast for text.
- All motion is CSS, 150 to 250 ms, and switched off by `prefers-reduced-motion`. No scroll effects.
- Every `Reply` state has a friendly message: `found: false` is an honest refusal (amber), `error` and
  `invalid_output` are errors (red).

## Security headers (`public/_headers`)

Cloudflare Workers Static Assets applies `public/_headers` (copied to `out/`) in production only; `npm run dev` and a plain
static server ignore it. It sets `nosniff`, `Referrer-Policy`, `X-Frame-Options: DENY` (as the portfolio does), a
Content-Security-Policy and long-term caching for `/_next/static/*`.

CSP: `default-src 'self'`, `font-src 'self'` (next/font is self-hosted), `style-src 'self'`, `img-src 'self' data:`,
`connect-src` only `'self'`, the Space host `https://lsapilot-medical-app-regulatory-helper.hf.space` (`/gradio_api/queue/*`,
SSE over fetch, no WebSocket) and `https://huggingface.co` (the Gradio client reads Space info there),
`frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`, `object-src 'none'`.
`script-src` needs `'unsafe-inline'`: the static export inlines three small scripts (Turbopack chunk list, RSC payload)
whose content changes with every build, so fixed hashes are not possible in a static `_headers` file. Risk is low: the
site renders no user HTML and has no third-party scripts. If the Space id changes, update `connect-src`.
Test the CSP locally with a static server that sends the same headers (violations show up in the console).
