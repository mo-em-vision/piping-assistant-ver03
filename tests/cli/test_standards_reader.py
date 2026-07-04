"""Standards reader tests."""

from __future__ import annotations

from pathlib import Path

from cli.standards_reader import StandardsReader


def test_load_wall_thickness_node() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    record = reader.load("304.1.2-a")

    assert record.node_id == "304.1.2-a"
    assert record.node_type == "calculation"
    assert "design_pressure" in {item["id"] for item in record.metadata.get("inputs", [])}


def test_validate_resolves_material_stress_dependency() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    result = reader.validate("304.1.2-a")

    assert result.passed is True
    assert not any("asme-b313-table-A-1" in issue.message for issue in result.issues)
    assert reader.find_node_path("asme-b313-table-A-1") is not None


def test_dependency_tree_includes_children() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    tree = reader.dependency_tree("pipe_wall_thickness_design")

    assert tree["id"] == "B313-PIPE-WALL-THICKNESS-DESIGN"
    child_ids = [child["id"] for child in tree.get("children", [])]
    assert "B313-304.1.1" in child_ids
    nom_node = next(child for child in tree["children"] if child["id"] == "B313-304.1.1")
    nom_child_ids = [child["id"] for child in nom_node.get("children", [])]
    assert "304.1.2-a" in nom_child_ids
    assert "B313-304.1.3" in nom_child_ids


def test_load_subsection_returns_only_requested_302_3_5_section() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")

    subsection = reader.load_subsection("302.3.5-e", "e")

    assert subsection.node_id == "302.3.5-e"
    assert subsection.subsection_id == "e"
    assert subsection.paragraph == "302.3.5-e"
    assert subsection.metadata["output"]["symbol"] == "W"
    assert "Unlisted Weld Strength Reduction Factors" not in subsection.body
