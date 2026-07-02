"""Tests for ASME B31.3 equation ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.b313_legacy_aliases import build_b313_legacy_aliases
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_reader import StandardsReader
from engine.validation.equation_node_validator import validate_equation_node

_FORBIDDEN_FIELDS = frozenset(
    {
        "runtime_value",
        "fact_value",
        "user_input",
        "execution_id",
        "task_id",
        "calculation_result",
        "selected_for_execution",
        "active_in_context",
        "variables",
        "steps",
        "executor",
        "execution_function",
        "calculation_module",
        "outputs",
        "equation_id",
    }
)

_EXPECTED_EQUATION_IDS = frozenset(
    {
        "asme_b313_304_1_1_eq_2",
        "asme_b313_304_1_2_wall_thickness",
        "asme_b313_mawp_pressure",
        "asme_b313_thick_wall_y",
        "asme_b313_pressure_design_thickness",
        "asme_b313_302_3_5_eq_1a",
        "asme_b313_302_3_5_eq_1b",
        "asme_b313_302_3_5_eq_1c",
        "asme_b313_304_3_3_eq_6",
        "asme_b313_304_3_3_eq_6a",
        "asme_b313_304_3_3_eq_7",
        "asme_b313_304_3_3_eq_8",
    }
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _equation_dir() -> Path:
    return (
        _project_root()
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
        / "nodes"
        / "equation"
    )


def test_equation_nodes_have_required_template_fields() -> None:
    paths = sorted(_equation_dir().glob("asme_b313_*.yaml"))
    assert len(paths) == 12
    ids = {path.stem for path in paths}
    assert ids == _EXPECTED_EQUATION_IDS
    for path in paths:
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        assert meta["type"] == "equation"
        assert str(meta["id"]).startswith("asme_")
        assert validate_equation_node(meta) == [], path.name
        for field in _FORBIDDEN_FIELDS:
            assert field not in meta, f"{path.name} must not contain {field!r} in frontmatter"


def test_equation_sidecars_expose_executor_metadata() -> None:
    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    record = reader.load("asme_b313_304_1_2_wall_thickness")
    assert record.metadata.get("executor") == "calculate_wall_thickness"
    assert record.metadata.get("variables")
    assert record.metadata.get("steps")


def test_legacy_equation_aliases_resolve() -> None:
    aliases = build_b313_legacy_aliases()
    assert aliases["B313-eq-2"] == "asme_b313_304_1_1_eq_2"
    assert aliases["304.1.1-eq-2"] == "asme_b313_304_1_1_eq_2"
    assert aliases["B313-eq-wall-thickness"] == "asme_b313_304_1_2_wall_thickness"
    assert aliases["B313-eq-mawp"] == "asme_b313_mawp_pressure"


def test_paragraph_references_new_equation_ids() -> None:
    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    record = reader.load("304.1.1")
    assert "asme_b313_304_1_1_eq_2" in (record.metadata.get("referenced_equations") or [])
    record_304_1_2 = reader.load("304.1.2")
    refs = set(record_304_1_2.metadata.get("referenced_equations") or [])
    assert "asme_b313_304_1_2_wall_thickness" in refs
