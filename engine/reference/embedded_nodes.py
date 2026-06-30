"""Helpers for embedded child nodes stored inside paragraph/table metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from engine.reference.standards_markdown import split_frontmatter
from engine.reference.node_types import normalize_node_metadata


_EMBEDDED_NODE_CONTAINER_KEYS = (
    "assumptions",
    "interactions",
    "criteria",
    "notes",
    "equations",
    "texts",
    "conditions",
    "references",
)

_EMBEDDED_SEARCH_CONTAINER_KEYS = _EMBEDDED_NODE_CONTAINER_KEYS + (
    "conditions",
    "references",
    "inputs",
    "outputs",
)

_BODY_KEYS = ("body", "text", "description", "markdown", "content")

_DEFAULT_TYPES = {
    "assumptions": "parameter",
    "interactions": "parameter",
    "criteria": "text",
    "notes": "text",
    "conditions": "text",
    "references": "text",
    "inputs": "parameter",
    "outputs": "quantity",
    "equations": "equation",
    "texts": "text",
}

_DEFAULT_KINDS = {
    "assumptions": "assumption",
    "interactions": "interaction",
    "notes": "note",
    "conditions": "condition",
    "references": "reference",
    "texts": "section",
}


@dataclass(frozen=True)
class EmbeddedNodeSource:
    node_id: str
    node_type: str
    metadata: dict[str, Any]
    body: str
    source_rel_path: str
    aliases: tuple[str, ...] = ()


def _body_from_item(item: dict[str, Any]) -> str:
    for key in _BODY_KEYS:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _parse_source_item(item: dict[str, Any]) -> tuple[dict[str, Any], str] | None:
    source = item.get("source")
    if not isinstance(source, str) or not source.strip():
        return None
    return split_frontmatter(source)


def _item_node_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("node_id") or "").strip()


def _embedded_source(
    *,
    parent_id: str,
    parent_source_rel_path: str,
    container_key: str,
    item: dict[str, Any],
    subsection_id: str | None = None,
) -> EmbeddedNodeSource | None:
    node_id = _item_node_id(item)
    if not node_id:
        return None

    metadata = dict(item)
    parsed = _parse_source_item(metadata)
    if parsed is not None:
        source_metadata, source_body = parsed
        merged = dict(source_metadata)
        merged.update({k: v for k, v in metadata.items() if k != "source"})
        metadata = merged
        if source_body.strip():
            metadata.setdefault("body", source_body)
    metadata.setdefault("id", node_id)
    metadata.setdefault("type", _DEFAULT_TYPES.get(container_key, "text"))
    if container_key in _DEFAULT_KINDS:
        metadata.setdefault("kind", _DEFAULT_KINDS[container_key])
    metadata.setdefault("parent_node_id", parent_id)
    metadata.setdefault("source_container", container_key)
    if subsection_id:
        metadata.setdefault("parent_subsection_id", subsection_id)
    body = _body_from_item(metadata)
    if not body and parsed is not None:
        body = parsed[1]
    if "body" not in metadata and body:
        metadata["body"] = body

    aliases: list[str] = []
    file_ref = str(metadata.get("file") or "").strip()
    if file_ref:
        aliases.append(file_ref.replace("\\", "/").lstrip("/"))
    elif container_key == "equations":
        equation_id = str(metadata.get("equation_id") or "").strip()
        if equation_id:
            aliases.append(f"equations/{equation_id.replace('-', '_')}.md")
        item_id = _item_node_id(item)
        if item_id.startswith("B313-eq-"):
            slug = item_id.split("B313-eq-", 1)[-1].replace("-", "_")
            aliases.append(f"equations/{slug}.md")
        elif item_id:
            aliases.append(f"equations/{item_id.replace('-', '_')}.md")
    elif container_key in {"conditions", "notes", "references"}:
        if item.get("source") or parsed is not None:
            item_id = str(metadata.get("id") or metadata.get("name") or "").strip()
            if item_id:
                aliases.append(f"{container_key}/{item_id.replace('-', '_')}.md")
    if subsection_id and file_ref:
        aliases.append(f"{subsection_id}/{file_ref}".replace("\\", "/").lstrip("/"))

    normalized_type, normalized_metadata = normalize_node_metadata(metadata, str(metadata["type"]))
    normalized_metadata.setdefault("id", node_id)
    normalized_metadata.setdefault("type", normalized_type)
    if body and "body" not in normalized_metadata:
        normalized_metadata["body"] = body
    return EmbeddedNodeSource(
        node_id=node_id,
        node_type=normalized_type,
        metadata=normalized_metadata,
        body=body,
        source_rel_path=parent_source_rel_path,
        aliases=tuple(dict.fromkeys(aliases)),
    )


def iter_embedded_node_sources(
    *,
    parent_id: str,
    parent_source_rel_path: str,
    metadata: dict[str, Any],
) -> Iterator[EmbeddedNodeSource]:
    """Yield embedded node sources from local metadata containers."""

    def emit_container(
        container_key: str,
        items: Any,
        *,
        subsection_id: str | None = None,
    ) -> Iterator[EmbeddedNodeSource]:
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            parsed = _parse_source_item(item)
            if parsed is not None:
                source_metadata, source_body = parsed
                merged = dict(source_metadata)
                merged.update({k: v for k, v in item.items() if k != "source"})
                item = merged
                if source_body.strip():
                    item.setdefault("body", source_body)
            source = _embedded_source(
                parent_id=parent_id,
                parent_source_rel_path=parent_source_rel_path,
                container_key=container_key,
                item=item,
                subsection_id=subsection_id,
            )
            if source is not None:
                yield source

    for key in _EMBEDDED_NODE_CONTAINER_KEYS:
        yield from emit_container(key, metadata.get(key))

    for subsection in metadata.get("subsections", []) or []:
        if not isinstance(subsection, dict):
            continue
        subsection_id = str(subsection.get("id") or "").strip() or None
        for key in _EMBEDDED_NODE_CONTAINER_KEYS:
            yield from emit_container(key, subsection.get(key), subsection_id=subsection_id)


def _asset_reference_matches(item: dict[str, Any], wanted: str) -> bool:
    normalized = wanted.replace("\\", "/").lstrip("/")
    file_ref = str(item.get("file") or "").replace("\\", "/").lstrip("/")
    if file_ref and file_ref == normalized:
        return True
    item_id = _item_node_id(item)
    if item_id and item_id == normalized:
        return True
    parsed = _parse_source_item(item)
    if parsed is not None:
        source_metadata, _ = parsed
        file_ref = str(source_metadata.get("file") or item.get("file") or "").replace("\\", "/").lstrip("/")
        if file_ref == normalized:
            return True
        source_id = str(
            source_metadata.get("id")
            or source_metadata.get("node_id")
            or source_metadata.get("equation_id")
            or item.get("id")
            or item.get("equation_id")
            or ""
        ).strip()
        if source_id and (source_id == normalized or source_id == Path(normalized).stem):
            return True
    equation_id = str(item.get("equation_id") or "").strip()
    if not equation_id and parsed is not None:
        equation_id = str(parsed[0].get("equation_id") or "").strip()
    if equation_id:
        slug = equation_id.replace("-", "_")
        if normalized in {f"equations/{slug}.md", f"equations/{equation_id}.md"}:
            return True
        if normalized.startswith(f"equations/{slug}") and normalized.endswith(".md"):
            return True
    if item_id.startswith("B313-eq-"):
        slug = item_id.split("B313-eq-", 1)[-1].replace("-", "_")
        if normalized == f"equations/{slug}.md":
            return True
    stem = str(item.get("id") or item.get("name") or "").strip().replace("-", "_")
    if stem and normalized == f"conditions/{stem}.md":
        return True
    if stem and normalized == f"notes/{stem}.md":
        return True
    if stem and normalized == f"references/{stem}.md":
        return True
    return False


def _embedded_source_text(item: dict[str, Any]) -> str | None:
    source = item.get("source")
    if isinstance(source, str) and source.strip():
        return source.strip()
    body = _body_from_item(item)
    return body or None


def find_embedded_body(metadata: dict[str, Any], reference: str) -> str | None:
    """Best-effort lookup of embedded object text by ``file`` or ``id``."""

    wanted = reference.replace("\\", "/").lstrip("/")
    if not wanted:
        return None

    def walk(item: Any) -> str | None:
        if isinstance(item, dict):
            if _asset_reference_matches(item, wanted):
                return _embedded_source_text(item)
            parsed = _parse_source_item(item)
            if parsed is not None:
                source_metadata, _source_body = parsed
                merged = dict(item)
                merged.update({k: v for k, v in source_metadata.items() if k != "source"})
                if _asset_reference_matches(merged, wanted):
                    return _embedded_source_text(item)
            for value in item.values():
                found = walk(value)
                if found is not None:
                    return found
        elif isinstance(item, list):
            for value in item:
                found = walk(value)
                if found is not None:
                    return found
        return None

    return walk(metadata)
