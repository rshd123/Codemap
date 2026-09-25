import { useSearch } from '../context/SearchContext'

const TYPE_STYLES = {
  Package: 'bg-blue-500/15 text-blue-300 border-blue-500/40',
  Vulnerability: 'bg-red-500/15 text-red-300 border-red-500/40',
  Issue: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40',
  Commit: 'bg-green-500/15 text-green-300 border-green-500/40',
}

const INTERNAL_KEYS = new Set(['x', 'y', 'vx', 'vy', 'fx', 'fy', 'index'])

export default function NodeDetail() {
  const { selectedNode, clearSelection } = useSearch()

  if (!selectedNode) return null

  const { label, id, ...rest } = selectedNode
  const props = Object.fromEntries(
    Object.entries(rest).filter(([k]) => !INTERNAL_KEYS.has(k))
  )
  const type = label || 'Node'
  const badge = TYPE_STYLES[type] || 'bg-slate-500/15 text-slate-300 border-slate-500/40'
  const entries = Object.entries(props).filter(
    ([, v]) => v !== null && v !== undefined && typeof v !== 'object'
  )

  return (
    <div className="absolute right-4 top-4 z-20 w-72 rounded-xl border border-navy-600 bg-navy-850/95 shadow-2xl shadow-black/50 backdrop-blur">
      <div className="flex items-center justify-between border-b border-navy-700 px-4 py-3">
        <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${badge}`}>
          {type}
        </span>
        <button
          onClick={clearSelection}
          aria-label="Close node detail"
          className="text-slate-400 transition hover:text-flame-400"
        >
          ✕
        </button>
      </div>

      <div className="px-4 py-3">
        <p className="mb-3 text-sm font-semibold text-slate-100">
          {props.name || props.title || props.id || id}
        </p>
        {entries.length > 0 ? (
          <dl className="space-y-2">
            {entries.map(([key, value]) => (
              <div key={key} className="flex items-start justify-between gap-3">
                <dt className="text-xs uppercase tracking-wide text-slate-500">{key}</dt>
                <dd className="break-all text-right text-xs text-slate-300">
                  {String(value)}
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-xs text-slate-500">No additional properties.</p>
        )}
      </div>
    </div>
  )
}
