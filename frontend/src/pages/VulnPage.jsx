import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getVulnerability } from '../services/api'
import GraphVisualization from '../components/GraphVisualization'
import LoadingSpinner from '../components/LoadingSpinner'
import { useSearch } from '../context/SearchContext'

function severityColor(cvss) {
  const score = parseFloat(cvss)
  if (Number.isNaN(score)) return 'bg-slate-500/15 text-slate-300 border-slate-500/40'
  if (score >= 9) return 'bg-red-500/15 text-red-300 border-red-500/50'
  if (score >= 7) return 'bg-orange-500/15 text-orange-300 border-orange-500/50'
  if (score >= 4) return 'bg-yellow-500/15 text-yellow-300 border-yellow-500/50'
  return 'bg-green-500/15 text-green-300 border-green-500/50'
}

export default function VulnPage() {
  const { id } = useParams()
  const { setGraph, reset } = useSearch()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    reset()

    getVulnerability(id)
      .then((res) => {
        if (cancelled) return
        setData(res.data)
        setGraph(res.data.graphData)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err.response?.data?.detail || err.message || 'Failed to load vulnerability')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  if (loading) return <LoadingSpinner label="Loading vulnerability…" />

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
        <Link to="/" className="mt-4 inline-block text-sm text-flame-400 underline">
          ← Back home
        </Link>
      </div>
    )
  }

  const vuln = data?.vulnerability || {}
  const affected = data?.affected_packages || []
  const cvss = vuln.cvss ?? vuln.baseScore ?? vuln.score

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link to="/" className="text-sm text-slate-400 hover:text-flame-400">
        ← Back home
      </Link>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-white sm:text-3xl">
          {vuln.id || id}
        </h1>
        {cvss !== undefined && cvss !== null && (
          <span
            className={`rounded-full border px-3 py-1 text-xs font-semibold ${severityColor(cvss)}`}
          >
            CVSS {cvss}
          </span>
        )}
        {vuln.source && (
          <span className="rounded-full border border-navy-600 bg-navy-900 px-3 py-1 text-xs text-slate-400">
            {vuln.source}
          </span>
        )}
      </div>

      {vuln.summary && (
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-300">
          {vuln.summary}
        </p>
      )}

      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-flame-500">
          Affected packages ({affected.length})
        </h2>
        {affected.length === 0 ? (
          <p className="text-sm text-slate-500">No affected packages recorded.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {affected.map((pkg) => (
              <Link
                key={pkg.id || pkg.name}
                to={`/graph/${encodeURIComponent(pkg.name || pkg.id)}`}
                className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 py-1.5 text-xs text-blue-300 transition hover:border-blue-400 hover:bg-blue-500/20"
              >
                {pkg.name || pkg.id}
                {pkg.version ? ` @ ${pkg.version}` : ''}
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-flame-500">
          Graph context
        </h2>
        <GraphVisualization />
      </section>

      <section className="mt-8 rounded-xl border border-navy-700 bg-navy-900/60 p-4">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-slate-500">
          All properties
        </h2>
        <dl className="grid gap-2 sm:grid-cols-2">
          {Object.entries(vuln)
            .filter(([, v]) => v !== null && v !== undefined && typeof v !== 'object')
            .map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 border-b border-navy-800 pb-1">
                <dt className="text-xs uppercase tracking-wide text-slate-500">{k}</dt>
                <dd className="break-all text-right text-xs text-slate-300">{String(v)}</dd>
              </div>
            ))}
        </dl>
      </section>
    </div>
  )
}
