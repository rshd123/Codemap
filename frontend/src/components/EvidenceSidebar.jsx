import { useSearch } from '../context/SearchContext'
import LoadingSpinner from './LoadingSpinner'

export default function EvidenceSidebar() {
  const { loading, error, explanation, cypher, query } = useSearch()

  return (
    <aside className="flex h-full flex-col rounded-xl border border-navy-700 bg-navy-900/60">
      <div className="border-b border-navy-700 px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-flame-500">
          Evidence
        </h2>
        {query && (
          <p className="mt-1 truncate text-xs text-slate-400" title={query}>
            Query: “{query}”
          </p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {loading && <LoadingSpinner label="Generating explanation…" />}

        {!loading && error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        {!loading && !error && !explanation && (
          <p className="text-sm text-slate-500">
            The LLM-generated explanation of the sub-graph will appear here.
          </p>
        )}

        {!loading && !error && explanation && (
          <div className="space-y-4">
            <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
              {explanation}
            </div>
            {cypher && (
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Generated Cypher
                </h3>
                <pre className="overflow-x-auto rounded-lg border border-navy-700 bg-navy-950/80 p-3 text-xs leading-relaxed text-flame-300">
                  {cypher}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  )
}
