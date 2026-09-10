# CodeMap

> Evidence-grounded software engineering knowledge graph that traces multi-hop dependencies and vulnerabilities across commits, issues, packages, and CVEs.

<!-- Screenshot placeholder -->

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Node.js 18+

## Quick Start

```bash
# 1. Start Neo4j
docker compose up -d

# 2. Seed the graph (optional, for UI testing)
cd scripts && python seed_graph.py

# 3. Start the backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 4. Start the frontend
cd frontend
npm install
npm run dev
```

## Documentation

- [docs/CONTEXT.md](docs/CONTEXT.md) — architecture, schema, and AI agent guidelines

## Project Structure

```
codemap/
├── backend/        FastAPI + LangChain AI service (port 8000)
├── frontend/       React + Vite + TailwindCSS (port 5173)
├── scripts/        Seed & utility scripts
├── docs/           Architecture docs
└── docker-compose.yml
```

## License

MIT
