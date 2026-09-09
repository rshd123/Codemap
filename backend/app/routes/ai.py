from fastapi import APIRouter, HTTPException
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
    nodes_map: dict[str, dict] = {}
    links: list[dict] = []

    for record in records:
        for key, value in record.items():
            if isinstance(value, dict):
                node_id = str(value.get("elementId", value.get("identity", id(value))))
                if node_id not in nodes_map:
                    labels = value.get("labels", value.get("elementId", ""))
                    props = value.get("properties", value)
                    node_label = labels[0] if isinstance(labels, list) and labels else str(labels)
                    nodes_map[node_id] = {
                        "id": node_id,
                        "label": node_label,
                        **props,
                    }
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        node_id = str(item.get("elementId", item.get("identity", id(item))))
                        if node_id not in nodes_map:
                            labels = item.get("labels", item.get("elementId", ""))
                            props = item.get("properties", item)
                            node_label = labels[0] if isinstance(labels, list) and labels else str(labels)
                            nodes_map[node_id] = {
                                "id": node_id,
                                "label": node_label,
                                **props,
                            }

    # Extract relationships from records
    for record in records:
        for key, value in record.items():
            if isinstance(value, dict) and "type" in value:
                src = str(value.get("startNodeElementId", value.get("start", "")))
                tgt = str(value.get("endNodeElementId", value.get("end", "")))
                links.append({
                    "source": src,
                    "target": tgt,
                    "type": value.get("type", "UNKNOWN"),
                })

    graph_data = {"nodes": list(nodes_map.values()), "links": links}

    # Step 4: Generate explanation
    explanation = await explain_evidence(req.prompt, cypher, graph_data)

    return SearchResponse(
        success=True,
        cypher=cypher,
        graphData=graph_data,
        explanation=explanation,
    )
