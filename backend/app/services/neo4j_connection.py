from neo4j import AsyncGraphDatabase, AsyncDriver
from app.config import settings

_driver: AsyncDriver | None = None


async def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def close_driver():
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


async def run_cypher(query: str, params: dict | None = None) -> list[dict]:
    """Run a read-only Cypher query and return records as dicts."""
    driver = await get_driver()
    async with driver.session(database="neo4j") as session:
        result = await session.run(query, params or {})
        records = [dict(record) async for record in result]
        return records


def is_read_only(cypher: str) -> bool:
    """Basic check that a Cypher query only contains read operations."""
    forbidden = [
        "CREATE", "MERGE", "SET ", "DELETE", "REMOVE",
        "DROP", "ALTER", "DETACH", "INSERT", "UPDATE",
    ]
    upper = cypher.upper()
    for keyword in forbidden:
        if keyword in upper:
            return False
    return True
