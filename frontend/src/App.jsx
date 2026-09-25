import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import HomePage from './pages/HomePage'
import GraphPage from './pages/GraphPage'
import VulnPage from './pages/VulnPage'
import useHealth from './hooks/useHealth'

const STATUS_STYLES = {
  online: 'bg-green-500',
  degraded: 'bg-yellow-500',
  offline: 'bg-red-500',
  checking: 'bg-slate-500',
}

function Header() {
  const status = useHealth()
  const location = useLocation()

  return (
    <header className="sticky top-0 z-30 border-b border-navy-700 bg-navy-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2">
          {/* <span>
            <img src="/public/logo.png" alt="image" />
          </span> */}
          <span className="text-lg font-bold tracking-tight text-white">
            Code<span className="text-flame-500">Map</span>
          </span>
        </Link>

        <nav className="flex items-center gap-4 text-sm">
          <Link
            to="/"
            className={`transition hover:text-flame-400 ${
              location.pathname === '/' ? 'text-flame-400' : 'text-slate-400'
            }`}
          >
            Home
          </Link>
          <Link
            to="/search"
            className={`transition hover:text-flame-400 ${
              location.pathname.startsWith('/search') ? 'text-flame-400' : 'text-slate-400'
            }`}
          >
            Search
          </Link>
          <span
            className="flex items-center gap-1.5 text-xs text-slate-500"
            title={`API: ${status}`}
          >
            <span className={`h-2 w-2 rounded-full ${STATUS_STYLES[status]}`} />
            API
          </span>
        </nav>
      </div>
    </header>
  )
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<GraphPage />} />
          <Route path="/graph/:id" element={<GraphPage />} />
          <Route path="/vulnerability/:id" element={<VulnPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="border-t border-navy-800 px-4 py-4 text-center text-xs text-slate-600">
        CodeMap — evidence-grounded dependency intelligence
      </footer>
    </div>
  )
}
