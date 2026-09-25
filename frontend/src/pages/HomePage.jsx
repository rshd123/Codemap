import { Link } from 'react-router-dom'
import SearchBar from '../components/SearchBar'

const FEATURES = [
  {
    title: 'Dependency Graph',
    body: 'Multi-hop traces across packages, commits, issues and CVEs — stored in Neo4j.',
    to: '/',
  },
  {
    title: 'Vulnerability Tracing',
    body: 'Ask plain-English questions and watch the graph expand from any affected package.',
    to: '/search',
  },
  {
    title: 'Evidence-Grounded',
    body: 'Every answer ships with the exact Cypher query and a generated explanation.',
    to: '/search',
  },
]

export default function HomePage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col items-center px-6 py-16 sm:py-24">
      <span className="mb-4 rounded-full border border-flame-500/40 bg-flame-500/10 px-3 py-1 text-xs font-medium text-flame-400">
        Evidence-grounded software intelligence
      </span>

      <h1 className="text-center text-4xl font-bold tracking-tight text-white sm:text-6xl">
        Map your dependencies with{' '}
        <span className="text-flame-500">CodeMap</span>
      </h1>

      <p className="mt-4 max-w-2xl text-center text-base text-slate-400 sm:text-lg">
        Ask questions in natural language and get back a visual dependency
        sub-graph, a generated Cypher query, and a plain-English explanation of
        every vulnerability it uncovers.
      </p>

      <div className="mt-8 w-full max-w-2xl">
        <SearchBar autoFocus />
      </div>

      <div className="mt-6 flex flex-wrap justify-center gap-3 text-xs text-slate-500">
        <span>Try:</span>
        {[
          'Which packages are affected by CVE-2024-3094?',
          'Show dependencies of lodash',
          'Find commits that fix open issues',
        ].map((s) => (
          <span
            key={s}
            className="rounded-md border border-navy-700 bg-navy-900 px-2 py-1 text-slate-400"
          >
            {s}
          </span>
        ))}
      </div>

      <div className="mt-16 grid w-full gap-6 sm:grid-cols-3">
        {FEATURES.map((f) => (
          <Link
            key={f.title}
            to={f.to}
            className="group rounded-xl border border-navy-700 bg-navy-900/60 p-5 transition hover:border-flame-500/50 hover:bg-navy-850"
          >
            <h3 className="text-sm font-semibold text-slate-100 group-hover:text-flame-400">
              {f.title}
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">{f.body}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
