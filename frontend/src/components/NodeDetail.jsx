import { Link } from 'react-router-dom'
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
    ([, v]) => v !== null && v !== undefined && typeof v !== 'object',
  )

  const links = []
  if (type === 'Package' && selectedNode.name) {
    links.push({
      key: 'deps',
      label: 'Dependency tree',
      to: `/dependencies/${encodeURIComponent(selectedNode.name)}`,
    })
  }
  if (type === 'Vulnerability' && props.id) {
    links.push({
      key: 'vuln',
      label: 'Vulnerability detail',
      to: `/vulnerability/${encodeURIComponent(props.id)}`,
    })
  }
  if (type === 'Issue' && props.repo && props.number) {
    links.push({
      key: 'issue',
      label: 'Open issue',
      href: `https://github.com/${props.repo}/issues/${props.number}`,
    })
  }
  if (props.url) {
    links.push({ key: 'url', label: 'Open source ↗', href: props.url })
  }

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

      {links.length > 0 && (
        <div className="flex flex-col gap-1.5 border-t border-navy-700 px-4 py-3">
          {links.map((link) =>
            link.to ? (
              <Link
                key={link.key}
                to={link.to}
                className="rounded-lg border border-navy-600 bg-navy-900 px-3 py-1.5 text-center text-xs text-blue-300 transition hover:border-blue-400/60 hover:text-blue-200"
              >
                {link.label}
              </Link>
            ) : (
              <a
                key={link.key}
                href={link.href}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-navy-600 bg-navy-900 px-3 py-1.5 text-center text-xs text-slate-300 transition hover:border-flame-500/60 hover:text-flame-400"
              >
                {link.label}
              </a>
            ),
          )}
        </div>
      )}
    </div>
  )
}
