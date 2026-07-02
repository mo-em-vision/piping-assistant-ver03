"""Tests for global authority ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_markdown import split_frontmatter
from engine.validation.authority_node_validator import validate_authority_node

_FORBIDDEN_FIELDS = frozenset(
    {
        "runtime_value",
        "fact_value",
        "execution_id",
        "task_id",
        "selected_for_execution",
        "active_in_context",
        "calculation_result",
        "user_input",
        "value",
        "unit",
        "source",
        "timestamp",
    }
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _authorities_dir() -> Path:
    return _project_root() / "knowledge" / "global" / "authorities" / "nodes"


def test_authority_nodes_have_required_fields() -> None:
    for path in sorted(_authorities_dir().glob("AUTH-*.yaml")):
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        assert meta["type"] == "authority"
        assert str(meta["id"]).startswith("AUTH-")
        assert validate_authority_node(meta) == [], path.name
        for field in _FORBIDDEN_FIELDS:
            assert field not in meta, f"{path.name} must not contain {field!r}"


def test_authority_pack_compiles() -> None:
    from engine.graph.graph_builder import GraphBuilder
    from engine.reference.graph_cache import write_graph_cache

    pack_root = _project_root() / "knowledge" / "global" / "authorities"
    graph = GraphBuilder(pack_root).build()
    expected = {
        "AUTH-ASME-B31.3",
        "AUTH-ASME-B36.10M",
        "AUTH-ASTM-A106",
    }
    assert expected <= set(graph.nodes.keys())
    b313 = graph.nodes["AUTH-ASME-B31.3"]
    assert b313.node_type == "authority"
    assert b313.metadata.get("authority_class") == "design_code"
    editions = b313.metadata.get("editions") or []
    assert any(item.get("year") == 2024 for item in editions)
    write_graph_cache(pack_root, graph)


def test_authority_registry_aligns_with_pack() -> None:
    from engine.reference.authority_registry import standard_primary_authority

    authority_id, edition, role = standard_primary_authority("asme_b31.3")
    assert authority_id == "AUTH-ASME-B31.3"
    assert edition == "2024"
    assert role == "primary_design_code"
