from langchain_community.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from langchain_groq import ChatGroq
from app.config import settings
from app.services.neo4j_connection import is_read_only


def _get_graph() -> Neo4jGraph:
    return Neo4jGraph(
        url=settings.neo4j_uri,
        username=settings.neo4j_user,
        password=settings.neo4j_password,
    )


def _get_llm() -> ChatGroq:
    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.llm_api_key or None,
        temperature=0,
    )


GRAPH_SCHEMA = """
Nodes:
  - Package {name, version, ecosystem}
  - Vulnerability {id, cvss, summary, source}
  - Issue {id, title, status, url}
  - Commit {hash, message, timestamp, author}

Relationships:
  - (Package)-[:DEPENDS_ON]->(Package)
  - (Vulnerability)-[:AFFECTS]->(Package)
  - (Commit)-[:FIXES]->(Issue)
  - (Commit)-[:PATCHES]->(Vulnerability)
  - (Issue)-[:REFERENCES]->(Vulnerability)
"""


async def generate_cypher(prompt: str) -> dict:
    """Translate a natural language prompt into a read-only Cypher query."""
    graph = _get_graph()
    llm = _get_llm()

    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
        allow_dangerous_requests=False,
        top_k=100,
    )

    result = await chain.ainvoke({"query": prompt})
    cypher = result.get("cypher", "")

    if not cypher:
        return {"cypher": "", "params": {}, "error": "Could not generate Cypher"}

    if not is_read_only(cypher):
        return {"cypher": "", "params": {}, "error": "Generated query is not read-only"}

    return {"cypher": cypher, "params": result.get("params", {})}
