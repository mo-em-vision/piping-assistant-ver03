"""Strategy executors for v2 lookup_rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.executor.lookup_rule_schema import (
    STRATEGY_MATERIAL_CATEGORY,
    STRATEGY_MATERIAL_CATEGORY_TEMPERATURE,
    STRATEGY_MATERIAL_GROUP_TEMPERATURE,
    STRATEGY_EXAMINATION_COMBINATION,
    STRATEGY_MATERIAL_CATALOG,
    STRATEGY_MATERIAL_ONLY,
    STRATEGY_MATERIAL_TEMPERATURE,
    STRATEGY_PIPE_NPS,
    STRATEGY_PIPE_NPS_SCHEDULE,
    RuleSpec,
    rule_output_column_policies,
)
from engine.executor.table_resolver import (
    RowResolutionPolicy,
    resolution_result_to_meta,
    resolve_table_rows,
)
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
from engine.executor.pipe_dimension_lookup import PipeDimensionLookup
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
    inputs: dict[str, Any],
    table_data: dict[str, Any],
    axis_policy: RowResolutionPolicy | None,
) -> float:
    unit_key = "design_temperature_unit"
    unit = str(inputs.get(unit_key) or "F")
    table_unit = str(
        table_data.get("temperature_unit")
        or (axis_policy.unit if axis_policy else None)
        or "F"
    )
    from engine.executor.unit_manager import convert_to_si

    converted, _ = convert_to_si(float(value), unit, target_unit=table_unit.lower())
    temp = float(converted)
    if axis_policy is None:
        return temp
    if axis_policy.min_bound is not None and temp < axis_policy.min_bound:
        if axis_policy.outside_range == "clamp_to_boundary":
            return float(axis_policy.min_bound)
    if axis_policy.max_bound is not None and temp > axis_policy.max_bound:
        if axis_policy.outside_range == "clamp_to_boundary":
            return float(axis_policy.max_bound)
    return temp


def _resolve_temperature_rows(
    *,
    spec: RuleSpec,
    rows: list[dict[str, Any]],
    temp_f: float,
    axis_key: str = "design_temperature",
    extra_meta: dict[str, Any] | None = None,
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    temp_input = spec.inputs[axis_key]
    axis_policy = spec.row_resolution.get(axis_key)
    if axis_policy is None:
        axis_policy = RowResolutionPolicy(
            breakpoint_column=temp_input.column or "design_temperature",
            method="exact",
        )
    breakpoint_column = axis_policy.breakpoint_column or temp_input.column or "design_temperature"
    output_columns = rule_output_column_policies(spec, axis_key)
    result = resolve_table_rows(
        rows,
        breakpoint_column=breakpoint_column,
        output_columns=output_columns,
        query_value=temp_f,
        policy=axis_policy,
    )
    meta = resolution_result_to_meta(result, policy=axis_policy)
    if extra_meta:
        meta.update(extra_meta)
    meta["design_temperature_f"] = temp_f
    return _apply_outputs(spec, result.values, returns=returns), meta


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
    axis_policy = spec.row_resolution.get("design_temperature")
    temp_f = _temperature_query(
        value=resolved["design_temperature"],
        inputs=inputs,
        table_data=table_data,
        axis_policy=axis_policy,
    )
    rows = _material_rows(table_data, str(material_key))
    if not rows:
        _policy_error(spec.on_no_match, f"No rows for material: {material_key!r}")

    return _resolve_temperature_rows(
        spec=spec,
        rows=rows,
        temp_f=temp_f,
        extra_meta={"material": material_key},
        returns=returns,
    )


def execute_material_group_temperature(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    table_data: dict[str, Any],
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    resolved = _resolved_inputs(spec, inputs, table_data=table_data, standards_root=None)
    group = str(resolved["metallurgical_group"])
    axis_policy = spec.row_resolution.get("design_temperature")
    temp_f = _temperature_query(
        value=resolved["design_temperature"],
        inputs=inputs,
        table_data=table_data,
        axis_policy=axis_policy,
    )
    rows = filter_rows_by_material_group(flatten_lookup_table_rows(table_data), group)
    if not rows:
        _policy_error(spec.on_no_match, f"No rows for material group: {group!r}")

    return _resolve_temperature_rows(
        spec=spec,
        rows=rows,
        temp_f=temp_f,
        extra_meta={"material_group": group},
        returns=returns,
    )


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
    axis_policy = spec.row_resolution.get("design_temperature")
    temp_f = _temperature_query(
        value=resolved["design_temperature"],
        inputs=inputs,
        table_data=table_data,
        axis_policy=axis_policy,
    )

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

    return _resolve_temperature_rows(
        spec=spec,
        rows=rows,
        temp_f=temp_f,
        extra_meta={"material": material_key, "category": category},
        returns=returns,
    )


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


def execute_material_catalog(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    table_data: dict[str, Any],
    standards_root: Path,
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    resolved = _resolved_inputs(spec, inputs, table_data=table_data, standards_root=standards_root)
    material_key = str(resolved["material_grade"])
    materials = table_data.get("materials", {}) or {}
    row = materials.get(material_key)
    if row is None:
        try:
            resolved_key = resolve_material_catalog_key(
                material_key,
                table_data=table_data,
                standards_root=standards_root,
            )
            row = materials.get(resolved_key)
            material_key = resolved_key
        except ValueError:
            row = None
    if row is None:
        _policy_error(spec.on_no_match, f"Material grade not found in catalog: {resolved['material_grade']!r}")

    out_spec = next(iter(spec.outputs.values()))
    material_id = str(row.get("material_id", material_key))
    density = (row.get("physical_properties") or {}).get("density_kg_m3")
    numeric_value = float(density) if density is not None else 1.0
    meta = {"material_id": material_id, "matched_row": row}
    return _apply_outputs(spec, {out_spec.column: numeric_value}, returns=returns), meta


def execute_examination_combination(
    *,
    spec: RuleSpec,
    inputs: dict[str, Any],
    table_data: dict[str, Any],
    returns: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    resolved = _resolved_inputs(spec, inputs, table_data=table_data, standards_root=None)
    logical_key = "supplementary_examination"
    input_spec = spec.inputs[logical_key]
    query = str(resolved[logical_key]).strip()
    column = input_spec.column or logical_key
    out_spec = next(iter(spec.outputs.values()))

    matches = [
        row
        for row in flatten_lookup_table_rows(table_data)
        if isinstance(row, dict) and str(row.get(column, "")).strip() == query
    ]
    if len(matches) > 1 and spec.on_multiple_matches == "error":
        _policy_error(
            spec.on_multiple_matches,
            f"Multiple rows for {logical_key}={query!r}",
        )
    if not matches:
        _policy_error(spec.on_no_match, f"No row for {logical_key}={query!r}")
    matched = matches[0]
    raw_value = matched.get(out_spec.column)
    if raw_value is None:
        _policy_error(spec.on_no_match, f"Column {out_spec.column!r} missing for matched row")
    meta = {logical_key: query, "matched_row": matched}
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
    if strategy == STRATEGY_EXAMINATION_COMBINATION:
        return execute_examination_combination(
            spec=spec,
            inputs=inputs,
            table_data=table_data,
            returns=returns,
        )
    if strategy == STRATEGY_MATERIAL_CATALOG:
        return execute_material_catalog(
            spec=spec,
            inputs=inputs,
            table_data=table_data,
            standards_root=standards_root,
            returns=returns,
        )
    raise ValueError(f"Unsupported lookup strategy: {strategy!r}")
