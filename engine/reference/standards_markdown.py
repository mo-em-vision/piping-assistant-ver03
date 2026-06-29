"""Shared markdown frontmatter parsing for standards content."""

from __future__ import annotations

from typing import Any

import yaml


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    metadata = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
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
