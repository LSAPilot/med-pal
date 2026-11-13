import type { Mode, Reply } from "@/lib/api";
import type { Strings } from "@/lib/i18n";

interface Props {
  t: Strings;
  reply: Reply;
  mode?: Mode;
}

/** "Blick unter die Haube": what the search did. Mode, rewritten query, hits with scores. */
export function UnderTheHood({ t, reply, mode }: Props) {
  return (
    <div className="space-y-5 text-sm">
      <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-[max-content_1fr]">
        {mode && (
          <>
            <dt className="font-semibold text-navy">{t.hoodMode}</dt>
            <dd className="m-0">{t.modeFull[mode]}</dd>
          </>
        )}
        <dt className="font-semibold text-navy">{t.hoodQuery}</dt>
        <dd className="m-0 break-words">{reply.search_query || <span className="text-ink-muted">{t.hoodQueryNone}</span>}</dd>
        {reply.best_cosine !== null && (
          <>
            <dt className="font-semibold text-navy">{t.hoodBest}</dt>
            <dd className="m-0 tabular-nums">{reply.best_cosine.toFixed(2)}</dd>
          </>
        )}
      </dl>

      <div>
        <h4 className="mb-2 font-semibold text-navy">{t.hoodHits}</h4>
        {reply.hits.length === 0 ? (
          <p className="text-ink-muted">{t.hoodNoHits}</p>
        ) : (
          <div className="overflow-x-auto rounded-panel border border-line">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="bg-surface text-meta text-ink-muted">
                  <th scope="col" className="w-12 px-3 py-2 font-semibold">{t.colRank}</th>
                  <th scope="col" className="px-3 py-2 font-semibold">{t.colCitation}</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">{t.colScore}</th>
                  <th scope="col" className="px-3 py-2 font-semibold">{t.colSimilarity}</th>
                </tr>
              </thead>
              <tbody>
                {reply.hits.map((h) => (
                  <tr key={`${h.rank}-${h.id}`} className="border-t border-line align-middle">
                    <td className="px-3 py-2 tabular-nums text-ink-muted">{h.rank}</td>
                    <td className="px-3 py-2 font-medium">{h.citation}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{h.score.toFixed(4)}</td>
                    <td className="px-3 py-2">
                      {h.cosine === null ? (
                        <span className="text-ink-muted">-</span>
                      ) : (
                        <span className="flex items-center gap-2">
                          <span aria-hidden="true" className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-surface sm:block">
                            <span
                              className="block h-full rounded-full bg-accent"
                              style={{ width: `${Math.max(0, Math.min(1, h.cosine)) * 100}%` }}
                            />
                          </span>
                          <span className="tabular-nums">{h.cosine.toFixed(2)}</span>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-2 text-meta text-ink-muted">{t.hoodScoreNote}</p>
      </div>
    </div>
  );
}
