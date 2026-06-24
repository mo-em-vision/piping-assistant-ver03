"""Cached access and warm-up for the global material catalog."""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any

from engine.reference.material_catalog_db import GlobalMaterialCatalog

_catalog_cache: dict[str, GlobalMaterialCatalog] = {}
_warm_cache: dict[str, bool] = {}
_cache_lock = Lock()


def get_material_catalog(standards_root: Path) -> GlobalMaterialCatalog:
    key = str(standards_root.resolve())
    with _cache_lock:
        catalog = _catalog_cache.get(key)
        if catalog is None:
            catalog = GlobalMaterialCatalog(standards_root)
            _catalog_cache[key] = catalog
        return catalog


def warm_material_catalog(standards_root: Path) -> dict[str, Any]:
    """Open the catalog database so the first material search is immediate."""
    catalog = get_material_catalog(standards_root)
    key = str(standards_root.resolve())

    with _cache_lock:
        if _warm_cache.get(key):
            return {"ready": catalog.exists, "cached": True}

    if not catalog.exists:
        return {"ready": False, "cached": False, "reason": "catalog_missing"}

    with catalog.connect() as connection:
        connection.execute("PRAGMA query_only = ON")
        connection.execute("SELECT COUNT(*) FROM material_aliases").fetchone()

    with _cache_lock:
        _warm_cache[key] = True

    return {"ready": True, "cached": True}


def search_material_catalog(
    standards_root: Path,
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, str]]:
    warm_material_catalog(standards_root)
    return get_material_catalog(standards_root).search(query, limit=limit)
