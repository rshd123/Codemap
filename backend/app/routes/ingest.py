"""ETL control endpoints: start ingestion runs and report their progress."""

from __future__ import annotations

import logging
import uuid
from collections import deque
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.schemas import EtlJobResponse, EtlRunRequest, EtlStatusResponse
from app.pipeline.runner import resolve_sources, run_etl, utc_now

logger = logging.getLogger("codemap.etl")

router = APIRouter(prefix="/etl", tags=["etl"])

_MAX_LOG_LINES = 200
_MAX_HISTORY = 10

_state: dict[str, Any] = {
    "jobId": None,
    "status": "idle",
    "sources": [],
    "startedAt": None,
    "finishedAt": None,
    "progress": None,
    "logs": [],
    "error": None,
    "summary": None,
}
_history: deque[dict[str, Any]] = deque(maxlen=_MAX_HISTORY)
_running = False


def _log(line: str) -> None:
    _state["logs"].append(line)
    overflow = len(_state["logs"]) - _MAX_LOG_LINES
    if overflow > 0:
        del _state["logs"][:overflow]


def _snapshot() -> dict[str, Any]:
    return {
        "jobId": _state["jobId"],
        "status": _state["status"],
        "sources": list(_state["sources"]),
        "startedAt": _state["startedAt"],
        "finishedAt": _state["finishedAt"],
        "error": _state["error"],
        "summary": _state["summary"],
    }


def _on_progress(payload: dict[str, Any]) -> None:
    event = payload.get("event")
    timestamp = payload.get("timestamp") or utc_now()
    if event == "job_started":
        _state["progress"] = {"source": payload.get("source"), "status": "running"}
        _log(f"[{timestamp}] job '{payload.get('source')}' started")
    elif event == "job_progress":
        _log(f"[{timestamp}] {payload.get('source')}: {payload.get('message')}")
    elif event == "job_finished":
        counts = payload.get("counts") or {}
        _state["progress"] = {"source": payload.get("source"), "status": payload.get("status")}
        _log(
            f"[{timestamp}] job '{payload.get('source')}' {payload.get('status')} "
            f"(+{counts.get('nodes_created', 0)} nodes, +{counts.get('relationships_created', 0)} relationships)"
        )


@router.post("/run", response_model=EtlJobResponse)
async def start_etl(req: EtlRunRequest, background_tasks: BackgroundTasks):
    """Trigger an ingestion run in the background."""
    global _running
    if _running:
        raise HTTPException(status_code=409, detail="An ETL run is already in progress")

    try:
        sources = resolve_sources(
            req.sources or None,
            repo=req.repo,
            packages=[package.model_dump() for package in req.packages],
            cve_ids=req.cve_ids,
            keywords=req.keywords,
            manifests=[manifest.model_dump() for manifest in req.manifests],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not sources:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one input: repo, packages, cve_ids, keywords or manifests",
        )

    job_id = uuid.uuid4().hex[:12]
    _state.update({
        "jobId": job_id,
        "status": "running",
        "sources": sources,
        "startedAt": utc_now(),
        "finishedAt": None,
        "progress": None,
        "logs": [],
        "error": None,
        "summary": None,
    })
    _running = True
    logger.info("ETL run %s queued for %s", job_id, ", ".join(sources))
    background_tasks.add_task(_execute, job_id, req, sources)

    return EtlJobResponse(jobId=job_id, status="running", sources=sources)


async def _execute(job_id: str, req: EtlRunRequest, sources: list[str]) -> None:
    global _running
    try:
        summary = await run_etl(
            sources,
            repo=req.repo,
            packages=[package.model_dump() for package in req.packages],
            cve_ids=req.cve_ids,
            keywords=req.keywords,
            ecosystem=req.ecosystem,
            manifests=[manifest.model_dump() for manifest in req.manifests],
            max_items=req.max_items,
            cross_ref=req.cross_ref,
            max_commits=req.max_commits,
            max_issues=req.max_issues,
            max_timelines=req.max_timelines,
            on_progress=_on_progress,
        )
        _state["summary"] = summary
        failures = [job.get("error") for job in summary.get("jobs") or [] if job.get("error")]
        _state["status"] = "completed" if summary.get("success") else "completed_with_errors"
        _state["error"] = "; ".join(str(failure) for failure in failures if failure) or None
        _log(f"[{utc_now()}] run finished ({_state['status']})")
    except Exception as exc:
        logger.exception("ETL run %s failed", job_id)
        _state["status"] = "failed"
        _state["error"] = str(exc)
        _log(f"[{utc_now()}] run failed: {exc}")
    finally:
        _state["finishedAt"] = utc_now()
        _history.appendleft(_snapshot())
        _running = False


@router.get("/status", response_model=EtlStatusResponse)
async def etl_status():
    """Return the current run, its progress log and recent run history."""
    return EtlStatusResponse(**_state, history=list(_history))


@router.get("/jobs/{job_id}")
async def etl_job(job_id: str):
    """Return a single run by id (current run first, then history)."""
    if _state["jobId"] == job_id:
        return {**_state, "history": []}
    for entry in _history:
        if entry.get("jobId") == job_id:
            return {**entry, "logs": [], "progress": None, "history": []}
    raise HTTPException(status_code=404, detail=f"ETL job '{job_id}' not found")
