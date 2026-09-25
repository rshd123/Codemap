"""Manifest parsers and DEPENDS_ON graph ingestion."""

from __future__ import annotations

import json
import logging
import re
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from app.pipeline.base import empty_counts, read, write_rows
from app.pipeline.queries import DEPENDS_ON_UPSERT, PACKAGE_UPSERT
from app.services.graph_serializer import to_graph_data

logger = logging.getLogger("codemap.pipeline")

MANIFEST_PRIORITY: tuple[str, ...] = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pom.xml",
    "Cargo.toml",
)

MANIFEST_ECOSYSTEMS: dict[str, str] = {
    "package.json": "npm",
    "pyproject.toml": "pypi",
    "requirements.txt": "pypi",
    "pom.xml": "maven",
    "Cargo.toml": "cargo",
}

OSV_ECOSYSTEMS: dict[str, str] = {
    "npm": "npm",
    "pypi": "PyPI",
    "maven": "Maven",
    "cargo": "crates.io",
    "go": "Go",
    "nuget": "NuGet",
    "gem": "RubyGems",
    "rubygems": "RubyGems",
    "packagist": "Packagist",
    "cran": "CRAN",
    "hex": "Hex",
    "pub": "Pub",
    "swifturl": "SwiftURL",
    "github": "GitHub Actions",
}

_REQUIREMENT_SPLIT = re.compile(r"(===|==|~=|!=|>=|<=|>|<)")
_CPE_PREFIX = "cpe:2.3:"


@dataclass
class Dependency:
    name: str
    spec: str = ""


@dataclass
class Manifest:
    file: str
    ecosystem: str
    name: str | None = None
    version: str | None = None
    dependencies: list[Dependency] = field(default_factory=list)


def normalize_pypi_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def normalize_name(ecosystem: str, name: str) -> str:
    cleaned = str(name).strip()
    if ecosystem == "pypi":
        return normalize_pypi_name(cleaned)
    return cleaned


def osv_ecosystem(ecosystem: str) -> str:
    return OSV_ECOSYSTEMS.get(str(ecosystem).lower(), str(ecosystem))


def ecosystem_from_osv(osv_name: str) -> str:
    target = str(osv_name or "").strip()
    lowered = target.lower()
    for key, value in OSV_ECOSYSTEMS.items():
        if value.lower() == lowered:
            return key
    return lowered


def parse_requirement_line(line: str) -> Dependency | None:
    text = line.strip()
    if not text or text.startswith(("#", "-")):
        return None
    text = text.split("#", 1)[0].strip()
    text = text.split(";", 1)[0].strip()
    if not text or "://" in text or text.startswith("git+"):
        return None
    match = _REQUIREMENT_SPLIT.search(text)
    if match:
        raw_name, spec = text[: match.start()].strip(), text[match.start():].strip()
    else:
        raw_name, spec = text, ""
    if "[" in raw_name:
        raw_name = raw_name.split("[", 1)[0]
    raw_name = raw_name.strip().replace("_", "-")
    if not raw_name or " " in raw_name:
        return None
    return Dependency(normalize_pypi_name(raw_name), spec)


def parse_package_json(text: str) -> Manifest:
    data = json.loads(text)
    manifest = Manifest(
        file="package.json",
        ecosystem="npm",
        name=data.get("name"),
        version=data.get("version"),
    )
    seen: dict[str, Dependency] = {}
    for section in ("dependencies", "peerDependencies", "optionalDependencies", "devDependencies"):
        block = data.get(section)
        if not isinstance(block, dict):
            continue
        for raw_name, raw_spec in block.items():
            if not isinstance(raw_name, str) or not isinstance(raw_spec, str):
                continue
            seen.setdefault(raw_name, Dependency(raw_name.strip(), raw_spec.strip()))
    manifest.dependencies = list(seen.values())
    return manifest


def parse_requirements_txt(text: str) -> Manifest:
    manifest = Manifest(file="requirements.txt", ecosystem="pypi")
    seen: dict[str, Dependency] = {}
    for raw_line in text.splitlines():
        dep = parse_requirement_line(raw_line)
        if dep and dep.name not in seen:
            seen[dep.name] = dep
    manifest.dependencies = list(seen.values())
    return manifest


