import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSearch } from '../context/SearchContext'

export default function SearchBar({ autoFocus = false, compact = false }) {
  const [value, setValue] = useState('')
  const { runSearch, loading } = useSearch()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    const prompt = value.trim()
    if (!prompt || loading) return
    navigate('/search')
    await runSearch(prompt)
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div
        className={`flex items-center gap-2 rounded-xl border border-navy-600 bg-navy-900/80 px-4 shadow-lg shadow-black/30 transition focus-within:border-flame-500/70 focus-within:ring-1 focus-within:ring-flame-500/40 ${
          compact ? 'py-2' : 'py-3'
        }`}
      >
        <svg
          className="h-5 w-5 shrink-0 text-flame-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M21 21l-4.35-4.35M17 10a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder='Ask about a dependency, CVE, or package… e.g. "which packages are affected by CVE-2024-3094?"'
          autoFocus={autoFocus}
          disabled={loading}
          className={`min-w-0 flex-1 bg-transparent text-slate-100 placeholder-slate-500 outline-none disabled:opacity-50 ${
            compact ? 'text-sm' : 'text-base'
          }`}
        />
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className={`shrink-0 rounded-lg bg-flame-500 font-medium text-navy-950 transition hover:bg-flame-400 disabled:cursor-not-allowed disabled:opacity-40 ${
            compact ? 'px-3 py-1 text-xs' : 'px-4 py-1.5 text-sm'
          }`}
        >
          {loading ? '…' : 'Search'}
        </button>
      </div>
    </form>
  )
}
