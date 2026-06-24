"""Resolve per-pack standards lookup SQLite database paths."""

from __future__ import annotations

from pathlib import Path


def resolve_pack_tables_db(pack_root: Path) -> Path:
    """Return the tables database for a standards pack.

    Prefers, in order:
    - ``{pack_slug}.db`` (ASTM convention)
    - ``{compact_slug}_tables.db`` (e.g. ``asme_b313_tables.db`` for ``asme_b31.3``)
    - legacy ``standards_tables.db``
    """
    pack_root = pack_root.resolve()
    slug = pack_root.name
    compact_slug = slug.replace(".", "")
    candidates = (
        pack_root / f"{slug}.db",
        pack_root / f"{compact_slug}_tables.db",
        pack_root / "standards_tables.db",
    )
    for path in candidates:
        if path.is_file():
            return path

    return pack_root / f"{compact_slug}_tables.db"
