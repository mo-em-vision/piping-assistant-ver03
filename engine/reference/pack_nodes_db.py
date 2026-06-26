"""Resolve per-pack standards nodes SQLite database paths."""

from __future__ import annotations

from pathlib import Path


def resolve_pack_nodes_db(pack_root: Path) -> Path:
    """Return the nodes database for a standards pack.

    Prefers ``{compact_slug}_nodes.db`` (e.g. ``asme_b313_nodes.db`` for ``asme_b31.3``).
    """
    pack_root = pack_root.resolve()
    slug = pack_root.name
    compact_slug = slug.replace(".", "")
    candidates = (
        pack_root / f"{compact_slug}_nodes.db",
        pack_root / "standards_nodes.db",
    )
    for path in candidates:
        if path.is_file():
            return path
    return pack_root / f"{compact_slug}_nodes.db"
