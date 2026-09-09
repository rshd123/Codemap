# CodeMap AI Rules & Orientation

## Project Summary
CodeMap is an evidence-grounded software engineering knowledge graph that traces multi-hop dependencies and vulnerabilities across GitHub commits, issues, packages, and CVEs using Neo4j and LLMs.

## Architecture

```
frontend/        React + Vite + TailwindCSS (Port 5173)
    |
    v
backend/         FastAPI + LangChain (Port 8000)
    |
    v
Neo4j            Graph Database (Port 7687)
```

## Tech Stack
- Frontend: React + Vite + TailwindCSS + react-force-graph
- Backend: Python FastAPI + LangChain (Port 8000)
- Database: Neo4j in Docker (Port 7474 / 7687)

## Rules for AI Agent
- Never interpolate raw strings into Cypher queries; use query parameters (`$pkgName`).
- Keep Cypher queries read-only during user searches (`MATCH`, `RETURN`).
- Never run frontend and backend servers — only the user will run those. Stop after making code changes.
- All AI/Cypher logic lives in `backend/`. Do not duplicate it elsewhere.
