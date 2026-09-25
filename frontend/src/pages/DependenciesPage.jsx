import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useSearch } from '../context/SearchContext'
import { getDependencies } from '../services/api'
import GraphVisualization from '../components/GraphVisualization'
import NodeDetail from '../components/NodeDetail'
import LoadingSpinner from '../components/LoadingSpinner'

const ECOSYSTEMS = ['', 'npm', 'pypi', 'maven', 'cargo', 'go', 'gem', 'nuget', 'github']
const DEPTHS = [1, 2, 3, 4, 5, 6, 7, 8]

const inputClass =
  'w-full rounded-lg border border-navy-600 bg-navy-900/80 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-flame-500/70 focus:ring-1 focus:ring-flame-500/40'

export default function DependenciesPage() {
  const { name: routeName } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { graphData, setGraph, reset } = useSearch()

  const ecosystem = searchParams.get('ecosystem') || ''
  const depth = Number(searchParams.get('depth') || 3)
  const direct = searchParams.get('direct') === 'true'

  const [nameInput, setNameInput] = useState(routeName || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const target = (routeName || '').trim()
    if (!target) return undefined
    let cancelled = false
    setLoading(true)
    setError(null)

    getDependencies({ name: target, ecosystem: ecosystem || undefined, depth, direct })
      .then((res) => {
        if (cancelled) return
        setGraph(res.data)
        if (!(res.data.nodes || []).length) {
          setError(`No DEPENDS_ON edges found for "${target}"${ecosystem ? ` in ${ecosystem}` : ''}.`)
        }
      })
      .catch((err) => {
        if (cancelled) return
        setError(err.response?.data?.detail || err.message || 'Failed to load dependencies')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeName, ecosystem, depth, direct])

  function applyParams(next) {
    const params = new URLSearchParams(searchParams)
    Object.entries(next).forEach(([key, value]) => {
      if (value === '' || value === null || value === undefined) params.delete(key)
      else params.set(key, String(value))
    })
    setSearchParams(params)
  }

  function handleSubmit(e) {
    e.preventDefault()
    const target = nameInput.trim()
    if (!target) return
    navigate(`/dependencies/${encodeURIComponent(target)}`)
  }

  const nodeCount = graphData?.nodes?.length || 0
  const linkCount = graphData?.links?.length || 0

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6">
      <div className="flex flex-col gap-3">
        <div>
          <h1 className="text-lg font-semibold text-white">Dependency explorer</h1>
          <p className="text-sm text-slate-400">
            Transitive <span className="text-flame-400">DEPENDS_ON</span> traversal straight from the graph.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex-1 text-xs text-slate-400">
            Package
            <input
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              placeholder="express"
              className={`${inputClass} mt-1`}
            />
          </label>

          <label className="text-xs text-slate-400">
            Ecosystem
            <select
              value={ecosystem}
              onChange={(e) => applyParams({ ecosystem: e.target.value })}
              className={`${inputClass} mt-1`}
            >
              {ECOSYSTEMS.map((eco) => (
                <option key={eco || 'any'} value={eco}>
                  {eco || 'any'}
                </option>
              ))}
            </select>
          </label>

          <label className="text-xs text-slate-400">
            Depth
            <select
              value={depth}
              onChange={(e) => applyParams({ depth: e.target.value })}
              disabled={direct}
              className={`${inputClass} mt-1`}
            >
              {DEPTHS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 pb-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={direct}
              onChange={(e) => applyParams({ direct: e.target.checked ? 'true' : '' })}
              className="h-4 w-4 accent-flame-500"
            />
            Direct only
          </label>

          <button
            type="submit"
            disabled={loading || !nameInput.trim()}
            className="rounded-lg bg-flame-500 px-4 py-2 text-sm font-medium text-navy-950 transition hover:bg-flame-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? '…' : 'Explore'}
          </button>
        </form>
      </div>

      {loading && !nodeCount && <LoadingSpinner />}

      {error && !loading && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {!routeName && !loading && (
        <div className="rounded-xl border border-navy-700 bg-navy-900/60 px-6 py-16 text-center">
          <p className="text-sm text-slate-400">
            Enter a package name above — try <span className="text-flame-400">express</span> or{' '}
            <span className="text-flame-400">codemap-etl-smoke</span>.
          </p>
        </div>
      )}

      {routeName && nodeCount > 0 && (
        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
          <span className="rounded-lg border border-navy-600 bg-navy-900 px-3 py-1.5 text-flame-400">
            {routeName}
            {ecosystem ? ` (${ecosystem})` : ''}
          </span>
          <span>{nodeCount} nodes</span>
          <span>{linkCount} links</span>
          <span>{direct ? 'direct edges' : `up to ${depth} hops`}</span>
        </div>
      )}

      {nodeCount > 0 && (
        <div className="relative">
          <GraphVisualization />
          <NodeDetail />
        </div>
      )}
    </div>
  )
}
