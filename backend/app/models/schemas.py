from pydantic import BaseModel, Field


class CypherRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="Natural language query")


class CypherResponse(BaseModel):
    cypher: str
    params: dict[str, str] = {}


class ExplainRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    cypher: str = Field(..., min_length=1, max_length=5000)
    graphData: dict


class ExplainResponse(BaseModel):
    explanation: str


class SearchRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="Natural language query")


class SearchResponse(BaseModel):
    success: bool
    cypher: str
    graphData: dict
    explanation: str
