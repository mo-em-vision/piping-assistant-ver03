"""Material search for desktop UI autocomplete."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.material_catalog_db import search_materials


def search_astm_materials(
    standards_root: Path,
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Backward-compatible alias for global material search."""
    return search_materials(standards_root, query, limit=limit)


def search_material_catalog(
    standards_root: Path,
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    return search_materials(standards_root, query, limit=limit)
