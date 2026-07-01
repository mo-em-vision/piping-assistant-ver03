#!/usr/bin/env python3
"""Build the global material search catalog from registered standards sources."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.knowledge_paths import materials_root
from engine.reference.material_catalog_db import GlobalMaterialCatalog, load_material_registry
from scripts.build_astm_standards_tables_db import build_all as build_astm_packs


def build_all(*, rebuild_astm: bool = True) -> Path:
    standards_root = _ROOT / "knowledge" / "standards"
    if rebuild_astm:
        build_astm_packs()

    sources = load_material_registry(standards_root)
    if not sources:
        raise FileNotFoundError(
            f"No material sources registered in {materials_root(standards_root=standards_root) / 'registry.yaml'}"
        )

    catalog = GlobalMaterialCatalog(standards_root)
    alias_count = catalog.rebuild()
    print(f"Built {catalog.db_path} ({len(sources)} sources, {alias_count} aliases)")
    return catalog.db_path


if __name__ == "__main__":
    build_all()
