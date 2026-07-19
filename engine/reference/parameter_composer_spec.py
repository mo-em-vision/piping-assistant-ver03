"""Build desktop composer field specs from PARAM nodes and graph interactions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.graph.resolution_branches import (
    active_resolution_branch_id,
    default_resolution_branch_id,
    resolution_branch_fact_key,
    resolution_branches_from_metadata,
    via_parameter_keys,
)
from engine.reference.parameter_keys import (
    api_parameter_id,
    load_parameter_node_metadata,
    param_node_id_for_input,
)
from engine.reference.parameter_metadata import prepare_parameter_metadata
from engine.reference.standards_reader import StandardsReader
from engine.reference.table_options_resolver import resolve_table_dropdown_options
from engine.units.unit_ids import symbol_from_unit_id
from engine.units.unit_registry import get_unit_registry
from models.task import Task

_DESIGNATION_DIMENSIONS = frozenset({"DIM-material-designation", "DIM-designation"})
_COMPOSER_META_KEYS = frozenset(
    {
        "allowed_units",
        "composer_input",
        "composer_options",
        "table_options",
        "canonical_unit",
        "default_value",
        "default",
        "resolution_branches",
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


def _branch_composer_spec(
    branch: dict[str, Any],
    *,
    reader: StandardsReader | None,
    param_index: dict[str, str] | None,
    task: Task | None,
    standards_root: Path | None,
) -> dict[str, Any]:
    method = str(branch.get("method") or "").strip()
    value_composer = str(branch.get("value_composer") or "number").strip()
    if method == "user_input":
        units, default_unit = _unit_symbols_for_metadata(
            {"parameter_class": "geometric_quantity", "dimension": "DIM-length"}
        )
        return {
            "type": value_composer,
            "units": units,
            "default_unit": default_unit,
            "validation": {"min": 0},
        }

    via_keys = []
    for raw in branch.get("via_parameters") or []:
        text = str(raw or "").strip()
        if text.startswith("PARAM-"):
            from engine.reference.workflow_sidecar import _PARAM_TO_FIELD

            mapped = _PARAM_TO_FIELD.get(text)
            if mapped:
                via_keys.append(mapped)
                continue
        via_keys.append(api_parameter_id(text.replace("PARAM-", "").replace("-", "_")))

    submit_parameter = via_keys[0] if via_keys else None
    options: list[dict[str, str]] = []
    if submit_parameter and task is not None and standards_root is not None:
        options = resolve_table_dropdown_options(
            task,
            submit_parameter,
            standards_root=standards_root,
        )
    elif submit_parameter and reader is not None:
        via_meta = _load_param_metadata(submit_parameter, reader=reader, param_index=param_index)
        if via_meta is not None:
            options = _composer_options_from_meta(via_meta)
    return {
        "type": "dropdown",
        "units": [],
        "default_unit": "dimensionless",
        "options": options,
        "submit_parameter": submit_parameter,
    }


def build_resolution_ui(
    meta: dict[str, Any],
    *,
    task: Task | None = None,
    reader: StandardsReader | None = None,
    param_index: dict[str, str] | None = None,
    standards_root: Path | None = None,
) -> dict[str, Any]:
    param_key = str(meta.get("key") or "").strip()
    active_branch = None
    if task is not None:
        active_branch = active_resolution_branch_id(param_key, task.fact_store.active_facts())
    branches: list[dict[str, Any]] = []
    for branch in resolution_branches_from_metadata(meta):
        branch_id = str(branch.get("id") or "").strip()
        if not branch_id:
            continue
        composer = _branch_composer_spec(
            branch,
            reader=reader,
            param_index=param_index,
            task=task,
            standards_root=standards_root,
        )
        branches.append(
            {
                "id": branch_id,
                "label": str(branch.get("label") or branch_id.replace("_", " ").title()),
                "help_text": (
                    str(branch.get("help_text") or "").strip() or None
                ),
                "composer": composer,
                "submit_parameter": composer.get("submit_parameter"),
            }
        )
    nested = meta.get("metadata")
    block = nested if isinstance(nested, dict) else meta
    return {
        "branches": branches,
        "active_branch": active_branch,
        "default_value": default_resolution_branch_id(meta),
        "branch_fact_key": resolution_branch_fact_key(param_key),
        "question": str(block.get("resolution_branch_question") or "").strip() or None,
        "help_text": (
            str(block.get("resolution_branch_help_text") or "").strip() or None
        ),
    }


def build_composer_parameter_spec(
    parameter_id: str,
    *,
    reader: StandardsReader | None = None,
    param_index: dict[str, str] | None = None,
    task: Task | None = None,
    standards_root: Path | None = None,
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

    if spec["type"] == "resolution_branch":
        spec["resolution_ui"] = build_resolution_ui(
            meta,
            task=task,
            reader=reader,
            param_index=param_index,
            standards_root=standards_root,
        )
        return spec

    table_options = meta.get("table_options")
    has_table_options = isinstance(table_options, dict) and bool(
        str(table_options.get("query") or "").strip()
    )
    if not has_table_options:
        options = _composer_options_from_meta(meta)
        if options:
            spec["options"] = options
    return spec
