"""OSV.dev ingestion: advisory nodes plus AFFECTS edges to affected packages."""

from __future__ import annotations

import logging
import re
from typing import Any, Sequence

from app.pipeline.base import ApiError, accumulate, empty_counts, osv_client, write_rows
from app.pipeline.dependency_graph import ecosystem_from_osv, normalize_name, osv_ecosystem
from app.pipeline.queries import AFFECTS_UPSERT, VULN_UPSERT

logger = logging.getLogger("codemap.pipeline")

CVE_PATTERN = re.compile(r"\bCVE-\d{4}-\d{4,7}\b")
MAX_SUMMARY = 400
MAX_LIST = 20


def canonical_id(vuln: dict) -> tuple[str, str | None]:
    """Prefer the CVE alias as the stable node id so OSV and NVD land on one node."""
    identifier = str(vuln.get("id") or "").strip()
    aliases = [str(alias) for alias in vuln.get("aliases") or []]
    cve_id = identifier if CVE_PATTERN.fullmatch(identifier) else None
    if cve_id is None:
        cve_id = next((alias for alias in aliases if CVE_PATTERN.fullmatch(alias)), None)
    return (cve_id or identifier), cve_id


def _summary(vuln: dict) -> str | None:
    summary = str(vuln.get("summary") or "").strip()
    if summary:
        return summary[:MAX_SUMMARY]
    details = str(vuln.get("details") or "").strip()
    if not details:
        return None
    return details[:MAX_SUMMARY]


def _cvss(vuln: dict) -> tuple[float | None, str | None, str | None]:
    cvss_value: float | None = None
    vector: str | None = None
    for entry in vuln.get("severity") or []:
        if not isinstance(entry, dict):
            continue
        score = entry.get("score")
        if isinstance(score, (int, float)):
            cvss_value = float(score)
        elif isinstance(score, str) and score.startswith("CVSS"):
            vector = score
    database = vuln.get("database_specific") or {}
    ecosystem = vuln.get("ecosystem_specific") or {}
    severity = database.get("severity") or ecosystem.get("severity")
    return cvss_value, vector, str(severity).upper() if severity else None


def _cwe(vuln: dict) -> list[str]:
    database = vuln.get("database_specific") or {}
    values = database.get("cwe_ids") or []
    return [str(value) for value in values if value][:MAX_LIST]


def _reference_urls(vuln: dict) -> list[str]:
    urls = []
    for reference in vuln.get("references") or []:
        url = reference.get("url") if isinstance(reference, dict) else reference
        if isinstance(url, str) and url.startswith("http"):
            urls.append(url)
        if len(urls) >= MAX_LIST:
            break
    return urls


def vuln_row(vuln: dict, source: str = "osv") -> dict | None:
    node_id, cve_id = canonical_id(vuln)
    if not node_id:
        return None
    cvss, vector, severity = _cvss(vuln)
    return {
        "id": node_id,
        "source": source,
        "summary": _summary(vuln),
        "cvss": cvss,
        "cvss_vector": vector,
        "severity": severity,
        "published": vuln.get("published"),
        "modified": vuln.get("modified"),
        "aliases": [str(alias) for alias in vuln.get("aliases") or []][:MAX_LIST] or None,
        "reference_urls": _reference_urls(vuln) or None,
        "cwe": _cwe(vuln) or None,
        "osv_id": str(vuln.get("id")) if vuln.get("id") else None,
        "cve_id": cve_id,
        "url": f"https://osv.dev/vulnerability/{vuln['id']}" if vuln.get("id") else None,
    }


def _range_info(affected: dict) -> tuple[list[str] | None, str | None]:
    fixed: list[str] = []
    parts: list[str] = []
    for entry in affected.get("ranges") or []:
        introduced = ""
        last_fixed = ""
        for event in entry.get("events") or []:
            if "introduced" in event:
                introduced = str(event["introduced"])
            if "fixed" in event:
                last_fixed = str(event["fixed"])
                fixed.append(last_fixed)
        if introduced or last_fixed:
            parts.append(f"{entry.get('type', 'RANGE')}:{introduced}..{last_fixed or 'latest'}")
    versions = [str(value) for value in affected.get("versions") or []][:MAX_LIST]
    if not parts and versions:
        parts.append("VERSIONS:" + ",".join(versions[:5]))
    return (fixed or None), "; ".join(parts)[:300] or None


