#!/usr/bin/env python3

"""Write micro-graph SQLite cache from on-disk Markdown/YAML sources."""



from __future__ import annotations



import sys

from pathlib import Path



_ROOT = Path(__file__).resolve().parents[1]

if str(_ROOT) not in sys.path:

    sys.path.insert(0, str(_ROOT))



from engine.graph.graph_builder import GraphBuilder

from engine.reference.graph_cache import write_graph_cache

from engine.reference.pack_graph_db import resolve_pack_graph_db

from engine.reference.standards_paths import list_standard_packs





def build_pack_graph_db(pack_root: Path) -> Path:

    """Compile sources → PackGraph → SQLite cache."""

    pack_root = pack_root.resolve()

    graph = GraphBuilder(pack_root).build()

    return write_graph_cache(pack_root, graph)





def build_all(*, standards_root: Path | None = None) -> list[Path]:

    root = (standards_root or (_ROOT / "standards")).resolve()

    built: list[Path] = []

    for _slug, pack_root in list_standard_packs(root):

        nodes_dir = pack_root / "nodes"

        if not nodes_dir.is_dir():

            continue

        path = build_pack_graph_db(pack_root)

        built.append(path)

        print(f"  Cached graph DB: {path}")

    return built





if __name__ == "__main__":

    build_all()

