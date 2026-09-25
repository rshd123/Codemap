export default function LoadingSpinner({ label = 'Searching dependency graph…' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <div className="relative h-12 w-12">
        <div className="absolute inset-0 rounded-full border-2 border-navy-700" />
        <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-flame-500" />
      </div>
      <p className="text-sm text-slate-400">{label}</p>
    </div>
  )
}
