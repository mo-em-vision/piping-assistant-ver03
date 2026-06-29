"""Resolve per-pack micro-graph SQLite database paths."""

from __future__ import annotations

from pathlib import Path


def resolve_pack_graph_db(pack_root: Path) -> Path:
    """Return the graph database for a standards pack."""
    pack_root = pack_root.resolve()
    slug = pack_root.name
    compact_slug = slug.replace(".", "")
    candidates = (
        pack_root / f"{compact_slug}_graph.db",
        pack_root / "standards_graph.db",
    )
    for path in candidates:
        if path.is_file():
            return path
    return pack_root / f"{compact_slug}_graph.db"
