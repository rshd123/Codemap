from pydantic import BaseModel


class CypherRequest(BaseModel):
    prompt: str


class CypherResponse(BaseModel):
    cypher: str
    params: dict[str, str] = {}


class ExplainRequest(BaseModel):
    prompt: str
    cypher: str
    graphData: dict


class ExplainResponse(BaseModel):
    explanation: str


class SearchRequest(BaseModel):
    prompt: str


class SearchResponse(BaseModel):
    success: bool
    cypher: str
    graphData: dict
    explanation: str
