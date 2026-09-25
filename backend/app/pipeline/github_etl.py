"""GitHub ingestion: repository packages, commits, issues and their security links."""

from __future__ import annotations

import base64
import logging
import re
from typing import Sequence

from app.pipeline.base import ApiError, accumulate, empty_counts, github_client, write_rows
from app.pipeline.dependency_graph import MANIFEST_PRIORITY, ingest_manifest, parse_manifest
from app.pipeline.osv_etl import CVE_PATTERN
from app.pipeline.queries import (
    COMMIT_UPSERT,
    FIXES_LINK,
    ISSUE_UPSERT,
    PACKAGE_UPSERT,
    PATCHES_LINK,
    REFERENCES_LINK,
    VULN_UPSERT,
)

logger = logging.getLogger("codemap.pipeline")

GHSA_PATTERN = re.compile(r"\bGHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}\b")
CLOSED_EVENTS = ("closed", "referenced", "connected", "merged")
MAX_MESSAGE = 400
MAX_BODY_SCAN = 4000


def issue_id(owner: str, repo: str, number: int | str) -> str:
    return f"{owner}/{repo}#{number}"


def extract_vuln_ids(text: str | None, limit: int = 5) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for pattern in (CVE_PATTERN, GHSA_PATTERN):
        for match in pattern.findall(text):
            if match not in found:
                found.append(match)
    return found[:limit]


def _vuln_stub(identifier: str, source: str = "github") -> dict:
    is_cve = bool(CVE_PATTERN.fullmatch(identifier))
    return {
        "id": identifier,
        "source": source,
        "summary": None,
        "cvss": None,
        "cvss_vector": None,
        "severity": None,
        "published": None,
        "modified": None,
        "aliases": None,
        "reference_urls": None,
        "cwe": None,
        "osv_id": None if is_cve else identifier,
        "cve_id": identifier if is_cve else None,
        "url": (
            f"https://nvd.nist.gov/vuln/detail/{identifier}"
            if is_cve
            else f"https://github.com/advisories/{identifier}"
        ),
    }


def _decode_file(data: dict | None) -> str | None:
    if not isinstance(data, dict) or data.get("type") != "file":
        return None
    payload = data.get("content")
    if not payload:
        return None
    if data.get("encoding") == "base64":
        try:
            return base64.b64decode(payload).decode("utf-8", errors="replace")
        except (ValueError, TypeError):
            return None
    return str(payload)


def _commit_row(owner: str, repo: str, sha: str, commit: dict | None) -> dict:
    commit = commit or {}
    author = commit.get("author") or {}
    user = author.get("name") or author.get("email") or ""
    return {
        "hash": sha,
        "message": str(commit.get("message") or "").strip()[:MAX_MESSAGE] or None,
        "timestamp": author.get("date"),
        "author": user or None,
        "repo": f"{owner}/{repo}",
        "url": f"https://github.com/{owner}/{repo}/commit/{sha}",
        "source": "github",
    }


def _issue_row(owner: str, repo: str, issue: dict) -> dict:
    return {
        "id": issue_id(owner, repo, issue.get("number")),
        "title": str(issue.get("title") or "")[:500] or None,
        "status": issue.get("state"),
        "url": issue.get("html_url"),
        "repo": f"{owner}/{repo}",
        "number": issue.get("number"),
        "author": ((issue.get("user") or {}).get("login")),
        "created_at": issue.get("created_at"),
        "source": "github",
    }


