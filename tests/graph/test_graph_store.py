"""Graph store and traversal tests."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.graph.graph_store import GraphStore
from engine.reference.standards_reader import StandardsReader
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "standards", standard="asme_b31.3")


def test_graph_store_loads_workflows() -> None:
    reader = _reader()
    store = GraphStore(reader.pack_root)
    assert store.available
    workflows = store.list_workflows()
    ids = {wf.node_id for wf in workflows}
    assert "B313-WF-PIPE-WALL-THICKNESS" in ids


def test_micro_graph_build_plan_internal_pressure() -> None:
    reader = _reader()
    engine = GraphEngine()
    assert engine.uses_micro_graph(reader, "pipe_wall_thickness_design")
    plan = engine.build_plan(
        task_id="graph-micro-test",
        root_id="pipe_wall_thickness_design",
        inputs={
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": internal_pressure_assumption(),
        },
        reader=reader,
    )
    assert "B313-eq-wall-thickness" in plan.nodes
    assert "B313-eq-2" in plan.nodes
    assert "B313-304.1.3" not in plan.nodes


def test_get_neighbors() -> None:
    reader = _reader()
    levels = GraphEngine().get_neighbors(reader, "B313-WF-PIPE-WALL-THICKNESS", depth=1)
    assert 0 in levels
    assert "B313-WF-PIPE-WALL-THICKNESS" in levels[0]


def test_graph_store_builds_from_sources_without_sqlite_cache(tmp_path: Path) -> None:
    """SQLite is optional; Markdown/YAML under nodes/ is the source of truth."""
    import shutil

    root = Path(__file__).resolve().parents[2]
    pack_src = root / "standards" / "asme" / "asme_b31.3"
    standards_root = tmp_path / "standards"
    pack_dst = standards_root / "asme" / "asme_b31.3"
    pack_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pack_src, pack_dst, ignore=shutil.ignore_patterns("*.db"))

    cache_path = pack_dst / "asme_b313_graph.db"
    assert not cache_path.is_file()

    reader = StandardsReader(standards_root, standard="asme_b31.3")
    store = GraphStore(reader.pack_root)
    store.load(prefer_cache=False)
    assert store.available
    assert not cache_path.is_file()
    workflows = store.list_workflows()
    assert any(wf.node_id == "B313-WF-PIPE-WALL-THICKNESS" for wf in workflows)
