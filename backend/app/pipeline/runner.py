"""ETL orchestration: source selection, progress reporting and run summaries."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from app.pipeline import github_etl, nvd_etl, osv_etl
from app.pipeline.base import ApiError, accumulate, empty_counts, ensure_schema
from app.pipeline.dependency_graph import MANIFEST_PRIORITY, ingest_manifest, parse_manifest

logger = logging.getLogger("codemap.pipeline")

SOURCES: tuple[str, ...] = ("deps", "github", "osv", "nvd")

ProgressCallback = Callable[[dict], None]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve_sources(
    sources: Sequence[str] | None = None,
    *,
    repo: str | None = None,
    packages: Sequence[Any] | None = None,
    cve_ids: Sequence[str] | None = None,
    keywords: Sequence[str] | None = None,
    manifests: Sequence[dict] | None = None,
) -> list[str]:
    if sources:
        requested = [str(value).strip().lower() for value in sources if str(value).strip()]
        unknown = [value for value in requested if value not in SOURCES]
        if unknown:
            raise ValueError(f"Unknown ETL source(s): {', '.join(unknown)}")
        return [source for source in SOURCES if source in requested]

    derived: list[str] = []
    if manifests:
        derived.append("deps")
    if repo:
        derived.append("github")
    if packages:
        derived.append("osv")
    if cve_ids or keywords:
        derived.append("nvd")
    return [source for source in SOURCES if source in derived]


def normalize_packages(packages: Sequence[Any] | None, default_ecosystem: str | None = None) -> list[dict]:
    normalized: list[dict] = []
    for item in packages or []:
        if isinstance(item, str):
            name, _, rest = item.partition(":")
            ecosystem, _, version = rest.partition(":")
            normalized.append({
                "name": name.strip(),
                "ecosystem": (ecosystem.strip() or default_ecosystem or "npm"),
                "version": version.strip() or None,
            })
        elif isinstance(item, dict):
            normalized.append({
                "name": str(item.get("name") or "").strip(),
                "ecosystem": str(item.get("ecosystem") or default_ecosystem or "npm"),
                "version": item.get("version") or None,
            })
    return [entry for entry in normalized if entry["name"]]


async def run_etl(
    sources: Sequence[str] | None = None,
    *,
    repo: str | None = None,
    packages: Sequence[Any] | None = None,
    cve_ids: Sequence[str] | None = None,
    keywords: Sequence[str] | None = None,
    ecosystem: str | None = None,
    manifests: Sequence[dict] | None = None,
    max_items: int = 25,
    cross_ref: bool = True,
    max_commits: int = 20,
    max_issues: int = 10,
    max_timelines: int = 5,
    on_progress: ProgressCallback | None = None,
) -> dict:
    selected = resolve_sources(
        sources,
        repo=repo,
        packages=packages,
        cve_ids=cve_ids,
        keywords=keywords,
        manifests=manifests,
    )
    if not selected:
        raise ValueError("No ETL inputs given: provide a repo, packages, CVE ids, keywords or manifests")

    package_rows = normalize_packages(packages, ecosystem)
    explicit_cves = [str(value).strip().upper() for value in (cve_ids or []) if str(value).strip()]
    keyword_rows = [str(value).strip() for value in (keywords or []) if str(value).strip()]
    manifest_rows = [
        entry for entry in (manifests or [])
        if isinstance(entry, dict) and entry.get("filename") in MANIFEST_PRIORITY and entry.get("content")
    ]

    started_at = utc_now()
    start_clock = time.monotonic()
    jobs: list[dict] = []
    totals = empty_counts()
    requests = 0
    harvested_cves: list[str] = []

    logger.info("ETL run started: %s", ", ".join(selected))
    _emit(on_progress, {"event": "run_started", "sources": selected, "timestamp": started_at})

    try:
        schema_counts = await ensure_schema()
        accumulate(totals, schema_counts)
    except Exception as exc:
        logger.error("ETL aborted, Neo4j schema setup failed: %s", exc)
        failure = {
            "source": "schema",
            "status": "failed",
            "error": str(exc),
            "counts": empty_counts(),
            "durationSeconds": 0.0,
        }
        return {
            "success": False,
            "sources": selected,
            "startedAt": started_at,
            "finishedAt": utc_now(),
            "durationSeconds": round(time.monotonic() - start_clock, 2),
            "jobs": [failure],
            "totals": totals,
            "requests": 0,
        }

    for source in selected:
        job_start = time.monotonic()
        _emit(on_progress, {"event": "job_started", "source": source, "timestamp": utc_now()})
        logger.info("ETL job '%s' started", source)
        try:
            result = await _run_source(
                source,
                repo=repo,
                packages=package_rows,
                cve_ids=explicit_cves,
                keywords=keyword_rows,
                ecosystem=ecosystem,
                manifests=manifest_rows,
                max_items=max_items,
                cross_ref=cross_ref,
                max_commits=max_commits,
                max_issues=max_issues,
                max_timelines=max_timelines,
                harvested_cves=harvested_cves,
                on_progress=on_progress,
            )
        except (ApiError, ValueError) as exc:
            job = _failed_job(source, str(exc), job_start)
            jobs.append(job)
            _emit(on_progress, {"event": "job_finished", **job, "timestamp": utc_now()})
            logger.error("ETL job '%s' failed: %s", source, exc)
            continue
        except Exception as exc:
            job = _failed_job(source, f"{type(exc).__name__}: {exc}", job_start)
            jobs.append(job)
            _emit(on_progress, {"event": "job_finished", **job, "timestamp": utc_now()})
            logger.exception("ETL job '%s' failed unexpectedly", source)
            continue

        counts = result.get("counts") or empty_counts()
        accumulate(totals, counts)
        requests += int(result.get("requests") or 0)
        if source == "osv":
            harvested_cves.extend(result.get("cve_ids") or [])
        if source == "nvd" and result.get("cve_ids"):
            harvested_cves.extend(result["cve_ids"])

        job = {
            "source": source,
            "status": "completed",
            "error": None,
            "counts": counts,
            "details": {key: value for key, value in result.items() if key not in ("counts",)},
            "durationSeconds": round(time.monotonic() - job_start, 2),
        }
        jobs.append(job)
        _emit(on_progress, {"event": "job_finished", **job, "timestamp": utc_now()})
        logger.info("ETL job '%s' finished in %ss", source, job["durationSeconds"])

    summary = {
        "success": all(job["status"] == "completed" for job in jobs),
        "sources": selected,
        "startedAt": started_at,
        "finishedAt": utc_now(),
        "durationSeconds": round(time.monotonic() - start_clock, 2),
        "jobs": jobs,
        "totals": totals,
        "requests": requests,
    }
    logger.info(
        "ETL run finished: %s nodes, %s relationships, %s API requests",
        totals.get("nodes_created", 0),
        totals.get("relationships_created", 0),
        requests,
    )
    _emit(on_progress, {"event": "run_finished", "summary": summary, "timestamp": utc_now()})
    return summary


def _failed_job(source: str, error: str, job_start: float) -> dict:
    return {
        "source": source,
        "status": "failed",
        "error": error,
        "counts": empty_counts(),
        "details": {},
        "durationSeconds": round(time.monotonic() - job_start, 2),
    }


def _emit(callback: ProgressCallback | None, payload: dict) -> None:
    if callback is None:
        return
    try:
        callback(payload)
    except Exception:
        logger.warning("Progress callback failed", exc_info=True)


async def _run_source(
    source: str,
    *,
    repo: str | None,
    packages: list[dict],
    cve_ids: list[str],
    keywords: list[str],
    ecosystem: str | None,
    manifests: list[dict],
    max_items: int,
    cross_ref: bool,
    max_commits: int,
    max_issues: int,
    max_timelines: int,
    harvested_cves: list[str],
    on_progress: ProgressCallback | None,
) -> dict:
    if source == "deps":
        counts = empty_counts()
        parsed = 0
        for entry in manifests:
            filename = str(entry["filename"])
            manifest = parse_manifest(filename, str(entry["content"]))
            if manifest is None or not manifest.name:
                counts["errors"] += 1
                continue
            accumulate(counts, await ingest_manifest(manifest, source="manifest"))
            parsed += 1
            _emit(on_progress, {"event": "job_progress", "source": source,
                                "message": f"ingested {filename}", "timestamp": utc_now()})
        return {"counts": counts, "requests": 0, "manifests": parsed}

    if source == "github":
        if not repo:
            raise ValueError("The github source requires a 'repo' of the form owner/name")
        result = await github_etl.ingest(
            repo,
            max_commits=max_commits,
            max_issues=max_issues,
            max_timelines=max_timelines,
        )
        return result

    if source == "osv":
        counts = empty_counts()
        requests = 0
        harvested: list[str] = []
        vuln_ids: list[str] = []
        if cve_ids:
            id_result = await osv_etl.ingest_ids(cve_ids, max_items=max_items)
            accumulate(counts, id_result["counts"])
            requests += id_result["requests"]
            harvested.extend(id_result["cve_ids"])
            vuln_ids.extend(id_result["vuln_ids"])
        if packages:
            package_result = await osv_etl.ingest_packages(packages, max_items=max_items)
            accumulate(counts, package_result["counts"])
            requests += package_result["requests"]
            harvested.extend(package_result["cve_ids"])
            vuln_ids.extend(package_result["vuln_ids"])
        if not cve_ids and not packages:
            raise ValueError("The osv source requires packages or vulnerability ids")
        return {
            "counts": counts,
            "requests": requests,
            "cve_ids": sorted(set(harvested)),
            "vuln_ids": sorted(set(vuln_ids)),
        }

    if source == "nvd":
        target_cves = list(dict.fromkeys([*cve_ids, *harvested_cves]))
        if not target_cves and not keywords:
            raise ValueError("The nvd source requires CVE ids or keywords")
        return await nvd_etl.ingest(
            cve_ids=target_cves,
            keywords=keywords,
            ecosystem=ecosystem,
            max_items=max_items,
            cross_ref=cross_ref,
        )

    raise ValueError(f"Unknown ETL source: {source}")
