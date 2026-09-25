"""Shared ETL primitives: schema setup, parameterized writes, HTTP clients, progress stats."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.config import settings
from app.services.neo4j_connection import run_cypher, run_write

logger = logging.getLogger("codemap.pipeline")

CONSTRAINTS: tuple[str, ...] = (
    "CREATE CONSTRAINT vulnerability_id IF NOT EXISTS FOR (v:Vulnerability) REQUIRE v.id IS UNIQUE",
    "CREATE CONSTRAINT issue_id IF NOT EXISTS FOR (i:Issue) REQUIRE i.id IS UNIQUE",
    "CREATE CONSTRAINT commit_hash IF NOT EXISTS FOR (c:Commit) REQUIRE c.hash IS UNIQUE",
)

COUNTER_FIELDS: tuple[str, ...] = (
    "nodes_created",
    "nodes_deleted",
    "relationships_created",
    "relationships_deleted",
    "properties_set",
    "labels_added",
    "labels_removed",
    "indexes_added",
    "constraints_added",
)


class ApiError(RuntimeError):
    """Raised when a source API cannot be queried successfully."""


class RateLimitExceeded(ApiError):
    """Raised when a source API would need to sleep longer than the allowed budget."""


def empty_counts(items: int = 0, errors: int = 0) -> dict[str, int]:
    counts = {field: 0 for field in COUNTER_FIELDS}
    counts["items"] = items
    counts["errors"] = errors
    return counts


def counters_to_counts(counters: Any, items: int = 0, errors: int = 0) -> dict[str, int]:
    counts = empty_counts(items=items, errors=errors)
    if counters is None:
        return counts
    for field in COUNTER_FIELDS:
        try:
            counts[field] = int(getattr(counters, field, 0) or 0)
        except (TypeError, ValueError):
            counts[field] = 0
    return counts


def accumulate(total: dict[str, int], partial: dict[str, int] | None) -> dict[str, int]:
    for key, value in (partial or {}).items():
        total[key] = total.get(key, 0) + int(value)
    return total


async def ensure_schema() -> dict[str, int]:
    totals = empty_counts()
    for statement in CONSTRAINTS:
        _, counters = await run_write(statement)
        accumulate(totals, counters_to_counts(counters))
    logger.info("Schema constraints verified")
    return totals


async def write(query: str, params: dict | None = None) -> dict[str, int]:
    _, counters = await run_write(query, params)
    return counters_to_counts(counters)


async def write_rows(query: str, rows: list[dict]) -> dict[str, int]:
    if not rows:
        return empty_counts()
    counts = await write("UNWIND $rows AS row\n" + query, {"rows": rows})
    counts["items"] = len(rows)
    return counts


async def read(query: str, params: dict | None = None) -> list[dict]:
    return await run_cypher(query, params)


class RateLimiter:
    def __init__(self, min_interval: float = 0.0):
        self.min_interval = max(0.0, min_interval)
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def wait(self) -> None:
        if self.min_interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            delay = self._last_call + self.min_interval - now
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_call = time.monotonic()


class ApiClient:
    """Thin async JSON client with throttling, retries and rate-limit handling."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        min_interval: float = 0.0,
        timeout: float = 30.0,
        max_retries: int = 3,
        max_wait: float = 90.0,
        name: str = "api",
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_wait = max_wait
        self.name = name
        self.limiter = RateLimiter(min_interval)
        self.request_count = 0
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ApiClient":
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _retry_delay(self, response: httpx.Response | None, attempt: int) -> float:
        if response is not None:
            retry_after = response.headers.get("retry-after")
            if retry_after:
                try:
                    return min(float(retry_after), self.max_wait)
                except ValueError:
                    pass
            if response.headers.get("x-ratelimit-remaining") == "0":
                reset = response.headers.get("x-ratelimit-reset")
                if reset:
                    try:
                        return min(max(float(reset) - time.time(), 1.0), self.max_wait)
                    except ValueError:
                        pass
        return min(2.0 ** attempt, self.max_wait)

    async def request(self, method: str, path: str, params: dict | None = None, json: Any = None) -> Any:
        if self._client is None:
            raise ApiError(f"{self.name} client is not open")

        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            await self.limiter.wait()
            try:
                response = await self._client.request(method, path, params=params, json=json)
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning("%s request to %s failed (%s/%s)", self.name, path, attempt + 1, self.max_retries)
                if attempt < self.max_retries:
                    await asyncio.sleep(min(2.0 ** attempt, 10.0))
                    continue
                break

            self.request_count += 1

            if response.status_code == 404:
                return None

            if response.status_code in (403, 429):
                delay = self._retry_delay(response, attempt)
                logger.warning("%s rate limited on %s, waiting %.1fs", self.name, path, delay)
                if delay > self.max_wait or attempt >= self.max_retries:
                    raise RateLimitExceeded(f"{self.name} rate limit exceeded on {path}")
                await asyncio.sleep(delay)
                continue

            if response.status_code >= 500:
                last_error = f"HTTP {response.status_code}"
                logger.warning("%s server error %s on %s", self.name, response.status_code, path)
                if attempt < self.max_retries:
                    await asyncio.sleep(min(2.0 ** attempt, 10.0))
                    continue
                break

            if response.status_code >= 400:
                raise ApiError(f"{self.name} HTTP {response.status_code} on {path}: {response.text[:200]}")

            try:
                return response.json()
            except ValueError:
                raise ApiError(f"{self.name} returned non-JSON response on {path}")

        raise ApiError(f"{self.name} request to {path} failed: {last_error or 'unknown error'}")

    async def get(self, path: str, params: dict | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, json: Any = None) -> Any:
        return await self.request("POST", path, json=json)


def github_client() -> ApiClient:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "codemap-etl",
    }
    token = settings.github_token.strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return ApiClient(
        settings.github_api_url,
        headers=headers,
        min_interval=0.2 if token else 1.2,
        timeout=30.0,
        max_wait=60.0,
        name="github",
    )


def osv_client() -> ApiClient:
    return ApiClient(
        settings.osv_api_url,
        headers={"User-Agent": "codemap-etl"},
        min_interval=0.1,
        timeout=30.0,
        name="osv",
    )


def nvd_client() -> ApiClient:
    headers = {"User-Agent": "codemap-etl"}
    api_key = settings.nvd_api_key.strip()
    if api_key:
        headers["apiKey"] = api_key
    return ApiClient(
        settings.nvd_api_url,
        headers=headers,
        min_interval=6.0 if not api_key else 0.7,
        timeout=60.0,
        max_retries=4,
        max_wait=70.0,
        name="nvd",
    )
