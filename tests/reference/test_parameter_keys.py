"""Tests for canonical parameter key helpers."""

from __future__ import annotations

from pathlib import Path

from engine.reference.parameter_keys import (
    param_node_id_for_input,
    parameter_node_description,
)
from engine.reference.standards_reader import StandardsReader


def test_param_node_id_for_input_resolves_material_legacy_key() -> None:
    assert param_node_id_for_input("material") == "PARAM-material-grade"


def test_param_node_id_for_input_preserves_existing_param_node_id() -> None:
    assert param_node_id_for_input("PARAM-internal-design-gage-pressure") == (
        "PARAM-internal-design-gage-pressure"
    )


def test_parameter_node_description_reads_param_yaml_description() -> None:
    text = parameter_node_description(input_id="internal_design_gage_pressure")
    assert text == "internal design gage pressure"


def test_parameter_node_description_resolves_legacy_design_pressure_key() -> None:
    text = parameter_node_description(input_id="design_pressure")
    assert text == "internal design gage pressure"


def test_parameter_node_description_prefers_yaml_over_stale_reader_cache(
    project_root: Path,
) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards")
    text = parameter_node_description(
        reader=reader,
        param_id="PARAM-required-wall-thickness",
    )
    assert text == "pressure design thickness"
