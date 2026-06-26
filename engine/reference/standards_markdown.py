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
