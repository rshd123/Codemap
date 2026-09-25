import { useCallback, useEffect, useState } from 'react'
import { getEtlJob, getEtlStatus, runEtl } from '../services/api'

const SOURCES = ['deps', 'github', 'osv', 'nvd']
const MANIFESTS = ['package.json', 'requirements.txt', 'pyproject.toml', 'pom.xml', 'Cargo.toml']
const ECOSYSTEMS = ['', 'npm', 'pypi', 'maven', 'cargo', 'go', 'gem', 'nuget']

const STATUS_STYLES = {
  idle: 'bg-slate-500/15 text-slate-300 border-slate-500/40',
  running: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40',
  completed: 'bg-green-500/15 text-green-300 border-green-500/40',
  failed: 'bg-red-500/15 text-red-300 border-red-500/40',
}

const inputClass =
  'w-full rounded-lg border border-navy-600 bg-navy-900/80 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-flame-500/70 focus:ring-1 focus:ring-flame-500/40'
const labelClass = 'block text-xs text-slate-400'
const cardClass = 'rounded-xl border border-navy-700 bg-navy-900/60 p-4'
const buttonClass =
  'rounded-lg bg-flame-500 px-4 py-2 text-sm font-medium text-navy-950 transition hover:bg-flame-400 disabled:cursor-not-allowed disabled:opacity-40'

function formatDetail(err) {
  const detail = err?.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => `${(item.loc || []).join('.')}: ${item.msg}`)
      .join('; ')
  }
  if (typeof detail === 'string') return detail
  if (err?.response?.status === 409) return 'An ETL run is already in progress.'
  return err?.message || 'Request failed'
}

function splitList(value) {
  return value
    .split(/[\n,]/)
    .map((part) => part.trim())
    .filter(Boolean)
}