async def ingest(
    repo: str,
    max_commits: int = 20,
    max_issues: int = 10,
    max_timelines: int = 5,
    source: str = "github",
) -> dict:
    counts = empty_counts()
    stats = {"commits": 0, "issues": 0, "timelines": 0, "manifests": 0}

    parts = str(repo or "").strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("repo must look like 'owner/name'")
    owner, name = parts

    async with github_client() as client:
        meta = await client.get(f"/repos/{owner}/{name}")
        if not isinstance(meta, dict):
            raise ApiError(f"GitHub repository '{repo}' was not found")

        full_name = meta.get("full_name") or f"{owner}/{name}"
        html_url = meta.get("html_url") or f"https://github.com/{full_name}"
        description = meta.get("description")
        stars = meta.get("stargazers_count")
        logger.info("GitHub: ingesting %s (%s stars)", full_name, stars)

        manifest_ingested = False
        manifest = None
        for filename in MANIFEST_PRIORITY:
            data = await client.get(f"/repos/{owner}/{name}/contents/{filename}")
            content = _decode_file(data)
            if not content:
                continue
            manifest = parse_manifest(filename, content)
            if manifest is None or not manifest.name:
                continue
            manifest_counts = await ingest_manifest(
                manifest,
                source=source,
                repo=full_name,
                package_url=html_url,
                package_description=description,
                stars=stars,
            )
            accumulate(counts, manifest_counts)
            stats["manifests"] += 1
            manifest_ingested = True
            break

        if not manifest_ingested:
            root_name = str(manifest.name if manifest else name).strip() or name
            counts = accumulate(counts, await write_rows(PACKAGE_UPSERT, [{
                "name": root_name,
                "ecosystem": "github",
                "source": source,
                "version": meta.get("default_branch"),
                "repo": full_name,
                "url": html_url,
                "description": description,
                "stars": stars,
            }]))
            logger.info("GitHub: no manifest found, created package node for %s", root_name)

        commit_rows: list[dict] = []
        commit_hashes: set[str] = set()
        patch_rows: list[dict] = []
        commits = await client.get(
            f"/repos/{owner}/{name}/commits",
            params={"per_page": max(1, min(max_commits, 100))},
        )
        for entry in commits or []:
            sha = entry.get("sha")
            if not sha:
                continue
            row = _commit_row(owner, name, sha, entry.get("commit"))
            commit_rows.append(row)
            commit_hashes.add(sha)
            for vuln_id in extract_vuln_ids(row.get("message")):
                patch_rows.append({"hash": sha, "vuln_id": vuln_id, "source": source})
        stats["commits"] = len(commit_rows)
        logger.info("GitHub: %s commits fetched for %s", len(commit_rows), full_name)

        issue_rows: list[dict] = []
        reference_rows: list[dict] = []
        stub_rows: dict[str, dict] = {}
        closed_numbers: list[int] = []
        page = 1
        while len(issue_rows) < max_issues and page <= 3:
            batch = await client.get(
                f"/repos/{owner}/{name}/issues",
                params={"state": "all", "per_page": 100, "page": page},
            )
            if not isinstance(batch, list) or not batch:
                break
            for entry in batch:
                if len(issue_rows) >= max_issues:
                    break
                if not isinstance(entry, dict) or "pull_request" in entry or not entry.get("number"):
                    continue
                row = _issue_row(owner, name, entry)
                issue_rows.append(row)
                if entry.get("state") == "closed":
                    closed_numbers.append(entry["number"])
                scan_text = " ".join([
                    str(entry.get("title") or ""),
                    str(entry.get("body") or "")[:MAX_BODY_SCAN],
                ])
                for vuln_id in extract_vuln_ids(scan_text):
                    stub_rows.setdefault(vuln_id, _vuln_stub(vuln_id, source))
                    reference_rows.append({"issue_id": row["id"], "vuln_id": vuln_id, "source": source,
                                           "summary": None, "url": None, "aliases": None, "cve_id": None,
                                           "reference_urls": None})
            if len(batch) < 100:
                break
            page += 1
        stats["issues"] = len(issue_rows)
        logger.info("GitHub: %s issues fetched for %s", len(issue_rows), full_name)

        if stub_rows:
            accumulate(counts, await write_rows(VULN_UPSERT, list(stub_rows.values())))

        timeline_rows: list[dict] = []
        timeline_hashes: set[str] = set()
        timeline_targets = closed_numbers[: max(0, max_timelines)]
        for number in timeline_targets:
            events = await client.get(f"/repos/{owner}/{name}/issues/{number}/timeline",
                                      params={"per_page": 100})
            if not isinstance(events, list):
                continue
            stats["timelines"] += 1
            for event in events:
                if not isinstance(event, dict):
                    continue
                commit_sha = event.get("commit_id")
                if not commit_sha or event.get("event") not in CLOSED_EVENTS:
                    continue
                timeline_rows.append({
                    "hash": commit_sha,
                    "issue_id": issue_id(owner, name, number),
                    "source": source,
                })
                timeline_hashes.add(commit_sha)
        logger.info("GitHub: %s issue timelines scanned for %s", stats["timelines"], full_name)

        orphan_rows = [
            _commit_row(owner, name, sha, None)
            for sha in timeline_hashes - commit_hashes
        ]

        requests = client.request_count

    if commit_rows or orphan_rows:
        accumulate(counts, await write_rows(COMMIT_UPSERT, commit_rows + orphan_rows))
    if issue_rows:
        accumulate(counts, await write_rows(ISSUE_UPSERT, issue_rows))
    if timeline_rows:
        accumulate(counts, await write_rows(FIXES_LINK, timeline_rows))
    if patch_rows:
        accumulate(counts, await write_rows(PATCHES_LINK, patch_rows))
    if reference_rows:
        accumulate(counts, await write_rows(REFERENCES_LINK, reference_rows))

    counts["items"] = stats["commits"] + stats["issues"]
    return {
        "counts": counts,
        "requests": requests,
        "stats": stats,
        "vuln_ids": sorted(stub_rows),
    }


async def ingest_repos(repos: Sequence[str], **kwargs) -> dict:
    counts = empty_counts()
    requests = 0
    stats: dict[str, int] = {}
    vuln_ids: set[str] = set()
    for index, repo in enumerate(repos, start=1):
        logger.info("GitHub: repository %s/%s (%s)", index, len(repos), repo)
        result = await ingest(repo, **kwargs)
        accumulate(counts, result["counts"])
        requests += result.get("requests", 0)
        for key, value in result.get("stats", {}).items():
            stats[key] = stats.get(key, 0) + value
        vuln_ids.update(result.get("vuln_ids") or [])
    return {"counts": counts, "requests": requests, "stats": stats, "vuln_ids": sorted(vuln_ids)}
