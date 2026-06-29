"""Relationship resolver tests for Phase 3 concept requires."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_store import GraphStore
from engine.graph.relationship_resolver import (
    find_parameter_for_concept,
    resolve_require_binding,
    resolve_require_bindings,
)
from engine.reference.standards_reader import StandardsReader


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "standards", standard="asme_b31.3")


def test_wall_thickness_requires_quantity_concepts() -> None:
    reader = _reader()
    store = GraphStore(reader.pack_root)
    bindings = resolve_require_bindings(
        store,
        store.metadata("B313-eq-wall-thickness").get("requires"),
    )
    by_symbol = {binding.sympy_symbol: binding for binding in bindings}
    assert by_symbol["P"].concept_id == "B313-quantity-pressure"
    assert by_symbol["P"].param_id == "B313-param-P"
    assert by_symbol["D"].concept_id == "B313-quantity-diameter"
    assert by_symbol["S"].concept_id == "B313-quantity-stress"


def test_eq_2_resolves_shared_thickness_quantity_by_alias() -> None:
    reader = _reader()
    store = GraphStore(reader.pack_root)
    bindings = resolve_require_bindings(
        store,
        store.metadata("B313-eq-2").get("requires"),
    )
    assert len(bindings) == 2
    symbols = {binding.sympy_symbol: binding.param_id for binding in bindings}
    assert symbols["t"] == "B313-param-t"
    assert symbols["c"] == "B313-param-c"
    assert bindings[0].concept_id == "B313-quantity-thickness"


def test_external_pressure_section_uses_pressure_quantity_with_pe_alias() -> None:
    reader = _reader()
    store = GraphStore(reader.pack_root)
    binding = resolve_require_binding(
        store,
        store.metadata("B313-304.1.3").get("requires")[0],
    )
    assert binding is not None
    assert binding.concept_id == "B313-quantity-pressure"
    assert binding.sympy_symbol == "Pe"
    assert binding.param_id == "B313-param-P"
    assert binding.metadata.get("role") == "External Pressure"


def test_find_parameter_for_concept_disambiguates_thickness_aliases() -> None:
    reader = _reader()
    store = GraphStore(reader.pack_root)
    assert find_parameter_for_concept(store, "B313-quantity-thickness", alias="t") == "B313-param-t"
    assert find_parameter_for_concept(store, "B313-quantity-thickness", alias="c") == "B313-param-c"
