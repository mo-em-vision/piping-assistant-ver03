"""Standards reader tests."""

from __future__ import annotations

from pathlib import Path

from cli.standards_reader import StandardsReader


def test_load_wall_thickness_node() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "standards", standard="asme_b31.3")
    record = reader.load("B313-304.1.1")

    assert record.node_id == "B313-304.1.1"
    assert record.node_type == "calculation"
    assert "design_pressure" in {item["id"] for item in record.metadata.get("inputs", [])}


def test_validate_reports_missing_dependency_warning() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "standards", standard="asme_b31.3")
    result = reader.validate("B313-304.1.1")

    assert result.passed is True
    assert any("B313-material-stress" in issue.message for issue in result.issues)


def test_dependency_tree_includes_children() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "standards", standard="asme_b31.3")
    tree = reader.dependency_tree("pipe_wall_thickness_design")

    assert tree["id"] == "B313-PIPE-WALL-THICKNESS-DESIGN"
    child_ids = [child["id"] for child in tree.get("children", [])]
    assert "B313-304.1.1" in child_ids