export default function IngestPage() {
  const [selectedSources, setSelectedSources] = useState([])
  const [repo, setRepo] = useState('')
  const [packages, setPackages] = useState('')
  const [cves, setCves] = useState('')
  const [keywords, setKeywords] = useState('')
  const [ecosystem, setEcosystem] = useState('')
  const [manifestFile, setManifestFile] = useState('package.json')
  const [manifestText, setManifestText] = useState('')
  const [maxItems, setMaxItems] = useState(25)
  const [maxCommits, setMaxCommits] = useState(10)
  const [maxIssues, setMaxIssues] = useState(10)
  const [maxTimelines, setMaxTimelines] = useState(3)
  const [crossRef, setCrossRef] = useState(true)

  const [starting, setStarting] = useState(false)
  const [formError, setFormError] = useState(null)
  const [status, setStatus] = useState(null)
  const [jobDetail, setJobDetail] = useState(null)

  const statusValue = status?.status || 'idle'
  const isActive = starting || statusValue === 'running'

  const refresh = useCallback(async () => {
    try {
      const res = await getEtlStatus()
      setStatus(res.data)
      return res.data
    } catch {
      return null
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    getEtlStatus()
      .then((res) => {
        if (!cancelled) setStatus(res.data)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!isActive) return undefined
    const timer = setInterval(async () => {
      const next = await refresh()
      if (next && next.status !== 'running') setStarting(false)
    }, 2000)
    return () => clearInterval(timer)
  }, [isActive, refresh])

  function toggleSource(source) {
    setSelectedSources((prev) =>
      prev.includes(source) ? prev.filter((s) => s !== source) : [...prev, source],
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError(null)
    setJobDetail(null)

    const packageRows = splitList(packages).map((line) => {
      const [name, eco, version] = line.split(':')
      const row = { name: name.trim() }
      if (eco && eco.trim()) row.ecosystem = eco.trim()
      if (version && version.trim()) row.version = version.trim()
      return row
    })
    const manifestContent = manifestText.trim()

    if (!repo.trim() && !packageRows.length && !splitList(cves).length && !splitList(keywords).length && !manifestContent) {
      setFormError('Provide at least one input: repo, package, CVE id, keyword or manifest.')
      return
    }

    const payload = {
      repo: repo.trim() || null,
      packages: packageRows,
      cve_ids: splitList(cves).map((value) => value.toUpperCase()),
      keywords: splitList(keywords),
      ecosystem: ecosystem || null,
      manifests: manifestContent ? [{ filename: manifestFile, content: manifestContent }] : [],
      max_items: Number(maxItems),
      cross_ref: Boolean(crossRef),
      max_commits: Number(maxCommits),
      max_issues: Number(maxIssues),
      max_timelines: Number(maxTimelines),
    }
    if (selectedSources.length) payload.sources = selectedSources

    setStarting(true)
    try {
      await runEtl(payload)
      await refresh()
    } catch (err) {
      setStarting(false)
      setFormError(formatDetail(err))
    }
  }

  async function openJob(jobId) {
    try {
      const res = await getEtlJob(jobId)
      setJobDetail(res.data)
    } catch (err) {
      setFormError(formatDetail(err))
    }
  }

  const totals = status?.summary?.totals || null
  const jobs = status?.summary?.jobs || []
  const history = status?.history || []

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-white">Ingestion console</h1>
          <p className="text-sm text-slate-400">
            Push GitHub, OSV.dev, NVD and manifest data into the graph.
          </p>
        </div>
        <span
          className={`rounded-full border px-3 py-1 text-xs font-semibold ${STATUS_STYLES[statusValue] || STATUS_STYLES.idle}`}
        >
          {isActive ? 'RUNNING' : statusValue.toUpperCase()}
        </span>
      </div>

      {formError && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {formError}
        </div>
      )}

      <form onSubmit={handleSubmit} className="grid gap-4 lg:grid-cols-2">
        <section className={`${cardClass} flex flex-col gap-3`}>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-flame-500">Inputs</h2>

          <div>
            <span className={labelClass}>Sources (none selected = auto-derive)</span>
            <div className="mt-1 flex flex-wrap gap-3">
              {SOURCES.map((source) => (
                <label key={source} className="flex items-center gap-2 text-xs text-slate-300">
                  <input
                    type="checkbox"
                    checked={selectedSources.includes(source)}
                    onChange={() => toggleSource(source)}
                    className="h-4 w-4 accent-flame-500"
                  />
                  {source}
                </label>
              ))}
            </div>
          </div>

          <label className={labelClass}>
            GitHub repository
            <input
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="expressjs/express"
              className={`${inputClass} mt-1`}
            />
          </label>

          <label className={labelClass}>
            Packages (one per line, <span className="text-slate-500">name[:ecosystem[:version]]</span>)
            <textarea
              value={packages}
              onChange={(e) => setPackages(e.target.value)}
              rows={3}
              placeholder={'lodash:4.17.21\nflask:pypi:3.0.0'}
              className={`${inputClass} mt-1 resize-y font-mono`}
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className={labelClass}>
              CVE / GHSA ids
              <input
                value={cves}
                onChange={(e) => setCves(e.target.value)}
                placeholder="CVE-2021-23337, GHSA-xxxx-xxxx-xxxx"
                className={`${inputClass} mt-1`}
              />
            </label>
            <label className={labelClass}>
              NVD keywords
              <input
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="lodash"
                className={`${inputClass} mt-1`}
              />
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className={labelClass}>
              Ecosystem
              <select
                value={ecosystem}
                onChange={(e) => setEcosystem(e.target.value)}
                className={`${inputClass} mt-1`}
              >
                {ECOSYSTEMS.map((eco) => (
                  <option key={eco || 'any'} value={eco}>
                    {eco || 'any'}
                  </option>
                ))}
              </select>
            </label>
            <label className={labelClass}>
              Max items per source
              <input
                type="number"
                min="1"
                max="200"
                value={maxItems}
                onChange={(e) => setMaxItems(e.target.value)}
                className={`${inputClass} mt-1`}
              />
            </label>
          </div>

          <label className="flex items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={crossRef}
              onChange={(e) => setCrossRef(e.target.checked)}
              className="h-4 w-4 accent-flame-500"
            />
            Cross-reference NVD results with OSV.dev
          </label>
        </section>

        <section className={`${cardClass} flex flex-col gap-3`}>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-flame-500">
            Manifest &amp; limits
          </h2>

          <label className={labelClass}>
            Manifest file
            <select
              value={manifestFile}
              onChange={(e) => setManifestFile(e.target.value)}
              className={`${inputClass} mt-1`}
            >
              {MANIFESTS.map((file) => (
                <option key={file} value={file}>
                  {file}
                </option>
              ))}
            </select>
          </label>

          <label className={labelClass}>
            Manifest contents
            <textarea
              value={manifestText}
              onChange={(e) => setManifestText(e.target.value)}
              rows={8}
              placeholder={'{\n  "name": "my-app",\n  "dependencies": { "lodash": "^4.17.21" }\n}'}
              className={`${inputClass} mt-1 resize-y font-mono`}
            />
          </label>

          <div className="grid grid-cols-3 gap-3">
            <label className={labelClass}>
              Commits
              <input
                type="number"
                min="0"
                max="100"
                value={maxCommits}
                onChange={(e) => setMaxCommits(e.target.value)}
                className={`${inputClass} mt-1`}
              />
            </label>
            <label className={labelClass}>
              Issues
              <input
                type="number"
                min="0"
                max="100"
                value={maxIssues}
                onChange={(e) => setMaxIssues(e.target.value)}
                className={`${inputClass} mt-1`}
              />
            </label>
            <label className={labelClass}>
              Timelines
              <input
                type="number"
                min="0"
                max="50"
                value={maxTimelines}
                onChange={(e) => setMaxTimelines(e.target.value)}
                className={`${inputClass} mt-1`}
              />
            </label>
          </div>

          <button type="submit" disabled={isActive} className={buttonClass}>
            {isActive ? 'Running…' : 'Run ingestion'}
          </button>
        </section>
      </form>

      <section className={cardClass}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-flame-500">Run status</h2>
          <button
            type="button"
            onClick={refresh}
            className="rounded-lg border border-navy-600 px-3 py-1 text-xs text-slate-300 transition hover:border-flame-500/60 hover:text-flame-400"
          >
            Refresh
          </button>
        </div>

        <dl className="grid gap-3 sm:grid-cols-4">
          <div className="rounded-lg border border-navy-700 bg-navy-950/50 px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-slate-500">Nodes created</dt>
            <dd className="text-lg font-semibold text-white">{totals?.nodes_created ?? '—'}</dd>
          </div>
          <div className="rounded-lg border border-navy-700 bg-navy-950/50 px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-slate-500">Relationships</dt>
            <dd className="text-lg font-semibold text-white">{totals?.relationships_created ?? '—'}</dd>
          </div>
          <div className="rounded-lg border border-navy-700 bg-navy-950/50 px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-slate-500">API requests</dt>
            <dd className="text-lg font-semibold text-white">{status?.summary?.requests ?? '—'}</dd>
          </div>
          <div className="rounded-lg border border-navy-700 bg-navy-950/50 px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-slate-500">Duration</dt>
            <dd className="text-lg font-semibold text-white">
              {status?.summary?.durationSeconds != null ? `${status.summary.durationSeconds}s` : '—'}
            </dd>
          </div>
        </dl>

        {jobs.length > 0 && (
          <table className="mt-4 w-full text-left text-xs">
            <thead className="text-slate-500">
              <tr className="border-b border-navy-700">
                <th className="py-2">Source</th>
                <th className="py-2">Status</th>
                <th className="py-2">Nodes</th>
                <th className="py-2">Rels</th>
                <th className="py-2">Time</th>
                <th className="py-2">Error</th>
              </tr>
            </thead>
            <tbody className="text-slate-300">
              {jobs.map((job) => (
                <tr key={job.source} className="border-b border-navy-800">
                  <td className="py-2 font-medium text-flame-400">{job.source}</td>
                  <td className="py-2">{job.status}</td>
                  <td className="py-2">{job.counts?.nodes_created ?? 0}</td>
                  <td className="py-2">{job.counts?.relationships_created ?? 0}</td>
                  <td className="py-2">{job.durationSeconds}s</td>
                  <td className="py-2 text-red-300">{job.error || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {status?.logs?.length > 0 && (
          <pre className="mt-4 max-h-56 overflow-auto rounded-lg border border-navy-800 bg-navy-950/60 p-3 text-[11px] leading-relaxed text-slate-400">
            {status.logs.join('\n')}
          </pre>
        )}
      </section>

      <section className={cardClass}>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-flame-500">Job history</h2>
        {history.length === 0 ? (
          <p className="text-sm text-slate-500">No runs yet — start one above.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {history.map((entry) => (
              <li key={entry.jobId}>
                <button
                  type="button"
                  onClick={() => openJob(entry.jobId)}
                  className="flex w-full items-center justify-between rounded-lg border border-navy-700 bg-navy-950/40 px-3 py-2 text-left text-xs text-slate-300 transition hover:border-flame-500/50"
                >
                  <span className="font-mono">{entry.jobId}</span>
                  <span>{(entry.sources || []).join(', ') || '—'}</span>
                  <span className={entry.status === 'completed' ? 'text-green-400' : 'text-red-400'}>
                    {entry.status}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {jobDetail && (
          <div className="mt-4 rounded-lg border border-navy-700 bg-navy-950/50 p-3 text-xs text-slate-300">
            <p className="mb-2 font-mono text-flame-400">{jobDetail.jobId}</p>
            <p>
              {jobDetail.status} · {(jobDetail.sources || []).join(', ')} ·{' '}
              {jobDetail.summary?.totals?.nodes_created ?? 0} nodes /{' '}
              {jobDetail.summary?.totals?.relationships_created ?? 0} relationships
            </p>
            {jobDetail.error && <p className="mt-1 text-red-300">{jobDetail.error}</p>}
            {jobDetail.logs?.length > 0 && (
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-[11px] text-slate-500">
                {jobDetail.logs.join('\n')}
              </pre>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
