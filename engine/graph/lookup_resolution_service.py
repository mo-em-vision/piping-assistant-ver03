"""Graph-driven lookup resolution: execute table rules and store derived Facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.executor.lookup_engine import LookupEngine
from engine.executor.lookup_rule_schema import lookup_bindings
from engine.graph.lookup_parameter_resolution import _lookup_keys_from_metadata, _resolve_lookup_key, _table_id_from_metadata
from engine.reference.nps_normalization import nps_entry_unit, to_nps_lookup_key
from engine.reference.standards_paths import resolve_standard_pack
from engine.state.task_facts import (
    active_facts,
    fact_scalar_value,
    store_lookup_categorical_fact,
    store_lookup_numeric_fact,
)
from models.fact import Fact, SourceType, fact_scalar_value as scalar
from models.task import Task

B36_10_TABLE_REF = "asme_b36.10/table-2-1"
OUTSIDE_DIAMETER_LOOKUP_NODE = "asme-b3610-nps-outside-diameter-lookup"
WALL_THICKNESS_LOOKUP_NODE = "asme-b3610-pipe-dimensions-lookup"

_PARAM_OUTPUT_SYMBOLS: dict[str, str] = {
    "outside_diameter": "D",
    "actual_wall_thickness": "t_actual",
}


@dataclass
class LookupResolutionResult:
    lookup_node_id: str
    table_ref: str
    rule: str
    outputs: dict[str, float] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    stored_keys: list[str] = field(default_factory=list)


def _lookup_engine_for_standards(standards_root: Path) -> LookupEngine:
    pack_root = resolve_standard_pack(standards_root, "asme_b31.3")
    return LookupEngine(pack_root)


def _load_lookup_metadata(reader: Any, lookup_node_id: str) -> dict[str, Any]:
    node = reader.load(lookup_node_id)
    metadata = dict(node.metadata or {})
    if not lookup_bindings(metadata):
        path = reader.find_node_path(lookup_node_id)
        if path is not None and path.is_file():
            fresh = reader.load_file(path)
            metadata = dict(fresh.metadata or {})
    return metadata


def _lookup_config(metadata: dict[str, Any]) -> dict[str, Any]:
    lookup_block = metadata.get("lookup")
    if isinstance(lookup_block, dict):
        return dict(lookup_block)
    lookups = metadata.get("lookups") or []
    if lookups and isinstance(lookups[0], dict):
        return dict(lookups[0])
    return {}


def _return_specs(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    returns = metadata.get("returns") or []
    return [item for item in returns if isinstance(item, dict)]


def _param_key_from_return(item: dict[str, Any]) -> str:
    param_id = str(item.get("parameter") or "").strip()
    if param_id.startswith("PARAM-"):
        from engine.reference.workflow_sidecar import _PARAM_TO_FIELD

        mapped = _PARAM_TO_FIELD.get(param_id)
        if mapped:
            return mapped
        slug = param_id.removeprefix("PARAM-").replace("-", "_")
        return slug
    return str(item.get("symbol") or "").strip()


def _build_engine_inputs_from_bindings(
    task: Task,
    metadata: dict[str, Any],
    *,
    store: Any,
) -> dict[str, Any]:
    bindings = lookup_bindings(metadata)
    if not bindings:
        raise ValueError("lookup.bindings is required for table lookup resolution")

    inputs: dict[str, Any] = {}
    facts = active_facts(task)
    for logical_key, param_ref in bindings.items():
        fact_key = _resolve_lookup_key(store, param_ref)
        fact = facts.get(fact_key)
        if fact is None:
            continue
        value = fact_scalar_value(fact)
        if value is None:
            continue
        inputs[logical_key] = value
        if logical_key == "nominal_pipe_size":
            inputs["nominal_pipe_size_unit"] = nps_entry_unit(fact)
        elif logical_key == "design_temperature":
            inputs["design_temperature_unit"] = str(fact.unit or "F")
    return inputs


def _build_engine_inputs(task: Task, required_keys: list[str]) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    facts = active_facts(task)
    for key in required_keys:
        fact = facts.get(key)
        if fact is None:
            continue
        value = fact_scalar_value(fact)
        if value is None:
            continue
        inputs[key] = value
        if key == "nominal_pipe_size":
            inputs["nominal_pipe_size_unit"] = nps_entry_unit(fact)
    return inputs


def _row_identity(meta: dict[str, Any]) -> str:
    nps = str(meta.get("nps") or "")
    schedule = str(meta.get("schedule") or "")
    if schedule:
        return f"{nps}|{schedule}"
    return nps


def _facts_match_lookup(
    task: Task,
    *,
    param_key: str,
    expected_amount: float,
    lookup_node_id: str,
    row_identity: str,
) -> bool:
    fact = task.fact_store.active_fact(param_key)
    if fact is None:
        return False
    if fact.source.source_type != SourceType.TABLE_LOOKUP:
        return False
    if fact.source.lookup_node and fact.source.lookup_node != lookup_node_id:
        return False
    stored_row = str(fact.metadata.get("lookup_row_identity") or "")
    if stored_row and row_identity and stored_row != row_identity:
        return False
    current = scalar(fact)
    if current is None:
        return False
    try:
        return abs(float(current) - float(expected_amount)) < 1e-6
    except (TypeError, ValueError):
        return False


def _store_lookup_output(
    task: Task,
    *,
    param_key: str,
    amount: float,
    unit: str,
    lookup_node_id: str,
    table_ref: str,
    rule: str,
    meta: dict[str, Any],
    symbol: str | None = None,
    description: str | None = None,
    input_fact_keys: list[str] | None = None,
) -> None:
    from engine.state.task_facts import store_lookup_numeric_fact

    store_lookup_numeric_fact(
        task,
        key=param_key,
        amount=amount,
        unit=unit,
        table_ref=table_ref,
        symbol=symbol,
        description=description,
        lookup_node=lookup_node_id,
        lookup_rule=rule,
        input_facts=input_fact_keys or [],
        lookup_row_identity=_row_identity(meta),
        authority_id="AUTH-ASME-B36.10M",
    )


def _write_legacy_od_output(task: Task, meta: dict[str, Any], outside_diameter_mm: float) -> None:
    task.outputs["outside_diameter_lookup"] = {
        "standard": meta.get("standard"),
        "table_id": meta.get("table_id"),
        "lookup_node_id": OUTSIDE_DIAMETER_LOOKUP_NODE,
        "rule": meta.get("rule"),
        "nps": meta.get("nps"),
        "outside_diameter_in": meta.get("outside_diameter_in"),
        "outside_diameter_mm": float(outside_diameter_mm),
        "row_identity": _row_identity(meta),
    }


def resolve_and_store_lookup(
    task: Task,
    *,
    lookup_node_id: str,
    standards_root: Path,
    reader: Any | None = None,
    target_parameters: list[str] | None = None,
) -> LookupResolutionResult:
    """Execute a graph lookup node and store returned parameter Facts."""
    if reader is None:
        from engine.reference.standards_reader import StandardsReader

        reader = StandardsReader(standards_root, standard="asme_b31.3")

    metadata = _load_lookup_metadata(reader, lookup_node_id)
    lookup_cfg = _lookup_config(metadata)
    table_ref = str(
        lookup_cfg.get("table")
        or lookup_cfg.get("table_id")
        or _table_id_from_metadata(metadata)
        or "B3610-table-2-1"
    ).strip()
    rule = str(lookup_cfg.get("rule") or "").strip()
    if not rule:
        raise ValueError(f"Lookup node {lookup_node_id!r} has no lookup rule.")

    required_keys = _lookup_keys_from_metadata(reader.graph_store, metadata)
    engine_inputs = _build_engine_inputs_from_bindings(
        task,
        metadata,
        store=reader.graph_store,
    )
    if not engine_inputs:
        engine_inputs = _build_engine_inputs(task, required_keys)
    if "nominal_pipe_size" in engine_inputs:
        raw_nps = str(engine_inputs["nominal_pipe_size"])
        entry_unit = str(engine_inputs.get("nominal_pipe_size_unit") or "NPS")
        engine_inputs["nominal_pipe_size"] = to_nps_lookup_key(raw_nps, entry_unit)
        engine_inputs["nominal_pipe_size_unit"] = entry_unit

    engine = _lookup_engine_for_standards(standards_root)
    try:
        rule_result = engine.execute_rule_lookup(
            table_ref=table_ref,
            rule=rule,
            inputs=engine_inputs,
            returns=_return_specs(metadata),
        )
    except FileNotFoundError as exc:
        raise ValueError(
            "Pipe dimension database is not available. "
            "Run scripts/build_pipe_dimensions_db.py and retry."
        ) from exc

    return_specs = _return_specs(metadata)
    targets = target_parameters or [_param_key_from_return(item) for item in return_specs]
    stored: list[str] = []
    input_fact_keys = [key for key in required_keys if task.fact_store.active_fact(key) is not None]

    for item in return_specs:
        param_key = _param_key_from_return(item)
        if param_key not in targets:
            continue
        amount = rule_result.outputs.get(param_key)
        if amount is None:
            continue
        row_id = _row_identity(rule_result.meta)
        if _facts_match_lookup(
            task,
            param_key=param_key,
            expected_amount=float(amount),
            lookup_node_id=lookup_node_id,
            row_identity=row_id,
        ):
            stored.append(param_key)
            if param_key == "outside_diameter":
                _write_legacy_od_output(task, rule_result.meta, float(amount))
            continue

        symbol = str(item.get("symbol") or _PARAM_OUTPUT_SYMBOLS.get(param_key) or "").strip() or None
        unit = "mm" if param_key in {"outside_diameter", "actual_wall_thickness"} else "dimensionless"
        _store_lookup_output(
            task,
            param_key=param_key,
            amount=float(amount),
            unit=unit,
            lookup_node_id=lookup_node_id,
            table_ref=table_ref,
            rule=rule,
            meta=rule_result.meta,
            symbol=symbol,
            description=f"From {lookup_node_id}",
            input_fact_keys=input_fact_keys,
        )
        stored.append(param_key)

        if param_key == "outside_diameter":
            nps_fact = task.fact_store.active_fact("nominal_pipe_size")
            if nps_fact is not None:
                resolved_nps = str(rule_result.meta.get("nps") or fact_scalar_value(nps_fact))
                store_lookup_categorical_fact(
                    task,
                    key="nominal_pipe_size",
                    label=resolved_nps,
                    table_ref=B36_10_TABLE_REF,
                    original_value=nps_fact.original_value or fact_scalar_value(nps_fact),
                    lookup_node=lookup_node_id,
                    lookup_rule=rule,
                )
            _write_legacy_od_output(task, rule_result.meta, float(amount))

    from engine.state.goal_satisfaction import refresh_goal_satisfaction

    refresh_goal_satisfaction(task)

    return LookupResolutionResult(
        lookup_node_id=lookup_node_id,
        table_ref=table_ref,
        rule=rule,
        outputs=dict(rule_result.outputs),
        meta=dict(rule_result.meta),
        stored_keys=stored,
    )


def resolve_outside_diameter_from_nps(task: Task, standards_root: Path) -> LookupResolutionResult | None:
    """Resolve OD via the graph OD lookup node when NPS is confirmed."""
    from engine.graph.resolution_branches import (
        active_resolution_branch_id,
        resolution_branch_fact_key,
    )
    from engine.state.task_facts import store_system_categorical_fact

    if active_resolution_branch_id("outside_diameter", active_facts(task)) == "direct_od":
        return None

    nps_input = task.fact_store.active_fact("nominal_pipe_size")
    if nps_input is None or fact_scalar_value(nps_input) is None:
        return None

    branch_key = resolution_branch_fact_key("outside_diameter")
    if active_resolution_branch_id("outside_diameter", active_facts(task)) != "direct_od":
        store_system_categorical_fact(task, key=branch_key, label="nps_lookup")

    return resolve_and_store_lookup(
        task,
        lookup_node_id=OUTSIDE_DIAMETER_LOOKUP_NODE,
        standards_root=standards_root,
        target_parameters=["outside_diameter"],
    )


def resolve_wall_thickness_from_nps_schedule(
    task: Task,
    standards_root: Path,
) -> LookupResolutionResult:
    """Resolve nominal wall thickness via the graph NPS+schedule lookup node."""
    return resolve_and_store_lookup(
        task,
        lookup_node_id=WALL_THICKNESS_LOOKUP_NODE,
        standards_root=standards_root,
        target_parameters=["actual_wall_thickness"],
    )


def lookup_node_metadata(
    reader: Any,
    lookup_node_id: str,
) -> tuple[str, str, list[str]]:
    """Return table_ref, rule, and required input keys for a lookup node."""
    metadata = _load_lookup_metadata(reader, lookup_node_id)
    lookup_cfg = _lookup_config(metadata)
    table_ref = str(
        lookup_cfg.get("table")
        or lookup_cfg.get("table_id")
        or _table_id_from_metadata(metadata)
        or ""
    ).strip()
    rule = str(lookup_cfg.get("rule") or "").strip()
    keys = _lookup_keys_from_metadata(reader.graph_store, metadata)
    return table_ref, rule, keys
