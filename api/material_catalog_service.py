"""Cached access and warm-up for the global material catalog."""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any

from engine.reference.material_catalog_db import GlobalMaterialCatalog, load_material_registry

_catalog_cache: dict[str, GlobalMaterialCatalog] = {}
_warm_cache: dict[str, bool] = {}
_cache_lock = Lock()


def _catalog_key(standards_root: Path) -> str:
    return str(standards_root.resolve())


def _try_build_material_catalog(standards_root: Path) -> bool:
    """Build materials.db from registered sources when the search index is missing."""
    catalog = get_material_catalog(standards_root)
    if catalog.exists:
        return True
    try:
        sources = load_material_registry(standards_root)
    except (FileNotFoundError, OSError):
        return False
    if not sources:
        return False
    try:
        catalog.rebuild()
    except (FileNotFoundError, OSError):
        return False
    return catalog.exists


def get_material_catalog(standards_root: Path) -> GlobalMaterialCatalog:
    key = _catalog_key(standards_root)
    with _cache_lock:
        catalog = _catalog_cache.get(key)
        if catalog is None:
            catalog = GlobalMaterialCatalog(standards_root)
            _catalog_cache[key] = catalog
        return catalog


def warm_material_catalog(standards_root: Path) -> dict[str, Any]:
    """Open the catalog database so the first material search is immediate."""
    catalog = get_material_catalog(standards_root)
    key = _catalog_key(standards_root)

    with _cache_lock:
        if _warm_cache.get(key) and catalog.exists:
            return {"ready": True, "cached": True}

    if not catalog.exists:
        built = _try_build_material_catalog(standards_root)
        with _cache_lock:
            _warm_cache.pop(key, None)
        if not built:
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
    catalog = get_material_catalog(standards_root)
    if not catalog.exists:
        _try_build_material_catalog(standards_root)
    return catalog.search(query, limit=limit)
