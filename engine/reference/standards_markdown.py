"""Shared markdown frontmatter parsing for standards content."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        # Only column-0 ``---`` closes frontmatter; indented delimiters appear
        # inside embedded ``source: |`` blocks in node sources.
        if line == "---" or line == "---\r":
            end_index = index
            break
    if end_index is None:
        return {}, text
    metadata_text = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    metadata = yaml.safe_load(metadata_text) or {}
    return metadata, body


def compose_frontmatter(metadata: dict[str, Any], body: str = "") -> str:
    """Serialize metadata and markdown body into a node source file."""
    yaml_text = yaml.safe_dump(
        metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip()
    body_text = body.rstrip()
    if body_text:
        return f"---\n{yaml_text}\n---\n\n{body_text}\n"
    return f"---\n{yaml_text}\n---\n"


_YAML_PRIMARY_BLOCK_MD_KEYS = frozenset({
    "inputs",
    "equations",
    "formulas",
    "conditions",
    "outputs",
    "interactions",
    "assumptions",
    "depends_on",
    "lookups",
    "contains",
    "requires",
    "calculates",
})


def merge_dual_node_frontmatter(
    node_dir: Path,
    primary_metadata: dict[str, Any],
    primary_body: str,
    *,
    primary_path: Path | None = None,
) -> tuple[dict[str, Any], str]:
    """Merge sibling ``node.md`` frontmatter when both yaml and md exist.

    Primary source (usually ``node.yaml``) wins on key conflicts; markdown-only
    keys such as ``nomenclature`` are preserved. The longer body is kept.
    """
    md_path = node_dir / "node.md"
    if not md_path.is_file():
        return primary_metadata, primary_body
    if primary_path is not None and primary_path.resolve() == md_path.resolve():
        return primary_metadata, primary_body

    md_metadata, md_body = split_frontmatter(md_path.read_text(encoding="utf-8"))
    if primary_path is not None and primary_path.suffix.lower() in {".yaml", ".yml"}:
        merged_metadata = dict(primary_metadata)
        node_type = str(primary_metadata.get("type") or md_metadata.get("type") or "")
        for key, value in md_metadata.items():
            if key in primary_metadata:
                continue
            if node_type != "definition" and key in _YAML_PRIMARY_BLOCK_MD_KEYS:
                continue
            merged_metadata[key] = value
    else:
        merged_metadata = {**md_metadata, **primary_metadata}
    body = md_body if len(md_body.strip()) > len(primary_body.strip()) else primary_body
    return merged_metadata, body
