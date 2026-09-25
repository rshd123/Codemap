"""Command line entry point for the CodeMap ETL pipeline."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.pipeline.dependency_graph import MANIFEST_PRIORITY  # noqa: E402
from app.pipeline.runner import SOURCES, run_etl  # noqa: E402

logger = logging.getLogger("codemap.pipeline")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codemap-etl",
        description="Populate the CodeMap knowledge graph from GitHub, OSV.dev, NVD and dependency manifests.",
    )
    parser.add_argument(
        "--sources",
        default=None,
        help=f"Comma separated subset of: {', '.join(SOURCES)} (default: derived from the inputs)",
    )
    parser.add_argument("--repo", default=None, help="GitHub repository as owner/name")
    parser.add_argument(
        "--package",
        action="append",
        default=[],
        dest="packages",
        metavar="NAME[:ECOSYSTEM[:VERSION]]",
        help="Package queried against OSV.dev (repeatable)",
    )
    parser.add_argument(
        "--ecosystem",
        default=None,
        help="Ecosystem for packages and NVD matching (npm, pypi, maven, cargo)",
    )
    parser.add_argument(
        "--cve",
        action="append",
        default=[],
        dest="cves",
        metavar="ID",
        help="Vulnerability id, comma separated or repeated",
    )
    parser.add_argument("--keyword", action="append", default=[], dest="keywords", help="NVD keyword search (repeatable)")
    parser.add_argument(
        "--manifest",
        action="append",
        default=[],
        dest="manifests",
        metavar="PATH",
        help=f"Local manifest to ingest ({', '.join(MANIFEST_PRIORITY)}) (repeatable)",
    )
    parser.add_argument("--max-items", type=int, default=25, help="Cap per source (CVEs, advisories, packages)")
    parser.add_argument("--max-commits", type=int, default=20, help="Commits fetched per repository")
    parser.add_argument("--max-issues", type=int, default=10, help="Issues fetched per repository")
    parser.add_argument("--max-timelines", type=int, default=5, help="Issue timelines scanned for closing commits")
    parser.add_argument("--no-cross-ref", action="store_true", help="Skip the OSV cross-reference while ingesting NVD data")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--json", action="store_true", help="Print the run summary as JSON")
    return parser


def _split(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        out.extend(part.strip() for part in str(value).split(",") if part.strip())
    return out


def _load_manifests(paths: list[str]) -> list[dict]:
    manifests: list[dict] = []
    for raw_path in paths:
        path = Path(raw_path)
        filename = path.name
        if filename not in MANIFEST_PRIORITY:
            raise SystemExit(
                f"Unsupported manifest '{filename}'. Expected one of: {', '.join(MANIFEST_PRIORITY)}"
            )
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SystemExit(f"Cannot read manifest '{raw_path}': {exc}") from exc
        manifests.append({"filename": filename, "content": content})
    return manifests


def _print_summary(summary: dict) -> None:
    print(f"\nETL run {'succeeded' if summary.get('success') else 'finished with failures'}")
    print(f"  sources   : {', '.join(summary.get('sources') or [])}")
    print(f"  duration  : {summary.get('durationSeconds')}s")
    print(f"  requests  : {summary.get('requests')}")
    totals = summary.get("totals") or {}
    print(
        "  created   : "
        f"{totals.get('nodes_created', 0)} nodes, "
        f"{totals.get('relationships_created', 0)} relationships, "
        f"{totals.get('properties_set', 0)} properties"
    )
    for job in summary.get("jobs") or []:
        counts = job.get("counts") or {}
        line = (
            f"  - {job.get('source'):<6} {job.get('status'):<9} "
            f"{counts.get('nodes_created', 0)}n/{counts.get('relationships_created', 0)}r "
            f"({job.get('durationSeconds')}s)"
        )
        if job.get("error"):
            line += f" error={job['error']}"
        print(line)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    logging.getLogger("neo4j").setLevel(logging.WARNING)

    sources = _split([args.sources]) if args.sources else None
    manifests = _load_manifests(args.manifests)
    cves = _split(args.cves)

    try:
        summary = asyncio.run(
            run_etl(
                sources,
                repo=args.repo,
                packages=args.packages,
                cve_ids=cves,
                keywords=_split(args.keywords),
                ecosystem=args.ecosystem,
                manifests=manifests,
                max_items=args.max_items,
                cross_ref=not args.no_cross_ref,
                max_commits=args.max_commits,
                max_issues=args.max_issues,
                max_timelines=args.max_timelines,
            )
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        _print_summary(summary)
    return 0 if summary.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
