"""Material search for desktop UI autocomplete."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from api.material_catalog_service import search_material_catalog as _search_material_catalog
from api.material_catalog_service import warm_material_catalog


def search_astm_materials(
    standards_root: Path,
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Backward-compatible alias for global material search."""
    return _search_material_catalog(standards_root, query, limit=limit)


def search_material_catalog(
    standards_root: Path,
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    return _search_material_catalog(standards_root, query, limit=limit)


def warm_astm_material_catalog(standards_root: Path) -> dict[str, Any]:
    return warm_material_catalog(standards_root)
