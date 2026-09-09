from fastapi import APIRouter
from app.services.neo4j_connection import get_driver

router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        driver = await get_driver()
        async with driver.session() as session:
            await session.run("RETURN 1")
        return {"status": "ok", "neo4j": "connected"}
    except Exception as e:
        return {"status": "degraded", "neo4j": str(e)}
