"""Tests for ASME B31.3 paragraph ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.paragraph_authoring_policy import check_paragraph_frontmatter_placement
from engine.reference.standards_markdown import split_frontmatter
from engine.validation.paragraph_node_validator import validate_paragraph_node


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _paragraph_dir() -> Path:
    return (
        _project_root()
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
        / "nodes"
        / "paragraph"
    )


def test_nomenclature_paragraph_rejects_table_edges() -> None:
    issues = validate_paragraph_node(
        {
            "type": "paragraph",
            "key": "test",
            "title": "Test",
            "authority": "AUTH-ASME-B31.3",
            "edition": 2024,
            "paragraph_number": "304.1.1-b",
            "id": "304.1.1-b",
            "text": {"original": "sample"},
            "hierarchy": {"parent": "304.1", "children": []},
            "metadata": {
                "kind": "nomenclature",
                "source_revision_year": 2024,
                "last_revision": "2026-07-04",
                "edited_by": "admin",
            },
            "edges": [
                {"type": "belongs_to_authority", "target": "AUTH-ASME-B31.3"},
                {"type": "references_table", "target": "asme-b313-table-A-1"},
            ],
        }
    )
    assert any("references_table" in issue for issue in issues)


def test_304_1_1_a_introduces_minimum_required_thickness() -> None:
    path = _paragraph_dir() / "304.1.1-a.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    introduced = [
        e.get("target")
        for e in meta.get("edges") or []
        if isinstance(e, dict) and e.get("type") == "introduces_parameter"
    ]
    assert introduced == ["PARAM-minimum-required-thickness"]
    issues = validate_paragraph_node(meta)
    assert issues == [], f"{path.name}: {issues}"


def test_304_1_1_b_introduces_parameters_via_edges() -> None:
    path = _paragraph_dir() / "304.1.1-b.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert (meta.get("metadata") or {}).get("kind") != "nomenclature"
    introduced = [
        e.get("target")
        for e in meta.get("edges") or []
        if isinstance(e, dict) and e.get("type") == "introduces_parameter"
    ]
    assert "PARAM-corrosion-allowance" in introduced
    assert "PARAM-outside-diameter" in introduced
    assert "PARAM-minimum-required-thickness" not in introduced
    issues = validate_paragraph_node(meta)
    assert issues == [], f"{path.name}: {issues}"


def test_paragraph_nodes_reject_links_block() -> None:
    issues = validate_paragraph_node(
        {
            "type": "paragraph",
            "key": "test",
            "title": "Test",
            "authority": "AUTH-ASME-B31.3",
            "edition": 2024,
            "paragraph_number": "304.1.2-a",
            "id": "304.1.2-a",
            "text": {"original": "sample"},
            "hierarchy": {"parent": "304.1", "children": []},
            "links": {"equations": ["304.1.2.eq.3a"]},
            "metadata": {
                "source_revision_year": 2024,
                "last_revision": "2026-07-04",
                "edited_by": "admin",
            },
            "edges": [],
        }
    )
    assert any("knowledge nodes must not use links" in issue for issue in issues)


def test_paragraph_nodes_reject_hierarchy_previous_next() -> None:
    issues = validate_paragraph_node(
        {
            "type": "paragraph",
            "key": "test",
            "title": "Test",
            "authority": "AUTH-ASME-B31.3",
            "edition": 2024,
            "paragraph_number": "304.1.2-a",
            "id": "304.1.2-a",
            "text": {"original": "sample"},
            "hierarchy": {"parent": "304.1", "children": [], "previous": "304.1.1-b"},
            "metadata": {
                "source_revision_year": 2024,
                "last_revision": "2026-07-04",
                "edited_by": "admin",
            },
            "edges": [],
        }
    )
    assert any("hierarchy.previous/next" in issue for issue in issues)


def test_paragraph_nodes_reject_structural_edges() -> None:
    issues = validate_paragraph_node(
        {
            "type": "paragraph",
            "key": "test",
            "title": "Test",
            "authority": "AUTH-ASME-B31.3",
            "edition": 2024,
            "paragraph_number": "304.1.2-a",
            "id": "304.1.2-a",
            "text": {"original": "sample"},
            "hierarchy": {"parent": "304.1", "children": []},
            "metadata": {
                "source_revision_year": 2024,
                "last_revision": "2026-07-04",
                "edited_by": "admin",
            },
            "edges": [{"type": "parent", "target": "304.1"}],
        }
    )
    assert any("structural edge type: parent" in issue for issue in issues)


def _paragraph_frontmatter_paths() -> list[Path]:
    return sorted(
        p
        for p in _paragraph_dir().glob("*.yaml")
        if not p.name.endswith(".execution.yaml") and not p.name.endswith(".nomenclature.yaml")
    )


def test_paragraph_nodes_have_required_template_fields() -> None:
    paths = _paragraph_frontmatter_paths()
    assert len(paths) >= 30
    for path in paths:
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        assert meta["type"] == "paragraph"
        assert meta.get("authority") == "AUTH-ASME-B31.3"
        node_id = str(meta.get("id") or path.stem)
        issues = validate_paragraph_node(meta)
        placement = check_paragraph_frontmatter_placement(meta, node_id=node_id)
        placement_fails = [msg for level, msg in placement if level == "FAIL"]
        validator_fail_fields = {
            msg.replace("forbidden field: ", "")
            for msg in issues
            if msg.startswith("forbidden field:")
        }
        placement_fail_fields = {
            msg.split(":")[1].split("(")[0].strip()
            for msg in placement_fails
            if msg.startswith("forbidden field:")
        }
        assert validator_fail_fields == placement_fail_fields, (
            f"{path.name}: validator {issues} vs placement fails {placement_fails}"
        )
        non_forbidden_issues = [i for i in issues if not i.startswith("forbidden field:")]
        assert not non_forbidden_issues, f"{path.name}: {non_forbidden_issues}"


def test_paragraph_parameters_load_from_global_param_nodes() -> None:
    from engine.reference.nomenclature_resolver import load_nomenclature
    from engine.reference.standards_reader import StandardsReader

    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    entries = load_nomenclature(reader, "304.1.1-b")
    assert "c" in entries
    assert entries["c"].input_id == "corrosion_allowance"
    assert entries["D"].input_id == "outside_diameter"


def test_branch_paragraph_without_introduced_parameters_returns_empty_nomenclature() -> None:
    from engine.reference.nomenclature_resolver import load_nomenclature
    from engine.reference.standards_reader import StandardsReader

    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    entries = load_nomenclature(reader, "304.3.3-a")
    assert entries == {}


def test_workflow_sidecar_loads_execution_metadata() -> None:
    from engine.graph.node_interaction import load_node_interactions
    from engine.reference.standards_reader import StandardsReader

    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    record = reader.load("WF-PIPE-WALL-THICKNESS")
    assert record.metadata.get("interactions")
    assert record.metadata.get("navigation")
    specs = load_node_interactions(record, reader)
    variables = {spec.variable for spec in specs}
    assert "pressure_design_case" in variables


def test_b31_3_pack_compiles_paragraph_nodes() -> None:
    from engine.graph.graph_builder import GraphBuilder
    from engine.reference.graph_cache import write_graph_cache

    pack_root = _project_root() / "knowledge" / "standards" / "asme" / "asme_b31.3"
    graph = GraphBuilder(pack_root).build()
    for node_id in (
        "304.1.1-a",
        "304.1.1-b",
        "304.1.2-a",
        "304.1.2-b",
        "302.3.5-e",
        "304.3.3-a",
    ):
        assert node_id in graph.nodes
        assert graph.nodes[node_id].node_type == "paragraph"
    write_graph_cache(pack_root, graph)
