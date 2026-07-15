"""Strategy executors for v2 lookup_rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.executor.lookup_rule_matching import match_column_value
from engine.executor.lookup_rule_resolvers import (
    RESOLVER_JOINT_CATEGORY_NORMALIZE,
    RESOLVER_MATERIAL_CATALOG,
    RESOLVER_METALLURGICAL_GROUP_KEY,
    RESOLVER_NPS_KEY,
    RESOLVER_SCHEDULE_KEY,
    filter_rows_by_material_group,
    resolve_input_value,
    resolve_material_catalog_key,
    _row_material_token,
)
from engine.executor.lookup_rule_schema import (
    STRATEGY_MATERIAL_CATEGORY,
    STRATEGY_MATERIAL_CATEGORY_TEMPERATURE,
    STRATEGY_MATERIAL_GROUP_TEMPERATURE,
    STRATEGY_MATERIAL_ONLY,
    STRATEGY_MATERIAL_TEMPERATURE,
    STRATEGY_PIPE_NPS,
    STRATEGY_PIPE_NPS_SCHEDULE,
    RuleSpec,
)
from engine.executor.pipe_dimension_lookup import PipeDimensionLookup
from engine.graph.lookup_conditionals import resolve_lookup_input_value
from engine.reference.standards_tables import flatten_lookup_table_rows


def _policy_error(action: str, message: str) -> None:
    if action == "error":
        raise ValueError(message)


def _resolved_inputs(
    spec: RuleSpec,
    inputs: dict[str, Any],
    *,
    table_data: dict[str, Any] | None,
    standards_root: Path | None,
) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for logical_key, input_spec in spec.inputs.items():
        raw = inputs.get(logical_key)
        resolved[logical_key] = resolve_input_value(
            raw,
            resolver=input_spec.resolver,
            logical_key=logical_key,
            inputs=inputs,
            table_data=table_data,
            standards_root=standards_root,
        )
    return resolved


def _temperature_query(
    *,
    value: Any,
    input_spec: Any,
    inputs: dict[str, Any],
    table_data: dict[str, Any],
) -> float:
    unit_key = "design_temperature_unit"
    unit = str(inputs.get(unit_key) or "F")
    param_node = input_spec.parameter
    if param_node:
        return resolve_lookup_input_value(
            float(value),
            input_key="design_temperature",
            input_unit=unit,
            output_param_node_id=param_node,
            table_unit=str(table_data.get("temperature_unit") or "F"),
        )
    from engine.executor.unit_manager import convert_to_si

    converted, _ = convert_to_si(float(value), unit, target_unit=str(table_data.get("temperature_unit") or "F").lower())
    return float(converted)


def _material_rows(table_data: dict[str, Any], material_key: str) -> list[dict[str, Any]]:
    materials = table_data.get("materials", {}) or {}
    rows = materials.get(material_key, {}).get("rows", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _apply_outputs(
    spec: RuleSpec,
    row_values: dict[str, float],
    *,
    returns: list[dict[str, Any]] | None = None,
) -> dict[str, float]:
    outputs: dict[str, float] = {}
    symbol_by_key: dict[str, str] = {}
    if returns:
        for item in returns:
            if not isinstance(item, dict):
                continue
            param_id = str(item.get("parameter") or "").strip()
            symbol = str(item.get("symbol") or "").strip()
            for out_key, out_spec in spec.outputs.items():
                if out_spec.parameter == param_id and symbol:
                    symbol_by_key[out_key] = symbol

    for logical_key, out_spec in spec.outputs.items():
        value = row_values.get(out_spec.column)
        if value is None:
            continue
        outputs[logical_key] = float(value)
        symbol = symbol_by_key.get(logical_key)
        if symbol:
            outputs[symbol] = float(value)
    return outputs


def execute_pipe_nps(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    standards_root: Path,
    table_ref: str,
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    resolved = _resolved_inputs(spec, inputs, table_data=None, standards_root=None)
    nps = resolved["nominal_pipe_size"]
    adapter = PipeDimensionLookup(standards_root)
    try:
        result = adapter.lookup(str(nps))
    except FileNotFoundError as exc:
        raise ValueError(
            "Pipe dimension database is not available. "
            "Run scripts/build_pipe_dimensions_db.py and retry."
        ) from exc

    out_spec = next(iter(spec.outputs.values()))
    column = out_spec.column
    column_values = {
        "outside_diameter_mm": float(result.outside_diameter_mm),
        "outside_diameter_in": float(result.outside_diameter_in),
        "wall_thickness_mm": float(result.wall_thickness_mm) if result.wall_thickness_mm is not None else None,
        "wall_thickness_in": float(result.wall_thickness_in) if result.wall_thickness_in is not None else None,
    }
    value = column_values.get(column)
    if value is None:
        _policy_error(spec.on_no_match, f"Column {column!r} was not resolved from pipe lookup")
    row_values = {column: float(value)}
    meta = {
        "nps": result.nps,
        "table_id": result.table_id or adapter.table_id,
        "standard": result.standard_slug or adapter.standard_slug,
        "table_ref": table_ref,
    }
    return _apply_outputs(spec, row_values, returns=returns), meta


def execute_pipe_nps_schedule(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    standards_root: Path,
    table_ref: str,
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    resolved = _resolved_inputs(spec, inputs, table_data=None, standards_root=None)
    nps = resolved["nominal_pipe_size"]
    schedule = resolved.get("pipe_schedule")
    if not schedule:
        _policy_error(spec.on_no_match, "pipe_schedule is required for pipe dimension lookup")
    adapter = PipeDimensionLookup(standards_root)
    try:
        result = adapter.lookup(str(nps), schedule=str(schedule))
    except FileNotFoundError as exc:
        raise ValueError(
            "Pipe dimension database is not available. "
            "Run scripts/build_pipe_dimensions_db.py and retry."
        ) from exc
    if result.wall_thickness_mm is None:
        _policy_error(
            spec.on_no_match,
            f"Wall thickness for NPS {result.nps!r} schedule {schedule!r} was not found.",
        )

    out_spec = next(iter(spec.outputs.values()))
    row_values = {out_spec.column: float(result.wall_thickness_mm)}
    meta = {
        "nps": result.nps,
        "schedule": result.schedule,
        "table_id": result.table_id or adapter.table_id,
        "standard": result.standard_slug or adapter.standard_slug,
        "table_ref": table_ref,
    }
    return _apply_outputs(spec, row_values, returns=returns), meta


def execute_material_temperature(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    table_data: dict[str, Any],
    standards_root: Path,
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    resolved = _resolved_inputs(spec, inputs, table_data=table_data, standards_root=standards_root)
    material_key = resolved["material_grade"]
    temp_input = spec.inputs["design_temperature"]
    temp_f = _temperature_query(
        value=resolved["design_temperature"],
        input_spec=temp_input,
        inputs=inputs,
        table_data=table_data,
    )
    rows = _material_rows(table_data, str(material_key))
    if not rows:
        _policy_error(spec.on_no_match, f"No rows for material: {material_key!r}")

    out_spec = next(iter(spec.outputs.values()))
    value, matched_row, interpolated = match_column_value(
        rows,
        query_value=temp_f,
        value_column=out_spec.column,
        temp_column=temp_input.column or "design_temperature",
        match=temp_input.match,
    )
    meta = {
        "material": material_key,
        "design_temperature_f": temp_f,
        "interpolated": interpolated,
        "matched_row": matched_row,
    }
    return _apply_outputs(spec, {out_spec.column: float(value)}, returns=returns), meta


def execute_material_group_temperature(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    table_data: dict[str, Any],
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    resolved = _resolved_inputs(spec, inputs, table_data=table_data, standards_root=None)
    group = str(resolved["metallurgical_group"])
    temp_input = spec.inputs["design_temperature"]
    temp_f = _temperature_query(
        value=resolved["design_temperature"],
        input_spec=temp_input,
        inputs=inputs,
        table_data=table_data,
    )
    rows = filter_rows_by_material_group(flatten_lookup_table_rows(table_data), group)
    if not rows:
        _policy_error(spec.on_no_match, f"No rows for material group: {group!r}")

    out_spec = next(iter(spec.outputs.values()))
    value, matched_row, interpolated = match_column_value(
        rows,
        query_value=temp_f,
        value_column=out_spec.column,
        temp_column=temp_input.column or "design_temperature",
        match=temp_input.match,
    )
    meta = {
        "material_group": group,
        "design_temperature_f": temp_f,
        "interpolated": interpolated,
        "matched_row": matched_row,
    }
    return _apply_outputs(spec, {out_spec.column: float(value)}, returns=returns), meta


def execute_material_category(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    table_data: dict[str, Any],
    standards_root: Path,
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    resolved = _resolved_inputs(spec, inputs, table_data=table_data, standards_root=standards_root)
    material_key = str(resolved["material_grade"])
    category = str(resolved["pipe_construction_type"])
    category_input = spec.inputs["pipe_construction_type"]
    category_column = category_input.column or "joint_category"
    out_spec = next(iter(spec.outputs.values()))

    matches = [
        row
        for row in (table_data.get("rows") or [])
        if isinstance(row, dict)
        and _row_material_token(row) == material_key
        and resolve_input_value(
            row.get(category_column),
            resolver=RESOLVER_JOINT_CATEGORY_NORMALIZE,
            logical_key="pipe_construction_type",
            inputs=inputs,
            table_data=table_data,
            standards_root=standards_root,
        )
        == category
    ]
    if len(matches) > 1 and spec.on_multiple_matches == "error":
        _policy_error(
            spec.on_multiple_matches,
            f"Multiple rows for material {material_key!r} and category {category!r}",
        )
    if not matches:
        _policy_error(
            spec.on_no_match,
            f"No row for material {material_key!r} and category {category!r}",
        )
    matched = matches[0]
    raw_value = matched.get(out_spec.column)
    if raw_value is None and out_spec.column == "quality_factor_E":
        raw_value = matched.get("quality_factor_E_c")
    if raw_value is None:
        _policy_error(spec.on_no_match, f"Column {out_spec.column!r} missing for matched row")
    meta = {"material": material_key, "category": category, "matched_row": matched}
    return _apply_outputs(spec, {out_spec.column: float(raw_value)}, returns=returns), meta


def execute_material_category_temperature(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    table_data: dict[str, Any],
    standards_root: Path,
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    resolved = _resolved_inputs(spec, inputs, table_data=table_data, standards_root=standards_root)
    material_key = str(resolved["material_grade"])
    category = str(resolved["pipe_construction_type"])
    category_input = spec.inputs["pipe_construction_type"]
    category_column = category_input.column or "weld_joint_category"
    temp_input = spec.inputs["design_temperature"]
    temp_f = _temperature_query(
        value=resolved["design_temperature"],
        input_spec=temp_input,
        inputs=inputs,
        table_data=table_data,
    )
    out_spec = next(iter(spec.outputs.values()))

    rows = [
        row
        for row in (table_data.get("rows") or [])
        if isinstance(row, dict)
        and _row_material_token(row) == material_key
        and str(row.get(category_column, "")).strip().lower().replace("-", "_")
        == str(category).strip().lower().replace("-", "_")
    ]
    if not rows:
        _policy_error(
            spec.on_no_match,
            f"No rows for material {material_key!r} and category {category!r}",
        )

    value, matched_row, interpolated = match_column_value(
        rows,
        query_value=temp_f,
        value_column=out_spec.column,
        temp_column=temp_input.column or "design_temperature",
        match=temp_input.match,
    )
    meta = {
        "material": material_key,
        "category": category,
        "design_temperature_f": temp_f,
        "interpolated": interpolated,
        "matched_row": matched_row,
    }
    return _apply_outputs(spec, {out_spec.column: float(value)}, returns=returns), meta


def execute_material_only(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    table_data: dict[str, Any],
    standards_root: Path,
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    resolved = _resolved_inputs(spec, inputs, table_data=table_data, standards_root=standards_root)
    material_key = str(resolved["material_grade"])
    out_spec = next(iter(spec.outputs.values()))
    matches = [
        row
        for row in (table_data.get("rows") or [])
        if isinstance(row, dict) and _row_material_token(row) == material_key
    ]
    if len(matches) > 1 and spec.on_multiple_matches == "error":
        _policy_error(spec.on_multiple_matches, f"Multiple rows for material {material_key!r}")
    if not matches:
        _policy_error(spec.on_no_match, f"No row for material {material_key!r}")
    matched = matches[0]
    raw_value = matched.get(out_spec.column)
    if raw_value is None and out_spec.column == "quality_factor_E_c":
        raw_value = matched.get("quality_factor_E")
    if raw_value is None:
        _policy_error(spec.on_no_match, f"Column {out_spec.column!r} missing for matched row")
    meta = {"material": material_key, "matched_row": matched}
    return _apply_outputs(spec, {out_spec.column: float(raw_value)}, returns=returns), meta


def execute_strategy(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    table_data: dict[str, Any] | None,
    standards_root: Path,
    table_ref: str,
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    strategy = spec.strategy
    if strategy == STRATEGY_PIPE_NPS:
        return execute_pipe_nps(
            spec=spec,
            inputs=inputs,
            standards_root=standards_root,
            table_ref=table_ref,
            returns=returns,
        )
    if strategy == STRATEGY_PIPE_NPS_SCHEDULE:
        return execute_pipe_nps_schedule(
            spec=spec,
            inputs=inputs,
            standards_root=standards_root,
            table_ref=table_ref,
            returns=returns,
        )
    if table_data is None:
        raise ValueError(f"Strategy {strategy!r} requires table data")

    if strategy == STRATEGY_MATERIAL_TEMPERATURE:
        return execute_material_temperature(
            spec=spec,
            inputs=inputs,
            table_data=table_data,
            standards_root=standards_root,
            returns=returns,
        )
    if strategy == STRATEGY_MATERIAL_GROUP_TEMPERATURE:
        return execute_material_group_temperature(
            spec=spec,
            inputs=inputs,
            table_data=table_data,
            returns=returns,
        )
    if strategy == STRATEGY_MATERIAL_CATEGORY:
        return execute_material_category(
            spec=spec,
            inputs=inputs,
            table_data=table_data,
            standards_root=standards_root,
            returns=returns,
        )
    if strategy == STRATEGY_MATERIAL_CATEGORY_TEMPERATURE:
        return execute_material_category_temperature(
            spec=spec,
            inputs=inputs,
            table_data=table_data,
            standards_root=standards_root,
            returns=returns,
        )
    if strategy == STRATEGY_MATERIAL_ONLY:
        return execute_material_only(
            spec=spec,
            inputs=inputs,
            table_data=table_data,
            standards_root=standards_root,
            returns=returns,
        )
    raise ValueError(f"Unsupported lookup strategy: {strategy!r}")
