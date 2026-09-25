import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useSearch } from '../context/SearchContext'
import { getGraph } from '../services/api'
import SearchBar from '../components/SearchBar'
import GraphVisualization from '../components/GraphVisualization'
import EvidenceSidebar from '../components/EvidenceSidebar'
import NodeDetail from '../components/NodeDetail'
import LoadingSpinner from '../components/LoadingSpinner'

export default function GraphPage() {
  const { id } = useParams()
  const {
    graphData,
    explanation,
    loading,
    error,
    setGraph,
    reset,
    selectNode,
  } = useSearch()
  const [pkgLoading, setPkgLoading] = useState(false)
  const [pkgError, setPkgError] = useState(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setPkgLoading(true)
    setPkgError(null)
    reset()
    selectNode(null)

    getGraph(id)
      .then((res) => {
        if (cancelled) return
        setGraph(res.data)
      })
      .catch((err) => {
        if (cancelled) return
        setPkgError(err.response?.data?.detail || err.message || 'Failed to load graph')
      })
      .finally(() => {
        if (!cancelled) setPkgLoading(false)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const isLoading = pkgLoading || loading
  const errorMsg = pkgError || error
  const hasData = (graphData?.nodes?.length || 0) > 0

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex-1">
          <SearchBar compact />
        </div>
        {id && (
          <span className="rounded-lg border border-navy-600 bg-navy-900 px-3 py-2 text-xs text-flame-400">
            Package: {id}
          </span>
        )}
      </div>

      {isLoading && !hasData && <LoadingSpinner />}

      {errorMsg && !isLoading && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {errorMsg}
        </div>
      )}

      {!isLoading && !errorMsg && !hasData && !explanation && (
        <div className="rounded-xl border border-navy-700 bg-navy-900/60 px-6 py-16 text-center">
          <p className="text-sm text-slate-400">
            Nothing to show yet. Search above, or{' '}
            <a href="/" className="text-flame-400 underline">
              go back home
            </a>{' '}
            for example queries.
          </p>
        </div>
      )}

      {(hasData || explanation) && (
        <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
          <div className="relative">
            <GraphVisualization />
            <NodeDetail />
          </div>
          <EvidenceSidebar />
        </div>
      )}
    </div>
  )
}
