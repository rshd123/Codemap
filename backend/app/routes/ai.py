from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    CypherRequest,
    CypherResponse,
    ExplainRequest,
    ExplainResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.cypher_generator import generate_cypher
from app.services.evidence_synthesizer import explain_evidence
from app.services.graph_serializer import to_graph_data
from app.services.neo4j_connection import run_cypher

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate-cypher", response_model=CypherResponse)
async def generate_cypher_endpoint(req: CypherRequest):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    result = await generate_cypher(req.prompt)

    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])

    return CypherResponse(cypher=result["cypher"], params=result["params"])


@router.post("/explain-evidence", response_model=ExplainResponse)
async def explain_evidence_endpoint(req: ExplainRequest):
    if not req.prompt or not req.cypher:
        raise HTTPException(status_code=400, detail="Prompt and cypher are required")

    explanation = await explain_evidence(req.prompt, req.cypher, req.graphData)
    return ExplainResponse(explanation=explanation)


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    """Full search pipeline: prompt → Cypher → execute → explain."""
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Step 1: Generate Cypher from prompt
    gen = await generate_cypher(req.prompt)
    if gen.get("error"):
        raise HTTPException(status_code=422, detail=gen["error"])

    cypher = gen["cypher"]
    params = gen.get("params", {})

    # Step 2: Execute Cypher against Neo4j
    records = await run_cypher(cypher, params)

    # Step 3: Build graph data (nodes + links)
    graph_data = to_graph_data(records)

    # Step 4: Generate explanation
    explanation = await explain_evidence(req.prompt, cypher, graph_data)

    return SearchResponse(
        success=True,
        cypher=cypher,
        graphData=graph_data,
        explanation=explanation,
    )


@router.get("/graph/subgraph")
async def get_subgraph(packageName: str = Query(..., min_length=1, max_length=200, description="Package name to explore")):
    """Fetch the neighborhood of a package node (1-hop relationships)."""
    cypher = """
    MATCH (p:Package {name: $name})-[r]-(neighbor)
    RETURN p, r, neighbor
    LIMIT 50
    """
    records = await run_cypher(cypher, {"name": packageName})

    return to_graph_data(records)


@router.get("/vulnerabilities/{vuln_id}")
async def get_vulnerability(vuln_id: str):
    """Fetch CVE/OSV detail and all affected packages."""
    if not vuln_id or len(vuln_id) > 100:
        raise HTTPException(status_code=400, detail="Invalid vulnerability ID")

    cypher = """
    MATCH (v:Vulnerability {id: $vuln_id})
    OPTIONAL MATCH (v)-[r:AFFECTS]->(p:Package)
    RETURN v, r, p
    LIMIT 200
    """
    records = await run_cypher(cypher, {"vuln_id": vuln_id})

    if not records:
        raise HTTPException(status_code=404, detail=f"Vulnerability {vuln_id} not found")

    graph = to_graph_data(records)
    vuln_props = next((node for node in graph["nodes"] if node.get("label") == "Vulnerability"), None)
    if vuln_props is None:
        raise HTTPException(status_code=404, detail=f"Vulnerability {vuln_id} not found")

    affected = [node for node in graph["nodes"] if node.get("label") == "Package"]

    return {
        "vulnerability": vuln_props,
        "affected_packages": affected,
        "graphData": graph,
    }
