"""NVD CVE ingestion with OSV cross-referencing."""

from __future__ import annotations

import logging
from typing import Sequence

from app.pipeline import osv_etl
from app.pipeline.base import ApiError, accumulate, empty_counts, nvd_client, osv_client, write_rows
from app.pipeline.dependency_graph import normalize_name, packages_from_cpe
from app.pipeline.queries import AFFECTS_UPSERT, VULN_UPSERT

logger = logging.getLogger("codemap.pipeline")

MAX_LIST = 20
CVSS_PRIORITY = ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2")


def extract_cvss(metrics: dict | None) -> tuple[float | None, str | None, str | None]:
    for key in CVSS_PRIORITY:
        entries = (metrics or {}).get(key) or []
        if not entries:
            continue
        entry = next((item for item in entries if item.get("type") == "Primary"), entries[0])
        data = entry.get("cvssData") or {}
        score = data.get("baseScore")
        severity = data.get("baseSeverity") or entry.get("baseSeverity")
        vector = data.get("vectorString")
        return (
            float(score) if isinstance(score, (int, float)) else None,
            str(severity).upper() if severity else None,
            vector,
        )
    return None, None, None


def _description(cve: dict) -> str | None:
    for entry in cve.get("descriptions") or []:
        if entry.get("lang") == "en" and entry.get("value"):
            return str(entry["value"]).strip()
    descriptions = cve.get("descriptions") or []
    if descriptions:
        return str(descriptions[0].get("value") or "").strip() or None
    return None


def _cwe(cve: dict) -> list[str]:
    values: list[str] = []
    for weakness in cve.get("weaknesses") or []:
        for entry in weakness.get("description") or []:
            value = entry.get("value")
            if isinstance(value, str) and value.startswith("CWE-") and value not in values:
                values.append(value)
    return values[:MAX_LIST]


def _reference_urls(cve: dict) -> list[str]:
    urls: list[str] = []
    for reference in cve.get("references") or []:
        url = reference.get("url")
        if isinstance(url, str) and url.startswith("http") and url not in urls:
            urls.append(url)
        if len(urls) >= MAX_LIST:
            break
    return urls


def vuln_row(cve: dict, osv_data: dict | None = None) -> dict | None:
    cve_id = str(cve.get("id") or "").strip()
    if not cve_id:
        return None
    cvss, severity, vector = extract_cvss(cve.get("metrics"))
    row = {
        "id": cve_id,
        "source": "nvd",
        "summary": _description(cve),
        "cvss": cvss,
        "cvss_vector": vector,
        "severity": severity,
        "published": cve.get("published"),
        "modified": cve.get("lastModified"),
        "aliases": None,
        "reference_urls": _reference_urls(cve) or None,
        "cwe": _cwe(cve) or None,
        "osv_id": None,
        "cve_id": cve_id,
        "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
    }
    if osv_data:
        enriched = osv_etl.vuln_row(osv_data, source="osv")
        if enriched:
            row["aliases"] = enriched["aliases"]
            row["osv_id"] = enriched["osv_id"]
            if not row["reference_urls"]:
                row["reference_urls"] = enriched["reference_urls"]
            if not row["cwe"]:
                row["cwe"] = enriched["cwe"]
    return row


def _cpe_range(match: dict) -> str | None:
    parts = []
    start_incl = match.get("versionStartIncluding")
    start_excl = match.get("versionStartExcluding")
    end_incl = match.get("versionEndIncluding")
    end_excl = match.get("versionEndExcluding")
    if start_incl:
        parts.append(f">={start_incl}")
    if start_excl:
        parts.append(f">{start_excl}")
    if end_incl:
        parts.append(f"<={end_incl}")
    if end_excl:
        parts.append(f"<{end_excl}")
    return " ".join(parts) if parts else None


def affect_rows(cve: dict, vuln_id: str, fallback_ecosystem: str | None = None, source: str = "nvd") -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def _add(name: str, ecosystem: str, version_range: str | None) -> None:
        cleaned = normalize_name(ecosystem, str(name).strip())
        if not cleaned:
            return
        key = (cleaned, ecosystem)
        if key in seen:
            return
        seen.add(key)
        rows.append({
            "vuln_id": vuln_id,
            "name": cleaned,
            "ecosystem": ecosystem,
            "version": None,
            "source": source,
            "versions": None,
            "fixed_versions": None,
            "version_range": version_range,
        })

    ecosystem = fallback_ecosystem
    cpe_packages: list[tuple[str, str, str | None]] = []
    for configuration in cve.get("configurations") or []:
        for node in configuration.get("nodes") or []:
            for match in node.get("cpeMatch") or []:
                if match.get("vulnerable") is False:
                    continue
                parsed = packages_from_cpe(match.get("criteria") or "", fallback_ecosystem)
                if not parsed:
                    continue
                derived_ecosystem, name = parsed
                if ecosystem is None and derived_ecosystem != "other":
                    ecosystem = derived_ecosystem
                cpe_packages.append((name, derived_ecosystem, _cpe_range(match)))

    for name, derived_ecosystem, version_range in cpe_packages:
        _add(name, ecosystem or derived_ecosystem, version_range)

    for block in cve.get("affected") or []:
        for entry in block.get("affectedData") or []:
            product = entry.get("product")
            if not product:
                continue
            _add(product, ecosystem or "other", None)

    return rows


