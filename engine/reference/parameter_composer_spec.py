"""Build desktop composer field specs from PARAM nodes and graph interactions."""

from __future__ import annotations

from typing import Any

from engine.reference.parameter_keys import (
    api_parameter_id,
    load_parameter_node_metadata,
    param_node_id_for_input,
)
from engine.reference.parameter_metadata import prepare_parameter_metadata
from engine.reference.standards_reader import StandardsReader
from engine.units.unit_ids import symbol_from_unit_id
from engine.units.unit_registry import get_unit_registry

_DESIGNATION_DIMENSIONS = frozenset({"DIM-material-designation", "DIM-designation"})
_COMPOSER_META_KEYS = frozenset(
    {
        "allowed_units",
        "composer_input",
        "composer_options",
        "canonical_unit",
        "default_value",
        "default",
    }
)


def _merge_param_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    merged = dict(raw)
    nested = raw.get("metadata")
    if isinstance(nested, dict):
        for key in _COMPOSER_META_KEYS:
            if key in nested and key not in merged:
                merged[key] = nested[key]
    return prepare_parameter_metadata(merged)


def _load_param_metadata(
    parameter_id: str,
    *,
    reader: StandardsReader | None,
    param_index: dict[str, str] | None,
) -> dict[str, Any]:
    parameter_id = api_parameter_id(parameter_id)
    param_node_id = (param_index or {}).get(parameter_id)
    if not param_node_id:
        candidate = param_node_id_for_input(parameter_id)
        if load_parameter_node_metadata(candidate) is not None:
            param_node_id = candidate
    if param_node_id and param_node_id.startswith("PARAM-"):
        meta = load_parameter_node_metadata(param_node_id)
        if meta is not None:
            return _merge_param_metadata(meta)
    if param_node_id and reader is not None:
        try:
            return _merge_param_metadata(reader.load(param_node_id).metadata)
        except FileNotFoundError:
            pass
    if param_node_id:
        meta = load_parameter_node_metadata(param_node_id)
        if meta is not None:
            return _merge_param_metadata(meta)
    return None


def _composer_type_from_class(parameter_class: str, dimension: str | None) -> str:
    if parameter_class == "categorical":
        if dimension in _DESIGNATION_DIMENSIONS:
            return "material"
        return "dropdown"
    if parameter_class == "selection":
        return "dropdown"
    if parameter_class in {
        "physical_quantity",
        "geometric_quantity",
        "environmental_condition",
        "factor",
        "coefficient",
        "calculated_quantity",
    }:
        return "number"
    return "text"


def _composer_options_from_meta(meta: dict[str, Any]) -> list[dict[str, str]]:
    raw = meta.get("composer_options")
    if not raw:
        return []
    options: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            value = str(item.get("value", "")).strip()
            if not value:
                continue
            label = str(item.get("label") or value.replace("_", " ").title())
            options.append({"value": value, "label": label})
        else:
            value = str(item).strip()
            if value:
                options.append({"value": value, "label": value.replace("_", " ").title()})
    return options


def _validation_for_metadata(meta: dict[str, Any]) -> dict[str, Any] | None:
    parameter_class = str(meta.get("parameter_class", "")).strip()
    dimension = str(meta.get("dimension") or "").strip()
    if parameter_class in {"factor", "coefficient"}:
        return {"min": 0, "max": 1}
    if dimension == "DIM-temperature":
        return {"min": -273}
    if dimension in {"DIM-pressure", "DIM-length"}:
        return {"min": 0}
    return None


def _unit_symbols_for_metadata(meta: dict[str, Any]) -> tuple[list[str], str]:
    dimension_id = str(meta.get("dimension") or "").strip() or None
    parameter_class = str(meta.get("parameter_class", "")).strip()
    if parameter_class == "categorical" and dimension_id in _DESIGNATION_DIMENSIONS:
        return [], "dimensionless"

    is_designation = parameter_class == "categorical" and dimension_id in _DESIGNATION_DIMENSIONS

    registry = get_unit_registry()
    allowed_ids = registry.allowed_units_for_parameter(
        param_meta=meta,
        quantity_dimension=dimension_id,
        is_designation=is_designation,
    )
    units = [symbol_from_unit_id(unit_id) for unit_id in allowed_ids]
    canonical_unit = str(meta.get("canonical_unit") or "").strip()
    if canonical_unit:
        if canonical_unit.startswith("UNIT-"):
            default_unit = symbol_from_unit_id(canonical_unit)
        else:
            default_unit = canonical_unit
    elif units:
        default_unit = units[0]
    else:
        default_unit = str(meta.get("unit") or "dimensionless")
    return units, default_unit


def build_composer_parameter_spec(
    parameter_id: str,
    *,
    reader: StandardsReader | None = None,
    param_index: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return label/type/units/validation for the workflow composer."""
    parameter_id = api_parameter_id(parameter_id)
    meta = _load_param_metadata(parameter_id, reader=reader, param_index=param_index)
    if meta is None:
        raise KeyError(f"No PARAM node metadata for parameter {parameter_id!r}")

    parameter_class = str(meta.get("parameter_class", "")).strip()
    dimension = str(meta.get("dimension") or "").strip() or None
    units, default_unit = _unit_symbols_for_metadata(meta)
    composer_input = str(meta.get("composer_input") or "").strip()
    spec: dict[str, Any] = {
        "label": str(meta.get("name") or parameter_id.replace("_", " ").title()),
        "type": composer_input or _composer_type_from_class(parameter_class, dimension),
        "units": units,
        "default_unit": default_unit,
    }
    validation = _validation_for_metadata(meta)
    if validation:
        spec["validation"] = validation
    default_value = meta.get("default_value")
    if default_value is None:
        default_value = meta.get("default")
    if default_value is not None:
        spec["default_value"] = default_value
    options = _composer_options_from_meta(meta)
    if options:
        spec["options"] = options
    return spec
