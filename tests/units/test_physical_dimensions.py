"""Tests for global physical dimension ontology nodes."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.graph_edge_schema import dimension_allowed_unit_ids
from engine.reference.standards_markdown import split_frontmatter
from engine.validation.dimension_node_validator import validate_dimension_node


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _unit_ids() -> set[str]:
    units_dir = _project_root() / "knowledge" / "global" / "units" / "nodes"
    return {path.stem for path in units_dir.glob("UNIT-*.yaml")}


def test_physical_dimension_nodes_reference_existing_units() -> None:
    dims_dir = _project_root() / "knowledge" / "global" / "dimensions" / "nodes"
    unit_ids = _unit_ids()
    for path in sorted(dims_dir.glob("DIM-*.yaml")):
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        issues = validate_dimension_node(meta, known_unit_ids=unit_ids)
        assert issues == [], f"{path.name}: {issues}"
        kind = str(meta.get("dimension_kind", "")).strip()
        if kind == "categorical":
            assert meta.get("canonical_unit") in {None, "null"}
            assert dimension_allowed_unit_ids(meta) == []
            continue
        canonical = str(meta.get("canonical_unit") or "").strip()
        allowed = dimension_allowed_unit_ids(meta)
        assert canonical in allowed, f"{path.name} canonical_unit must be in allows_unit edges"


def test_velocity_units_compile_and_convert() -> None:
    from engine.units.unit_resolver import UnitResolver, reset_unit_resolver

    reset_unit_resolver()
    resolver = UnitResolver.default()
    value, unit = resolver.convert_value(1.0, "ft/s", "m/s")
    assert unit == "m/s"
    assert value == pytest.approx(0.3048)
