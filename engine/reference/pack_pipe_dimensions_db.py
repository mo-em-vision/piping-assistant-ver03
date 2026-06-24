"""Resolve per-pack pipe dimension SQLite database paths."""

from __future__ import annotations

from pathlib import Path


def resolve_pack_pipe_dimensions_db(pack_root: Path) -> Path:
    """Return the pipe dimensions database for a standards pack.

    Uses ``pipe_dimensions.db`` at the pack root (same name for every pack).
    """
    return pack_root.resolve() / "pipe_dimensions.db"
