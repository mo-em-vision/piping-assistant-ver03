"""Load executable formula definitions from embedded node metadata or standards assets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.embedded_nodes import find_embedded_body
from engine.reference.standards_markdown import split_frontmatter, compose_frontmatter
from engine.reference.standards_reader import NodeRecord, StandardsReader


def _embedded_text_from_node_dir(
    node_dir: Path,
    refs: list[str],
    equation_meta: dict[str, Any] | None,
) -> str | None:
    for name in ("node.yaml", "node.yml", "node.md"):
        path = node_dir / name
        if not path.is_file():
            continue
        metadata, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        if equation_meta and equation_meta.get("source"):
            return str(equation_meta["source"])
        for ref in refs:
            body = find_embedded_body(metadata, _normalize_ref(ref))
            if body:
                return body
    return None


def _normalize_ref(file_ref: str) -> str:
    return str(file_ref).replace("\\", "/").lstrip("/")


def _resolve_cross_node_ref(file_ref: str) -> tuple[str | None, str]:
    """Return ``(node_id, relative_asset_path)`` for cross-node references."""

    normalized = _normalize_ref(file_ref)
    if normalized.startswith("nodes/"):
        parts = normalized.split("/")
        if len(parts) >= 3:
            return parts[1], "/".join(parts[2:])
        return None, normalized

    legacy = normalized.removeprefix("../")
    if legacy != normalized and "/" in legacy:
        segment, remainder = legacy.split("/", 1)
        if segment.replace(".", "").replace("_", "").isalnum():
            node_id = f"B313-{segment}" if not segment.startswith("B313-") else segment
            return node_id, remainder

    if normalized.startswith(("equations/", "conditions/", "notes/", "references/")):
        return None, normalized
    return None, f"equations/{normalized}"


def read_formula_text(
    *,
    reader: StandardsReader | None,
    record: NodeRecord | None,
    file_ref: str | None = None,
    equation_meta: dict[str, Any] | None = None,
    fallback_node_id: str | None = None,
    node_dir: Path | None = None,
) -> str | None:
    """Resolve formula markdown text from embedded metadata, nodes DB, or disk."""

    refs: list[str] = []
    if equation_meta:
        eq_id = str(equation_meta.get("id") or "").strip()
        if reader is not None and eq_id:
            try:
                eq_record = reader.load(eq_id)
                return compose_frontmatter(eq_record.metadata, eq_record.body)
            except FileNotFoundError:
                pass
        for key in ("file", "id", "equation_id"):
            value = str(equation_meta.get(key) or "").strip()
            if value:
                refs.append(value)
    if file_ref:
        refs.append(file_ref)

    seen: set[str] = set()
    for ref in refs:
        normalized = _normalize_ref(ref)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)

        if reader is not None and record is not None:
            text = reader.read_asset_text(record, normalized)
            if text:
                return text

        other_node_id, asset_path = _resolve_cross_node_ref(normalized)
        if reader is not None and other_node_id:
            try:
                other = reader.load(other_node_id)
            except FileNotFoundError:
                other = None
            if other is not None:
                text = reader.read_asset_text(other, asset_path)
                if text:
                    return text

        if reader is not None and fallback_node_id and other_node_id is None:
            try:
                other = reader.load(fallback_node_id)
            except FileNotFoundError:
                other = None
            if other is not None:
                text = reader.read_asset_text(other, normalized)
                if text:
                    return text

        if node_dir is not None:
            candidate = node_dir / normalized
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")

    if node_dir is not None:
        text = _embedded_text_from_node_dir(node_dir, refs, equation_meta)
        if text:
            return text
        if fallback_node_id:
            fallback_dir = node_dir.parent / fallback_node_id
            if fallback_dir.is_dir():
                text = _embedded_text_from_node_dir(fallback_dir, refs, equation_meta)
                if text:
                    return text

    return None


def load_formula_data(
    *,
    reader: StandardsReader | None = None,
    record: NodeRecord | None = None,
    file_ref: str | None = None,
    equation_meta: dict[str, Any] | None = None,
    fallback_node_id: str | None = None,
    node_dir: Path | None = None,
) -> dict[str, Any]:
    text = read_formula_text(
        reader=reader,
        record=record,
        file_ref=file_ref,
        equation_meta=equation_meta,
        fallback_node_id=fallback_node_id,
        node_dir=node_dir,
    )
    if not text:
        return {}
    metadata, _ = split_frontmatter(text)
    return metadata if isinstance(metadata, dict) else {}