def parse_pyproject(text: str) -> Manifest:
    data = tomllib.loads(text)
    project = data.get("project") or {}
    manifest = Manifest(
        file="pyproject.toml",
        ecosystem="pypi",
        name=project.get("name"),
        version=project.get("version"),
    )
    seen: dict[str, Dependency] = {}

    for item in project.get("dependencies") or []:
        dep = parse_requirement_line(str(item))
        if dep:
            seen.setdefault(dep.name, dep)
    for group in (project.get("optional-dependencies") or {}).values():
        if not isinstance(group, list):
            continue
        for item in group:
            dep = parse_requirement_line(str(item))
            if dep:
                seen.setdefault(dep.name, dep)

    poetry = ((data.get("tool") or {}).get("poetry")) or {}
    if not seen and poetry:
        manifest.name = manifest.name or poetry.get("name")
        manifest.version = manifest.version or poetry.get("version")
        poetry_blocks = [poetry.get("dependencies") or {}]
        for group in ((poetry.get("group") or {}).values()):
            poetry_blocks.append((group or {}).get("dependencies") or {})
        for block in poetry_blocks:
            for raw_name, raw_spec in block.items():
                if raw_name.lower() == "python":
                    continue
                if isinstance(raw_spec, str):
                    spec = raw_spec
                elif isinstance(raw_spec, dict):
                    spec = str(raw_spec.get("version") or "").strip()
                else:
                    spec = ""
                name = normalize_pypi_name(raw_name)
                seen.setdefault(name, Dependency(name, spec))

    manifest.dependencies = list(seen.values())
    return manifest


def _strip_xml_namespace(element: ET.Element) -> None:
    element.tag = element.tag.split("}", 1)[-1]
    for child in element:
        _strip_xml_namespace(child)


def parse_pom_xml(text: str) -> Manifest:
    root = ET.fromstring(text)
    _strip_xml_namespace(root)
    project_version = (root.findtext("version") or "").strip()
    if not project_version:
        parent = root.find("parent")
        if parent is not None:
            project_version = (parent.findtext("version") or "").strip()

    manifest = Manifest(
        file="pom.xml",
        ecosystem="maven",
        name=(root.findtext("artifactId") or "").strip() or None,
        version=project_version or None,
    )
    dependencies = root.find("dependencies")
    if dependencies is None:
        return manifest

    seen: dict[str, Dependency] = {}
    for node in dependencies.findall("dependency"):
        group = (node.findtext("groupId") or "").strip()
        artifact = (node.findtext("artifactId") or "").strip()
        version = (node.findtext("version") or "").strip()
        if not group or not artifact:
            continue
        if version.startswith("${") and project_version:
            version = project_version
        name = f"{group}:{artifact}"
        seen.setdefault(name, Dependency(name, version))
    manifest.dependencies = list(seen.values())
    return manifest


def parse_cargo_toml(text: str) -> Manifest:
    data = tomllib.loads(text)
    package = data.get("package") or {}
    manifest = Manifest(
        file="Cargo.toml",
        ecosystem="cargo",
        name=package.get("name"),
        version=package.get("version"),
    )
    seen: dict[str, Dependency] = {}
    for raw_name, raw_spec in (data.get("dependencies") or {}).items():
        if isinstance(raw_spec, str):
            spec = raw_spec
        elif isinstance(raw_spec, dict):
            spec = str(raw_spec.get("version") or "").strip()
        else:
            spec = ""
        name = str(raw_name).strip()
        seen.setdefault(name, Dependency(name, spec))
    manifest.dependencies = list(seen.values())
    return manifest


PARSERS = {
    "package.json": parse_package_json,
    "pyproject.toml": parse_pyproject,
    "requirements.txt": parse_requirements_txt,
    "pom.xml": parse_pom_xml,
    "Cargo.toml": parse_cargo_toml,
}


def parse_manifest(filename: str, text: str) -> Manifest | None:
    parser = PARSERS.get(filename)
    if parser is None:
        return None
    try:
        manifest = parser(text)
    except Exception as exc:
        logger.warning("Failed to parse %s: %s", filename, exc)
        return None
    if not manifest.dependencies:
        logger.info("No dependencies found in %s", filename)
    return manifest


_CPE_ECOSYSTEM_HINTS: tuple[tuple[str, str], ...] = (
    ("node.js", "npm"),
    ("nodejs", "npm"),
    ("npm", "npm"),
    ("python", "pypi"),
    ("pypi", "pypi"),
    ("pip", "pypi"),
    ("maven", "maven"),
    ("java", "maven"),
    ("crates.io", "cargo"),
    ("crates", "cargo"),
    ("rust", "cargo"),
    ("golang", "go"),
    ("rubygems", "gem"),
    ("ruby", "gem"),
    ("nuget", "nuget"),
    (".net", "nuget"),
)