def affect_rows(vuln: dict, source: str = "osv") -> list[dict]:
    node_id, _ = canonical_id(vuln)
    if not node_id:
        return []
    rows: list[dict] = []
    for affected in vuln.get("affected") or []:
        package = affected.get("package") or {}
        raw_name = str(package.get("name") or "").strip()
        raw_ecosystem = str(package.get("ecosystem") or "").strip()
        if not raw_name:
            continue
        ecosystem = ecosystem_from_osv(raw_ecosystem) if raw_ecosystem else "other"
        fixed, version_range = _range_info(affected)
        rows.append({
            "vuln_id": node_id,
            "name": normalize_name(ecosystem, raw_name),
            "ecosystem": ecosystem,
            "version": None,
            "source": source,
            "versions": [str(value) for value in (affected.get("versions") or [])][:50] or None,
            "fixed_versions": fixed,
            "version_range": version_range,
        })
    return rows


async def _persist(vulns: Sequence[dict]) -> tuple[dict, set[str], set[str]]:
    counts = empty_counts()
    seen: set[str] = set()
    node_rows: list[dict] = []
    edge_rows: list[dict] = []
    harvested: set[str] = set()
    node_ids: set[str] = set()

    for vuln in vulns:
        if not isinstance(vuln, dict):
            counts["errors"] += 1
            continue
        node_id, cve_id = canonical_id(vuln)
        if not node_id or node_id in seen:
            continue
        seen.add(node_id)
        row = vuln_row(vuln)
        if row is None:
            counts["errors"] += 1
            continue
        node_rows.append(row)
        edge_rows.extend(affect_rows(vuln))
        node_ids.add(node_id)
        if cve_id:
            harvested.add(cve_id)

    if node_rows:
        accumulate(counts, await write_rows(VULN_UPSERT, node_rows))
    if edge_rows:
        accumulate(counts, await write_rows(AFFECTS_UPSERT, edge_rows))
    counts["items"] = len(node_ids)
    return counts, harvested, node_ids


async def ingest_packages(packages: Sequence[dict], max_items: int = 25) -> dict:
    counts = empty_counts()
    harvested: set[str] = set()
    node_ids: set[str] = set()
    target_packages = [pkg for pkg in packages if pkg.get("name")][:max_items]
    if not target_packages:
        logger.info("OSV: nothing to ingest (no packages given)")
        return {"counts": counts, "cve_ids": [], "vuln_ids": [], "requests": 0}

    async with osv_client() as client:
        for index, package in enumerate(target_packages, start=1):
            raw_ecosystem = str(package.get("ecosystem") or "npm")
            body: dict[str, Any] = {
                "package": {
                    "name": package["name"],
                    "ecosystem": osv_ecosystem(raw_ecosystem),
                }
            }
            if package.get("version"):
                body["version"] = package["version"]
            try:
                data = await client.post("/v1/query", json=body)
            except ApiError as exc:
                counts["errors"] += 1
                logger.warning("OSV query failed for %s: %s", package["name"], exc)
                continue

            vulns = (data or {}).get("vulns") or []
            logger.info("OSV: %s/%s %s -> %s advisories", index, len(target_packages), package["name"], len(vulns))
            batch_counts, batch_harvested, batch_nodes = await _persist(vulns[:max_items])
            accumulate(counts, batch_counts)
            harvested.update(batch_harvested)
            node_ids.update(batch_nodes)

        requests = client.request_count

    return {
        "counts": counts,
        "cve_ids": sorted(harvested),
        "vuln_ids": sorted(node_ids),
        "requests": requests,
    }


async def ingest_ids(vuln_ids: Sequence[str], max_items: int = 25) -> dict:
    counts = empty_counts()
    harvested: set[str] = set()
    node_ids: set[str] = set()
    targets = [str(value).strip() for value in vuln_ids if str(value).strip()][:max_items]
    if not targets:
        logger.info("OSV: nothing to ingest (no vulnerability ids given)")
        return {"counts": counts, "cve_ids": [], "vuln_ids": [], "requests": 0}

    collected: list[dict] = []
    async with osv_client() as client:
        for index, vuln_id in enumerate(targets, start=1):
            try:
                data = await client.get(f"/v1/vulns/{vuln_id}")
            except ApiError as exc:
                counts["errors"] += 1
                logger.warning("OSV lookup failed for %s: %s", vuln_id, exc)
                continue
            if not data:
                logger.warning("OSV: %s not found", vuln_id)
                counts["errors"] += 1
                continue
            logger.info("OSV: %s/%s %s", index, len(targets), vuln_id)
            collected.append(data)

        requests = client.request_count

    batch_counts, harvested, node_ids = await _persist(collected)
    accumulate(counts, batch_counts)
    return {"counts": counts, "cve_ids": sorted(harvested), "vuln_ids": sorted(node_ids), "requests": requests}


async def fetch(vuln_id: str) -> dict | None:
    """Fetch a single advisory, used by other sources for cross-referencing."""
    try:
        async with osv_client() as client:
            data = await client.get(f"/v1/vulns/{vuln_id}")
    except ApiError as exc:
        logger.warning("OSV lookup failed for %s: %s", vuln_id, exc)
        return None
    return data if isinstance(data, dict) else None
