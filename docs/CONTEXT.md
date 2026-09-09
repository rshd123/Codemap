# Project Codemap

## 1. Project Identity & Purpose
CodeMap is an evidence-grounded software engineering knowledge graph system. It helps developers discover hidden multi-hop relationships across source code, direct and transitive dependencies, security vulnerabilities (CVEs), GitHub issues, commits, releases, and security advisories (OSV/NVD).

Unlike traditional search or flat text-vector RAG approaches, CodeMap converts the entire software ecosystem into an interconnected Neo4j graph and uses LLMs to perform multi-hop graph traversals (`Cypher`) to produce evidence-backed answers.

---

## 2. System Architecture & Tech Stack

CodeMap uses a two-service architecture:

1. **React Frontend (`/frontend`)**
   - **Stack:** React, Vite, TailwindCSS, `react-force-graph`
   - **Port:** `5173`
   - **Role:** Interactive search interface, 2D/3D force-graph visualization, and AI evidence sidebar.

2. **Python AI Backend (`/backend`)**
   - **Stack:** Python 3.12+, FastAPI, LangChain (`GraphCypherQAChain` via Groq), `pydantic`, `neo4j`
   - **Port:** `8000`
   - **Role:** Natural language to read-only Cypher query generation, graph evidence synthesis, and ETL background pipelines (GitHub, OSV.dev, NVD).

3. **Graph Database**
   - **Engine:** Neo4j Community Server (Docker container)
   - **Ports:** `7474` (Browser HTTP UI), `7687` (Bolt Protocol)

---

## 3. Neo4j Graph Schema Blueprint

### Nodes
- `(:Package {name: String, version: String, ecosystem: String})`
- `(:Vulnerability {id: String, cvss: Float, summary: String, source: String})`
- `(:Issue {id: String, title: String, status: String, url: String})`
- `(:Commit {hash: String, message: String, timestamp: String, author: String})`

### Allowed Relationships
- `(:Package)-[:DEPENDS_ON]->(:Package)`
- `(:Vulnerability)-[:AFFECTS]->(:Package)`
- `(:Commit)-[:FIXES]->(:Issue)`
- `(:Commit)-[:PATCHES]->(:Vulnerability)`
- `(:Issue)-[:REFERENCES]->(:Vulnerability)`

---

## 4. End-to-End Search Data Flow

1. **User Prompt:** React UI sends `POST /ai/search` with a natural language query to the Python FastAPI backend (`:8000`).
2. **AI Translation:** LangChain translates the prompt into a read-only Cypher query.
3. **Graph Traversal:** The backend executes the Cypher against Neo4j over Bolt (`:7687`) and retrieves matching nodes/links.
4. **Evidence Synthesis:** The backend uses LLM to generate a step-by-step plain English explanation of the sub-graph.
5. **Render:** Backend returns `{ success: true, graphData: { nodes, links }, explanation }` to React for graph rendering.

---

## 5. Critical Guidelines for AI Coding Agents

- **Query Security:** NEVER interpolate raw user inputs directly into Cypher strings. Always pass dynamic parameters (`$pkgName`, `$vulnId`) to prevent query injections.
- **Read-Only Enforcements:** All LLM-generated Cypher queries must be strictly read-only (`MATCH`, `WHERE`, `RETURN`).
- **Graph Output Contract:** API endpoints returning graph data MUST format responses as `{ nodes: [{ id, label, ... }], links: [{ source, target, type }] }` to match `react-force-graph` props.
- **Separation of Concerns:** Keep route handlers clean; delegate AI generation tasks to service modules in `backend/app/services/`.