def packages_from_cpe(criteria: str, fallback_ecosystem: str | None = None) -> tuple[str, str] | None:
    if not criteria or not criteria.startswith(_CPE_PREFIX):
        return None
    parts = criteria.split(":")
    if len(parts) < 5:
        return None
    product = parts[4]
    if not product or product in ("*", "-"):
        return None
    name = product.replace("\\", "").replace("%2f", "/").replace("%2F", "/").replace("_", "-")
    haystack = " ".join(parts[5:]).lower()
    ecosystem = fallback_ecosystem
    if not ecosystem:
        ecosystem = "other"
        for hint, candidate in _CPE_ECOSYSTEM_HINTS:
            if hint in haystack:
                ecosystem = candidate
                break
    return ecosystem, name


def _package_row(
    name: str,
    ecosystem: str,
    source: str,
    version: str | None = None,
    repo: str | None = None,
    url: str | None = None,
    description: str | None = None,
    stars: int | None = None,
) -> dict:
    return {
        "name": name,
        "ecosystem": ecosystem,
        "source": source,
        "version": version,
        "repo": repo,
        "url": url,
        "description": description,
        "stars": stars,
    }


async def upsert_package(**kwargs) -> dict:
    return await write_rows(PACKAGE_UPSERT, [_package_row(**kwargs)])


async def ingest_manifest(
    manifest: Manifest,
    source: str,
    repo: str | None = None,
    package_url: str | None = None,
    package_description: str | None = None,
    stars: int | None = None,
    kind: str = "runtime",
) -> dict:
    counts = empty_counts()
    if not manifest.name:
        logger.warning("Skipping %s: manifest has no package name", manifest.file)
        return counts

    root_name = normalize_name(manifest.ecosystem, manifest.name)
    root = _package_row(
        name=root_name,
        ecosystem=manifest.ecosystem,
        source=source,
        version=manifest.version,
        repo=repo,
        url=package_url,
        description=package_description,
        stars=stars,
    )
    counts = await write_rows(PACKAGE_UPSERT, [root])
    counts["items"] = 1

    rows: list[dict] = []
    for dep in manifest.dependencies:
        dep_name = normalize_name(manifest.ecosystem, dep.name)
        if not dep_name or dep_name == root_name:
            continue
        rows.append({
            "from_name": root_name,
            "from_ecosystem": manifest.ecosystem,
            "to_name": dep_name,
            "to_ecosystem": manifest.ecosystem,
            "to_version": None,
            "spec": dep.spec or None,
            "source": source,
            "kind": kind,
        })

    dependency_counts = await write_rows(DEPENDS_ON_UPSERT, rows)
    counts = await _merge_counts(counts, dependency_counts)
    logger.info(
        "Ingested %s for %s (%s): %s dependency edges",
        manifest.file,
        root_name,
        manifest.ecosystem,
        len(rows),
    )
    return counts


async def _merge_counts(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    merged = dict(left)
    for key, value in (right or {}).items():
        merged[key] = merged.get(key, 0) + int(value)
    return merged


async def transitive_dependencies(
    name: str,
    ecosystem: str | None = None,
    max_depth: int = 4,
    limit: int = 300,
) -> dict:
    depth = max(1, min(int(max_depth), 8))
    page_limit = max(1, min(int(limit), 1000))
    params: dict = {
        "name": str(name).strip(),
        "ecosystem": str(ecosystem).strip() if ecosystem else None,
        "limit": page_limit,
    }

    query = f"""
    MATCH path = (p:Package {{name: $name}})-[:DEPENDS_ON*1..{depth}]->(descendant:Package)
    WHERE $ecosystem IS NULL OR p.ecosystem = $ecosystem
    WITH nodes(path) AS path_nodes, relationships(path) AS path_rels
    UNWIND path_nodes AS node
    WITH DISTINCT node, path_rels
    UNWIND path_rels AS rel
    WITH DISTINCT node, rel
    RETURN node, rel
    LIMIT $limit
    """
    records = await read(query, params)
    graph = to_graph_data(records)
    graph["root"] = {"name": params["name"], "ecosystem": params["ecosystem"], "maxDepth": depth}
    return graph


async def direct_dependencies(name: str, ecosystem: str | None = None, limit: int = 200) -> dict:
    params: dict = {
        "name": str(name).strip(),
        "ecosystem": str(ecosystem).strip() if ecosystem else None,
        "limit": max(1, min(int(limit), 1000)),
    }
    query = """
    MATCH (p:Package {name: $name})-[r:DEPENDS_ON]->(d:Package)
    WHERE $ecosystem IS NULL OR p.ecosystem = $ecosystem
    RETURN p, r, d
    LIMIT $limit
    """
    records = await read(query, params)
    graph = to_graph_data(records)
    graph["root"] = {"name": params["name"], "ecosystem": params["ecosystem"]}
    return graph
