from langchain_groq import ChatGroq
from app.config import settings

EXPLAIN_PROMPT = """You are a software engineering security analyst.
A user asked: "{prompt}"

The following Cypher query was generated and executed against a software dependency graph:

```cypher
{cypher}
```

The query returned this sub-graph data (JSON):
{graph_data_json}

Provide a clear, step-by-step plain English explanation of:
1. What the query is looking for
2. What relationships exist in the returned data
3. Any security-relevant findings (vulnerabilities, affected packages, fix status)
4. Actionable recommendations if applicable

Keep the explanation concise but thorough. Use bullet points where helpful.
"""


async def explain_evidence(prompt: str, cypher: str, graph_data: dict) -> str:
    """Use an LLM to explain the sub-graph evidence in plain English."""
    import json

    llm = ChatGroq(
        model=settings.llm_model,
        api_key=settings.llm_api_key or None,
        temperature=0,
    )

    graph_data_json = json.dumps(graph_data, indent=2, default=str)

    formatted = EXPLAIN_PROMPT.format(
        prompt=prompt,
        cypher=cypher,
        graph_data_json=graph_data_json,
    )

    response = await llm.ainvoke(formatted)
    return response.content
