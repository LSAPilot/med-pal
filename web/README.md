# Regulatory Copilot web frontend

Static Next.js site (App Router, TypeScript, Tailwind CSS v4, `output: "export"`) that talks to the Gradio Space
backend (`/ask` endpoint) directly from the browser via `@gradio/client`. Hosted on Cloudflare Workers Static Assets
(`wrangler.jsonc`). Node 22 (`.node-version`).

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
- `src/lib/mock.ts`: mock backend, loaded only in mock mode.
- `src/hooks/useConversation.ts`: chat entries plus derived history (last 3 real answers), mirrored to `sessionStorage` when available.
- `src/app/page.tsx`: unstyled test page, replaced in F3.

## Mock triggers

In mock mode put a keyword anywhere in the question (case-insensitive). Default is a normal answer with sources and hits.

| Keyword | Reply |
|---|---|
| (none) or `mock:ok` | status `ok`, found, sources and hits |
| `mock:cached` | status `cached` |
| `mock:example` | status `example` |
| `mock:notfound` | status `ok`, `found: false`, reason `below_threshold` |
| `mock:invalid` | status `ok`, `found: false`, reason `invalid_output` |
| `mock:visitor` | `visitor_limit` |
| `mock:daily` | `daily_limit` |
| `mock:error` | `error` |
| blank question | `empty` |
| more than 500 characters | `too_long` |

Texts follow the selected language (`de`/`en`). Every mock reply takes about 600 ms.
