# Backend API Endpoints

Base URL: `http://localhost:8000`

---

## GET /

Returns service status.

**Response:**
```json
{ "service": "codemap-ai-engine", "status": "running" }
```

---

## GET /health

Checks Neo4j connectivity.

**Response:**
```json
{ "status": "ok", "neo4j": "connected" }
```

---

## POST /ai/generate-cypher

Translates a natural language prompt into a Cypher query without executing it.

**Request Body:**
```json
{ "prompt": "Find all packages affected by CVE-2024-12345" }
```

**Response:**
```json
{ "cypher": "MATCH ...", "params": {} }
```

---

## POST /ai/explain-evidence

Generates a plain English explanation of a graph result for a given prompt and Cypher query.

**Request Body:**
```json
{ "prompt": "...", "cypher": "MATCH ...", "graphData": { "nodes": [], "links": [] } }
```

**Response:**
```json
{ "explanation": "..." }
```

---

## POST /ai/search

Full pipeline: prompt → Cypher → execute against Neo4j → explain the sub-graph.

**Request Body:**
```json
{ "prompt": "What vulnerabilities affect lodash?" }
```

**Response:**
```json
{
  "success": true,
  "cypher": "MATCH ...",
  "graphData": { "nodes": [...], "links": [...] },
  "explanation": "..."
}
```

---

## GET /ai/graph/subgraph?packageName=lodash

Fetches the 1-hop neighborhood of a package node (all directly connected entities).

**Query Param:** `packageName` (required)

**Response:**
```json
{
  "nodes": [{ "id": "...", "label": "Package", "name": "lodash", "version": "4.17.21" }],
  "links": [{ "source": "...", "target": "...", "type": "DEPENDS_ON" }]
}
```

---

## GET /ai/vulnerabilities/{vuln_id}

Fetches a CVE/OSV detail and all packages it affects.

**Path Param:** `vuln_id` — e.g. `CVE-2024-12345`

**Response:**
```json
{
  "vulnerability": { "id": "CVE-2024-12345", "cvss": 8.6, "summary": "..." },
  "affected_packages": [{ "id": "...", "label": "Package", "name": "lodash" }],
  "graphData": { "nodes": [...], "links": [...] }
}
```

---

## GET /graph/dependencies

Walks the `DEPENDS_ON` graph for a package and returns the reachable sub-graph.

**Query Params:**

| Param | Default | Description |
|-------|---------|-------------|
| `name` | — | Package name (required) |
| `ecosystem` | any | `npm`, `pypi`, `maven`, `cargo`, ... |
| `depth` | `4` | Max `DEPENDS_ON` hops (1–8) |
| `limit` | `300` | Max rows returned (1–1000) |
| `direct` | `false` | Return only direct dependencies |

**Response:**
```json
{
  "nodes": [{ "id": "4:...", "label": "Package", "name": "express", "ecosystem": "npm" }],
  "links": [{ "source": "4:...", "target": "4:...", "type": "DEPENDS_ON", "spec": "^2.0.0" }],
  "root": { "name": "express", "ecosystem": "npm", "maxDepth": 4 }
}
```

---

## POST /etl/run

Starts an ingestion run in the background. Returns `409` if a run is already active and `422` for invalid input.

**Request Body:**
```json
{
  "sources": ["deps", "github", "osv", "nvd"],
  "repo": "expressjs/express",
  "packages": [{ "name": "lodash", "ecosystem": "npm" }],
  "cve_ids": ["CVE-2021-23337"],
  "keywords": ["lodash"],
  "ecosystem": "npm",
  "manifests": [{ "filename": "package.json", "content": "{...}" }],
  "max_items": 25,
  "cross_ref": true,
  "max_commits": 20,
  "max_issues": 10,
  "max_timelines": 5
}
```

`sources` may be omitted — sources are derived from the inputs that are present.

**Response:** `202`
```json
{ "jobId": "aa51f42f20df", "status": "running", "sources": ["osv"] }
```

---

## GET /etl/status

Status of the current (or most recent) run plus its log lines.

**Response:**
```json
{
  "jobId": "aa51f42f20df",
  "status": "running",
  "sources": ["osv"],
  "startedAt": "2026-09-25T16:31:24+00:00",
  "finishedAt": null,
  "progress": { "event": "job_started", "source": "osv" },
  "logs": ["[2026-09-25T16:31:24+00:00] job 'osv' started"],
  "error": null,
  "summary": null,
  "history": [{ "jobId": "...", "status": "completed" }]
}
```

`status` is one of `idle`, `running`, `completed`, `failed`.

---

## GET /etl/jobs/{job_id}

Fetches a finished run by id. Returns `404` when the job is unknown.

**Response:**
```json
{
  "jobId": "aa51f42f20df",
  "status": "completed",
  "sources": ["osv"],
  "startedAt": "...",
  "finishedAt": "...",
  "logs": ["..."],
  "error": null,
  "summary": { "success": true, "jobs": [...], "totals": { "nodes_created": 3, "relationships_created": 2 }, "requests": 1 }
}
```
