import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useSearch } from '../context/SearchContext'
import { explainEvidence, generateCypher } from '../services/api'

const inputClass =
  'w-full rounded-lg border border-navy-600 bg-navy-900/80 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-flame-500/70 focus:ring-1 focus:ring-flame-500/40'
const buttonClass =
  'rounded-lg bg-flame-500 px-4 py-2 text-sm font-medium text-navy-950 transition hover:bg-flame-400 disabled:cursor-not-allowed disabled:opacity-40'
const ghostClass =
  'rounded-lg border border-navy-600 px-4 py-2 text-sm text-slate-200 transition hover:border-flame-500/60 hover:text-flame-400 disabled:cursor-not-allowed disabled:opacity-40'

function message(err) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join('; ')
  return err?.message || 'Request failed'
}

export default function CypherPage() {
  const { graphData } = useSearch()
  const [prompt, setPrompt] = useState('')
  const [cypher, setCypher] = useState('')
  const [params, setParams] = useState(null)
  const [explanation, setExplanation] = useState('')
  const [pending, setPending] = useState(null)
  const [error, setError] = useState(null)

  const hasGraph = (graphData?.nodes?.length || 0) > 0

  async function handleGenerate(e) {
    e.preventDefault()
    if (!prompt.trim() || pending) return
    setPending('generate')
    setError(null)
    setExplanation('')
    try {
      const res = await generateCypher(prompt.trim())
      setCypher(res.data.cypher || '')
      setParams(res.data.params || null)
    } catch (err) {
      setError(message(err))
    } finally {
      setPending(null)
    }
  }

  async function handleExplain() {
    if (!prompt.trim() || !cypher || pending) return
    setPending('explain')
    setError(null)
    try {
      const res = await explainEvidence({ prompt: prompt.trim(), cypher, graphData })
      setExplanation(res.data.explanation || '')
    } catch (err) {
      setError(message(err))
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-6">
      <div>
        <h1 className="text-lg font-semibold text-white">Cypher lab</h1>
        <p className="text-sm text-slate-400">
          Step through the pipeline by hand: prompt → Cypher → evidence explanation.
        </p>
      </div>

      <form onSubmit={handleGenerate} className="flex flex-col gap-3">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          placeholder='e.g. "Which packages are affected by CVE-2021-23337?"'
          className={`${inputClass} resize-y`}
        />
        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={!prompt.trim() || Boolean(pending)}
            className={buttonClass}
          >
            {pending === 'generate' ? 'Generating…' : 'Generate Cypher'}
          </button>
          <button
            type="button"
            onClick={handleExplain}
            disabled={!cypher || Boolean(pending)}
            className={ghostClass}
          >
            {pending === 'explain' ? 'Explaining…' : 'Explain evidence'}
          </button>
          <Link to="/search" className={ghostClass}>
            Full search
          </Link>
        </div>
      </form>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {cypher && (
        <section className="rounded-xl border border-navy-700 bg-navy-900/60 p-4">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-flame-500">
            Generated Cypher
          </h2>
          <pre className="overflow-x-auto rounded-lg border border-navy-800 bg-navy-950/80 p-3 text-xs leading-relaxed text-flame-300">
            {cypher}
          </pre>
          {params && Object.keys(params).length > 0 && (
            <pre className="mt-2 overflow-x-auto rounded-lg border border-navy-800 bg-navy-950/80 p-3 text-xs text-slate-400">
              {JSON.stringify(params, null, 2)}
            </pre>
          )}
          <p className="mt-2 text-xs text-slate-500">
            Explanation runs against {hasGraph ? 'the currently loaded sub-graph' : 'an empty graph — run a search first to attach results'}.
          </p>
        </section>
      )}

      {explanation && (
        <section className="rounded-xl border border-navy-700 bg-navy-900/60 p-4">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-flame-500">
            Evidence
          </h2>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{explanation}</p>
        </section>
      )}
    </div>
  )
}
