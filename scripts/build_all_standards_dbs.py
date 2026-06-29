#!/usr/bin/env python3
"""Build all compiled standards SQLite databases from markdown/YAML sources."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.build_astm_standards_tables_db import build_all as build_astm_tables
from scripts.build_material_catalog_db import build_all as build_material_catalog
from scripts.build_pipe_dimensions_db import build_all as build_pipe_dimensions
from scripts.build_standards_nodes_db import build_all as build_nodes
from scripts.build_standards_registry_db import build_all as build_registry
from scripts.build_standards_tables_db import build_database as build_b313_tables
from scripts.build_standards_tasks_db import build_all as build_tasks


def build_all(*, standards_root: Path | None = None, rebuild_astm: bool = True) -> None:
    root = (standards_root or (_ROOT / "standards")).resolve()
    print("Building ASME B31.3 lookup tables...")
    build_b313_tables()
    print("Building ASTM pack lookup tables...")
    build_astm_tables()
    print("Building pack graph databases...")
    from scripts.build_graph_db import build_all as build_graph

    build_graph(standards_root=root)
    print("Building pack node databases...")
    build_nodes(standards_root=root)
    print("Building standards config registry...")
    build_registry(standards_root=root)
    print("Building global material catalog...")
    build_material_catalog(rebuild_astm=False)
    print("Building pipe dimension databases...")
    build_pipe_dimensions(standards_root=root)
    print("All standards databases built.")


if __name__ == "__main__":
    build_all()
