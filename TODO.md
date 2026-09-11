# CodeMap — Project TODO

> Living checklist. Mark items `[x]` when done.

---

## Phase 1 — Infrastructure & Foundation

Everything that must exist before any feature code runs.

- [x] **Docker Compose for Neo4j**
  - [x] Create `docker-compose.yml` at project root
  - [x] Configure Neo4j Community container (ports `7474` / `7687`)
  - [x] Set initial password, enable `apoc` plugin if needed
  - [x] Add volume for persistent data
- [x] **Mock Seed Script (Day 1 Testing)**
  - [x] Create `scripts/seed.cypher` or `pipeline/seed_graph.py`
  - [x] Seed a 10–15 node mock dependency graph with 1 vulnerability for instant UI testing
- [x] **Root `README.md`**
  - [x] Project overview
  - [x] Prerequisites (Python 3.12+, Docker)
  - [x] Quick-start instructions (`docker compose up`, `cd backend && pip install -r requirements.txt`, `uvicorn app.main:app`)

---

## Phase 2 — Backend (Python FastAPI)

Build out the AI microservice.

### 2a. Core AI endpoints
- [x] **`POST /ai/search`** — main search endpoint
  - [x] Accept `{ prompt: str }`
  - [x] Use LangChain `GraphCypherQAChain` to translate NL → Cypher
  - [x] Validate returned Cypher is read-only (`MATCH`, `RETURN` only)
  - [x] Execute Cypher against Neo4j (parameterized)
  - [x] Use LLM to synthesize explanation of the sub-graph
  - [x] Return `{ success, graphData: { nodes, links }, explanation }`
- [x] **`GET /ai/graph/subgraph`** — fetch neighborhood of a package node
- [x] **`GET /ai/vulnerabilities/:id`** — fetch CVE/OSV detail + affected packages

### 2b. Services & middleware
- [x] `services/cypher_generator.py` — LangChain GraphCypherQAChain via Groq
- [x] `services/evidence_synthesizer.py` — explanation generation
- [x] `services/neo4j_connection.py` — async Neo4j driver, `run_cypher`, read-only enforcement
- [x] Input validation on all routes
- [x] Global error handling middleware

### 2c. Dependencies
- [x] Verify `requirements.txt` has all needed packages
- [x] Add `python-dotenv` if not present

---

## Phase 3 — Frontend (React)

Replace the Vite template with a real CodeMap UI.

### 3a. Install dependencies & configure
- [ ] `npm install react-force-graph react-router-dom axios`
- [ ] `frontend/.env` — verify `VITE_API_URL=http://localhost:8000`
- [ ] `index.html` — verify title is `"CodeMap"`

### 3b. Project structure
- [ ] Create `src/components/`, `src/pages/`, `src/services/`, `src/hooks/`, `src/context/`
- [ ] Delete template files: `App.css` (template styles), `assets/hero.png`, `assets/react.svg`, `assets/vite.svg`

### 3c. API service layer
- [ ] `src/services/api.js` — axios instance with `VITE_API_URL` base
  - [ ] `search(prompt)` → `POST /ai/search`
  - [ ] `getGraph(packageName)` → `GET /ai/graph/:packageName`
  - [ ] `getVulnerability(id)` → `GET /ai/vulnerabilities/:id`
  - [ ] `healthCheck()` → `GET /health`

### 3d. Pages & routing
- [ ] `src/App.jsx` — React Router setup (`/`, `/search`, `/graph/:id`)
- [ ] `src/pages/HomePage.jsx` — landing page with search bar
- [ ] `src/pages/GraphPage.jsx` — force-graph visualization + evidence sidebar
- [ ] `src/pages/VulnPage.jsx` — vulnerability detail view

### 3e. Core components
- [ ] `SearchBar.jsx` — input field + submit, sends prompt to `/ai/search`
- [ ] `GraphVisualization.jsx` — renders `react-force-graph` with nodes/links
  - [ ] Node coloring by type (Package=blue, Vulnerability=red, Issue=yellow, Commit=green)
  - [ ] Relationship labels on links
  - [ ] Click-to-expand node detail
- [ ] `EvidenceSidebar.jsx` — displays LLM-generated explanation
- [ ] `NodeDetail.jsx` — popup/panel showing node properties
- [ ] `LoadingSpinner.jsx` — loading state during search

### 3f. State management
- [ ] React Context or `useReducer` for search state
  - [ ] `query`, `graphData`, `explanation`, `loading`, `error`

---

## Phase 4 — ETL & Data Ingestion

Populate the graph with real-world data.

### 4a. ETL scripts (inside `backend/app/pipeline/`)
- [ ] **GitHub ETL**
  - [ ] Fetch repos, commits, issues via GitHub API
  - [ ] Create `Package`, `Commit`, `Issue` nodes
  - [ ] Create `FIXES`, `REFERENCES` relationships
- [ ] **OSV.dev ETL**
  - [ ] Fetch vulnerabilities from OSV API
  - [ ] Create `Vulnerability` nodes
  - [ ] Create `AFFECTS` relationships to affected packages
- [ ] **NVD ETL**
  - [ ] Fetch CVE data from NVD API
  - [ ] Create/update `Vulnerability` nodes with CVSS scores
  - [ ] Cross-reference with OSV data

### 4b. Ingestion runner
- [ ] CLI command or FastAPI endpoint to trigger ETL
- [ ] Idempotent upserts (don't duplicate nodes on re-run)
- [ ] Logging & progress reporting

### 4c. Dependency graph
- [ ] Parse `package.json`, `requirements.txt`, `pom.xml`, etc.
- [ ] Create `DEPENDS_ON` relationships between packages
- [ ] Support transitive dependency traversal

---

## Phase 5 — Documentation & Polish

### 5a. Code quality
- [ ] Add input validation to all backend routes
- [ ] Add error boundaries in React
- [ ] Add `.env.example` files for all services
- [ ] Consistent code style across all services

### 5b. Final polish
- [ ] Add proper favicon for CodeMap
- [ ] Responsive design for frontend
- [ ] Dark mode support (optional)

---

## Dependency Order

```
Phase 1 (Infra)
    └──► Phase 2 (Backend) ──► Phase 3 (Frontend)
                  └──► Phase 4 (ETL)
                           └──► Phase 5 (Docs & Polish)
```

Phase 1 must finish first. Phases 2 & 3 can be built sequentially. Phase 4 needs Phase 2. Phase 5 is ongoing.
