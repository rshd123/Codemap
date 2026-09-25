"""Read-only graph traversal endpoints."""

from fastapi import APIRouter, Query

from app.pipeline.dependency_graph import direct_dependencies, transitive_dependencies

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/dependencies")
async def dependencies(
    name: str = Query(..., min_length=1, max_length=200, description="Package name"),
    ecosystem: str | None = Query(None, max_length=50, description="npm, pypi, maven, cargo, ..."),
    depth: int = Query(4, ge=1, le=8, description="Max DEPENDS_ON hops"),
    limit: int = Query(300, ge=1, le=1000, description="Max rows returned"),
    direct: bool = Query(False, description="Return only direct dependencies"),
):
    """Walk the DEPENDS_ON graph for a package and return { nodes, links }."""
    if direct:
        return await direct_dependencies(name, ecosystem, limit)
    return await transitive_dependencies(name, ecosystem, depth, limit)
