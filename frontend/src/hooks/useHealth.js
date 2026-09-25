import { useState, useEffect } from 'react'
import { healthCheck } from '../services/api'

export default function useHealth() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let cancelled = false

    async function check() {
      try {
        const res = await healthCheck()
        if (!cancelled) {
          setStatus(res.data?.status === 'ok' ? 'online' : 'degraded')
        }
      } catch {
        if (!cancelled) setStatus('offline')
      }
    }

    check()
    const id = setInterval(check, 30000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  return status
}
