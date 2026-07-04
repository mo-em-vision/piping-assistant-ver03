"""Load standards-pack defaults inherited by child nodes."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from engine.reference.standards_markdown import split_frontmatter

_PACK_FILENAMES = ("pack.yaml", "pack.yml")


@lru_cache(maxsize=32)
def load_pack_metadata(pack_root: Path) -> dict[str, Any]:
    """Return frontmatter from ``pack.yaml`` at the pack root (empty dict if missing)."""
    pack_root = pack_root.resolve()
    for name in _PACK_FILENAMES:
        path = pack_root / name
        if not path.is_file():
            continue
        metadata, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        if isinstance(metadata, dict):
            return metadata
    return {}


def apply_pack_metadata(metadata: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    """Merge inheritable pack fields into node metadata (node values win)."""
    if not pack:
        return metadata

    source_language = str(pack.get("source_language") or "").strip()
    if not source_language:
        return metadata

    text = metadata.get("text")
    if not isinstance(text, dict):
        return metadata
    if str(text.get("source_language") or "").strip():
        return metadata

    out = dict(metadata)
    merged_text = dict(text)
    merged_text["source_language"] = source_language
    out["text"] = merged_text
    return out