async def ingest(
    cve_ids: Sequence[str] | None = None,
    keywords: Sequence[str] | None = None,
    ecosystem: str | None = None,
    max_items: int = 25,
    cross_ref: bool = True,
) -> dict:
    counts = empty_counts()
    collected: list[dict] = []
    seen_ids: set[str] = set()
    requests = 0
    cross_refs = 0

    explicit_ids = [str(value).strip() for value in (cve_ids or []) if str(value).strip()]
    target_keywords = [str(value).strip() for value in (keywords or []) if str(value).strip()][:3]

    if not explicit_ids and not target_keywords:
        logger.info("NVD: nothing to ingest (no CVE ids or keywords given)")
        return {"counts": counts, "cve_ids": [], "requests": 0, "osv_cross_refs": 0}

    async with nvd_client() as client:
        for keyword in target_keywords:
            if len(collected) >= max_items:
                break
            page_size = min(max_items, 50)
            try:
                data = await client.get("", params={"keywordSearch": keyword, "resultsPerPage": page_size})
            except ApiError as exc:
                counts["errors"] += 1
                logger.warning("NVD keyword search failed for %s: %s", keyword, exc)
                continue
            results = (data or {}).get("vulnerabilities") or []
            logger.info("NVD: keyword '%s' matched %s results", keyword, (data or {}).get("totalResults", 0))
            for entry in results:
                cve = entry.get("cve") if isinstance(entry, dict) else None
                if not cve or not cve.get("id") or cve["id"] in seen_ids:
                    continue
                seen_ids.add(cve["id"])
                collected.append(cve)
                if len(collected) >= max_items:
                    break

        for cve_id in explicit_ids:
            if len(collected) >= max_items:
                break
            if cve_id in seen_ids:
                continue
            try:
                data = await client.get("", params={"cveId": cve_id, "resultsPerPage": 1})
            except ApiError as exc:
                counts["errors"] += 1
                logger.warning("NVD lookup failed for %s: %s", cve_id, exc)
                continue
            results = (data or {}).get("vulnerabilities") or []
            if not results:
                logger.warning("NVD: %s not found", cve_id)
                counts["errors"] += 1
                continue
            cve = results[0].get("cve")
            if cve:
                seen_ids.add(cve.get("id", cve_id))
                collected.append(cve)

        requests = client.request_count

    if not collected:
        return {"counts": counts, "cve_ids": [], "requests": requests, "osv_cross_refs": 0}

    osv_rows: list[dict] = []
    nvd_rows: list[dict] = []
    edge_rows: list[dict] = []
    osv_by_id: dict[str, dict] = {}

    if cross_ref:
        async with osv_client() as client:
            for index, cve in enumerate(collected, start=1):
                cve_id = str(cve.get("id") or "")
                try:
                    osv_data = await client.get(f"/v1/vulns/{cve_id}")
                except ApiError as exc:
                    logger.warning("OSV cross-reference failed for %s: %s", cve_id, exc)
                    osv_data = None
                if not isinstance(osv_data, dict):
                    continue
                cross_refs += 1
                osv_by_id[cve_id] = osv_data
                logger.info("NVD: %s/%s cross-referenced %s with OSV", index, len(collected), cve_id)
                row = osv_etl.vuln_row(osv_data, source="osv")
                if row:
                    row["id"] = cve_id
                    row["cve_id"] = cve_id
                    osv_rows.append(row)
                for affected in osv_etl.affect_rows(osv_data, source="osv"):
                    affected["vuln_id"] = cve_id
                    edge_rows.append(affected)
            requests += client.request_count

    for cve in collected:
        cve_id = str(cve.get("id") or "")
        row = vuln_row(cve, osv_by_id.get(cve_id))
        if row:
            nvd_rows.append(row)
        edge_rows.extend(affect_rows(cve, cve_id, fallback_ecosystem=ecosystem))

    if osv_rows:
        accumulate(counts, await write_rows(VULN_UPSERT, osv_rows))
    if nvd_rows:
        accumulate(counts, await write_rows(VULN_UPSERT, nvd_rows))
    if edge_rows:
        accumulate(counts, await write_rows(AFFECTS_UPSERT, edge_rows))

    counts["items"] = len(collected)
    return {
        "counts": counts,
        "cve_ids": sorted(seen_ids),
        "requests": requests,
        "osv_cross_refs": cross_refs,
    }
