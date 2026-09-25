import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

export function search(prompt) {
  return api.post('/ai/search', { prompt })
}

export function generateCypher(prompt) {
  return api.post('/ai/generate-cypher', { prompt })
}

export function explainEvidence(payload) {
  return api.post('/ai/explain-evidence', payload)
}

export function getGraph(packageName) {
  return api.get('/ai/graph/subgraph', { params: { packageName } })
}

export function getVulnerability(id) {
  return api.get(`/ai/vulnerabilities/${encodeURIComponent(id)}`)
}

export function getDependencies({ name, ecosystem, depth, limit, direct } = {}) {
  const params = {}
  if (name) params.name = name
  if (ecosystem) params.ecosystem = ecosystem
  if (depth) params.depth = depth
  if (limit) params.limit = limit
  if (direct !== undefined && direct !== null) params.direct = direct
  return api.get('/graph/dependencies', { params })
}

export function runEtl(payload) {
  return api.post('/etl/run', payload)
}

export function getEtlStatus() {
  return api.get('/etl/status')
}

export function getEtlJob(jobId) {
  return api.get(`/etl/jobs/${encodeURIComponent(jobId)}`)
}

export function healthCheck() {
  return api.get('/health')
}

export default api
