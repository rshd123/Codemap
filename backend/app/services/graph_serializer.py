"""Convert Neo4j records into the { nodes, links } contract used by react-force-graph."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Iterable

DEFAULT_LABEL = "Node"

_RECORD_KEYS = ("element_id", "elementId", "labels", "properties", "identity")
_LINK_KEYS = ("startNodeElementId", "endNodeElementId", "start", "end")


def _json_safe(value: Any) -> Any:
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def _is_mapping(value: Any) -> bool:
    return isinstance(value, dict)


def _first_label(labels: Any) -> str:
    if not labels:
        return DEFAULT_LABEL
    if isinstance(labels, str):
        return labels
    try:
        ordered = sorted(str(label) for label in labels)
    except TypeError:
        return DEFAULT_LABEL
    return ordered[0] if ordered else DEFAULT_LABEL


def _element_id(obj: Any, fallback: Any = None) -> str:
    for attribute in ("element_id", "elementId"):
        value = getattr(obj, attribute, None)
        if value:
            return str(value)
    if _is_mapping(obj):
        for key in ("element_id", "elementId", "id", "identity"):
            if obj.get(key) is not None:
                return str(obj.get(key))
    return str(fallback if fallback is not None else id(obj))


def node_to_dict(node: Any, fallback_id: Any = None) -> dict:
    if hasattr(node, "labels"):
        return {"id": _element_id(node, fallback_id), "label": _first_label(node.labels), **_json_safe(dict(node))}

    if _is_mapping(node):
        data = dict(node)
        labels = data.get("labels") if "labels" in data else data.get("label")
        raw_properties = data.get("properties")
        properties = raw_properties if isinstance(raw_properties, dict) else {
            key: value for key, value in data.items() if key not in _RECORD_KEYS
        }
        return {"id": _element_id(data, fallback_id), "label": _first_label(labels), **_json_safe(properties)}

    return {"id": str(fallback_id if fallback_id is not None else id(node)), "label": DEFAULT_LABEL}


def relationship_to_dict(rel: Any) -> dict | None:
    if hasattr(rel, "nodes") and hasattr(rel, "type"):
        start = rel.nodes[0] if len(rel.nodes) > 0 else None
        end = rel.nodes[-1] if len(rel.nodes) > 1 else None
        payload = {key: value for key, value in dict(rel).items()}
        return {
            "source": _element_id(start, ""),
            "target": _element_id(end, ""),
            "type": str(rel.type),
            **_json_safe(payload),
        }

    if _is_mapping(rel):
        data = dict(rel)
        if "type" not in data:
            return None
        source = data.get("startNodeElementId") or data.get("start") or data.get("source")
        target = data.get("endNodeElementId") or data.get("end") or data.get("target")
        raw_properties = data.get("properties")
        payload = raw_properties if isinstance(raw_properties, dict) else {
            key: value for key, value in data.items() if key not in _LINK_KEYS + ("type", "properties")
        }
        return {"source": str(source or ""), "target": str(target or ""), "type": str(data["type"]), **_json_safe(payload)}

    return None


def _record_values(record: Any) -> list[Any]:
    if hasattr(record, "labels") or (hasattr(record, "nodes") and hasattr(record, "type")):
        return [record]

    if _is_mapping(record):
        data = dict(record)
        if any(key in data for key in _RECORD_KEYS) or ("type" in data and any(key in data for key in _LINK_KEYS)):
            return [record]
        return list(data.values())

    return [record]


def to_graph_data(records: Iterable[Any] | None) -> dict:
    nodes: dict[str, dict] = {}
    links: dict[tuple[str, str, str], dict] = {}

    for record in records or []:
        for value in _record_values(record):
            for item in _walk(value):
                link = relationship_to_dict(item) if _looks_like_relationship(item) else None
                if link is not None:
                    key = (link["source"], link["target"], link["type"])
                    if link["source"] and link["target"]:
                        links.setdefault(key, link)
                    continue

                if _looks_like_node(item):
                    node = node_to_dict(item)
                    nodes.setdefault(node["id"], node)

    return {"nodes": list(nodes.values()), "links": list(links.values())}


def _looks_like_relationship(item: Any) -> bool:
    if hasattr(item, "nodes") and hasattr(item, "type"):
        return True
    if _is_mapping(item):
        data = dict(item)
        return "type" in data and any(key in data for key in _LINK_KEYS)
    return False


def _looks_like_node(item: Any) -> bool:
    if hasattr(item, "labels"):
        return True
    if _is_mapping(item):
        data = dict(item)
        return "labels" in data or "elementId" in data or "element_id" in data or "properties" in data
    return False


def _walk(value: Any):
    if isinstance(value, (list, tuple, set)):
        for entry in value:
            yield from _walk(entry)
        return
    yield value
