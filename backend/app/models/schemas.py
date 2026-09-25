import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

EtlSource = Literal["deps", "github", "osv", "nvd"]
ManifestFilename = Literal["package.json", "pyproject.toml", "requirements.txt", "pom.xml", "Cargo.toml"]
VULN_ID = r"CVE-\d{4}-\d{4,7}|GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}"
VulnIdPattern = rf"^({VULN_ID})$"
RepoPattern = r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"


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


class EtlPackage(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Package name as published in its registry")
    ecosystem: str = Field(default="npm", max_length=50, description="npm, pypi, maven, cargo, ...")
    version: str | None = Field(default=None, max_length=100)


class EtlManifest(BaseModel):
    filename: ManifestFilename = Field(..., description="Manifest file name, e.g. package.json")
    content: str = Field(..., min_length=1, max_length=500_000, description="Raw manifest text")


class EtlRunRequest(BaseModel):
    sources: list[EtlSource] = Field(default_factory=list, description="Empty derives sources from the inputs")
    repo: str | None = Field(default=None, max_length=200, pattern=RepoPattern, description="owner/name")
    packages: list[EtlPackage] = Field(default_factory=list, max_length=50)
    cve_ids: list[str] = Field(default_factory=list, max_length=100)
    keywords: list[str] = Field(default_factory=list, max_length=5)
    ecosystem: str | None = Field(default=None, max_length=50)
    manifests: list[EtlManifest] = Field(default_factory=list, max_length=5)
    max_items: int = Field(default=25, ge=1, le=200, description="Per source cap for CVEs, advisories and packages")
    cross_ref: bool = Field(default=True, description="Cross-reference NVD data with OSV.dev")
    max_commits: int = Field(default=20, ge=0, le=100)
    max_issues: int = Field(default=10, ge=0, le=100)
    max_timelines: int = Field(default=5, ge=0, le=50)

    @field_validator("cve_ids")
    @classmethod
    def _validate_cve_ids(cls, values: list[str]) -> list[str]:
        cleaned = []
        for value in values:
            candidate = value.strip().upper()
            if not re.fullmatch(VULN_ID, candidate):
                raise ValueError(f"Invalid vulnerability id '{value}' (expected CVE-YYYY-NNNNN or GHSA-xxxx-xxxx-xxxx)")
            cleaned.append(candidate)
        return cleaned


class EtlJobResponse(BaseModel):
    jobId: str
    status: str
    sources: list[str]


class EtlStatusResponse(BaseModel):
    jobId: str | None = None
    status: str = "idle"
    sources: list[str] = []
    startedAt: str | None = None
    finishedAt: str | None = None
    progress: dict | None = None
    logs: list[str] = []
    error: str | None = None
    summary: dict | None = None
    history: list[dict] = []
