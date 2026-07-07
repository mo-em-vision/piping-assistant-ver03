"""Tests for equation display variable resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.formula_display import (
    _resolve_equation_node_id,
    load_equation_context,
    resolve_equation_display_variables,
)
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_resolve_wall_thickness_variables_for_304_1_2(
    standards_reader: StandardsReader,
) -> None:
    resolved = resolve_equation_display_variables(
        standards_reader, "asme-b313-304-1-2-eq-3a"
    )
    variables = resolved["variables"]
    by_symbol = {row["symbol"]: row["name"] for row in variables}

    assert by_symbol["P"] == "Internal design gage pressure"
    assert by_symbol["P"] != "P"
    assert by_symbol["D"] == "Outside diameter of pipe"
    assert by_symbol["S"] == "Stress value from Table A-1"
    assert len(variables) >= 6

    nomenclature_reference = resolved["nomenclature_reference"]
    assert nomenclature_reference is not None
    assert nomenclature_reference["node_id"] in {"304.1.1-b", "B313-304.1.1"}
    assert nomenclature_reference["label"] == "§304.1.1-b"


def test_resolve_equation_node_from_paragraph_references_equation(
    standards_reader: StandardsReader,
) -> None:
    resolved = _resolve_equation_node_id(standards_reader, "304.1.2-a", task_facts={})
    assert resolved == "asme-b313-304-1-2-eq-3a"

    context = load_equation_context(standards_reader, "304.1.2-a", task_facts={})
    assert context["display"] == "t = PD / 2(SEW + PY)"
