import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

export function search(prompt) {
  return api.post('/ai/search', { prompt })
}

export function getGraph(packageName) {
  return api.get('/ai/graph/subgraph', { params: { packageName } })
}

export function getVulnerability(id) {
  return api.get(`/ai/vulnerabilities/${encodeURIComponent(id)}`)
}

export function healthCheck() {
  return api.get('/health')
}

export default api
