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
