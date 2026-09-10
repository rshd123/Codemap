<h1 align="center">CodeMap</h1>

<p align="center">
  <strong>AI-Powered Software Supply Chain Intelligence Platform</strong>
</p>

<p align="center">
  Trace hidden multi-hop vulnerabilities across packages, commits, issues, and CVEs — powered by Knowledge Graphs and LLMs.
</p>

---

## Why CodeMap?

Traditional security scanners tell you *what* is vulnerable. CodeMap tells you *how* vulnerabilities ripple through your entire dependency tree.

CodeMap converts your software ecosystem into an interconnected **Neo4j knowledge graph** and uses **LLMs** to perform multi-hop graph traversals via Cypher queries — producing evidence-backed answers about hidden dependency risks that flat text-vector RAG systems simply cannot find.

**Key capabilities:**

- **Multi-hop dependency tracing** — follow `DEPENDS_ON` chains across direct and transitive dependencies to surface deeply buried risks
- **Vulnerability correlation** — link CVEs/OSVs from NVD and OSV.dev to the exact packages and commits they affect
- **Natural language search** — ask questions like *"Which packages are affected by CVE-2024-12345 through transitive dependencies?"* and get graph-backed answers with plain English explanations
- **Interactive visualization** — explore the dependency graph with force-directed 2D rendering, node coloring by type, and click-to-expand details
- **Evidence-grounded explanations** — every answer includes the Cypher query, the sub-graph, and an LLM-synthesized step-by-step explanation

---

## Tech Stack

<div align="center">

<img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
<img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" />
<img src="https://img.shields.io/badge/Tailwind_CSS-38BDF8?style=for-the-badge&logo=tailwindcss&logoColor=white" />
<img src="https://img.shields.io/badge/React_Force_Graph-FF6B6B?style=for-the-badge" />

<br/>

<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
<img src="https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white" />
<img src="https://img.shields.io/badge/Groq-F55036?style=for-the-badge" />

<br/>

<img src="https://img.shields.io/badge/Neo4j-008CC1?style=for-the-badge&logo=neo4j&logoColor=white" />
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />

</div>



## Graph Schema

| Node | Properties |
|------|-----------|
| `Package` | `name`, `version`, `ecosystem` |
| `Vulnerability` | `id`, `cvss`, `summary`, `source` |
| `Issue` | `id`, `title`, `status`, `url` |
| `Commit` | `hash`, `message`, `timestamp`, `author` |

| Relationship | From → To |
|-------------|-----------|
| `DEPENDS_ON` | Package → Package |
| `AFFECTS` | Vulnerability → Package |
| `FIXES` | Commit → Issue |
| `PATCHES` | Commit → Vulnerability |
| `REFERENCES` | Issue → Vulnerability |

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| npm | 9+ | Frontend package manager |
| Docker | 24+ | Container runtime for Neo4j |
| Docker Compose | v2+ | Multi-container orchestration |
| Groq API Key | — | LLM inference (free tier available at [console.groq.com](https://console.groq.com)) |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-org/codemap.git
cd codemap

# 2. Start Neo4j
docker compose up -d

# 3. Seed the graph (optional, for UI testing)
cd scripts
python seed_graph.py
cd ..

# 4. Start the backend
cd backend
cp .env.example .env   # add your Groq API key
pip install -r requirements.txt
uvicorn app.main:app --reload

# 5. Start the frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and start searching.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service status |
| `GET` | `/health` | Neo4j connectivity check |
| `POST` | `/ai/search` | Full NL → Cypher → execute → explain pipeline |
| `POST` | `/ai/generate-cypher` | NL prompt → Cypher query only |
| `POST` | `/ai/explain-evidence` | Generate explanation of graph results |
| `GET` | `/ai/graph/subgraph?packageName=` | 1-hop neighborhood of a package |
| `GET` | `/ai/vulnerabilities/{id}` | CVE detail + affected packages |

Full request/response examples: [docs/endpoints.md](docs/endpoints.md)

---

## Project Structure

```
codemap/
├── backend/              # FastAPI + LangChain AI service (port 8000)
│   ├── app/
│   │   ├── routes/       # API route handlers
│   │   ├── services/     # Cypher generation, evidence synthesis, Neo4j
│   │   └── models/       # Pydantic schemas
│   └── requirements.txt
├── frontend/             # React + Vite + TailwindCSS (port 5173)
│   └── src/
├── scripts/              # Seed & utility scripts
├── docs/                 # Architecture & API docs
└── docker-compose.yml    # Neo4j container
```

---

## Documentation

- [API Endpoints](docs/endpoints.md)

---

