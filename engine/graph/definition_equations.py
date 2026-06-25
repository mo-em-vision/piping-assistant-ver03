"""Track and evaluate definition-node equations after calculation nodes complete."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from engine.executor.functions import get_execution_function
from engine.executor.unit_manager import prepare_engineering_input
from engine.reference.standards_reader import StandardsReader
from models.input import EngineeringInput, InputStatus, input_is_expansion_ready
from models.task import Task, TaskStatus

_OUTPUT_SYMBOL_KEYS: dict[str, tuple[str, ...]] = {
    "t": ("t", "required_thickness"),
    "t_m": ("t_m", "minimum_required_thickness"),
    "S": ("S", "allowable_stress"),
}


@dataclass(frozen=True)
class DefinitionEquationSpec:
    node_id: str
    equation_id: str
    function_name: str
    node_dir: Path
    variables: tuple[str, ...]
    output_keys: tuple[str, ...]


def has_execution_trace(task: Task) -> bool:
    trace = task.outputs.get("_execution_trace")
    return isinstance(trace, list) and bool(trace)


def definition_equation_outputs_complete(task: Task, specs: list[DefinitionEquationSpec]) -> bool:
    if not specs:
        return True
    for spec in specs:
        if not any(task.outputs.get(key) is not None for key in spec.output_keys):
            return False
    return True


def pending_definition_equation_inputs(
    task: Task,
    reader: StandardsReader,
    execution_order: tuple[str, ...] | list[str],
) -> list[str]:
    """Return user input ids still required to finish definition-node equations."""
    if not has_execution_trace(task):
        return []

    missing: list[str] = []
    seen: set[str] = set()
    for spec in _definition_equation_specs(reader, execution_order):
        if _equation_outputs_satisfied(task, spec):
            continue
        for input_id in _missing_user_inputs_for_equation(task, reader, spec):
            if input_id not in seen:
                seen.add(input_id)
                missing.append(input_id)
    return missing


def try_complete_definition_equations(
    task: Task,
    reader: StandardsReader,
    execution_order: tuple[str, ...] | list[str],
) -> bool:
    """Evaluate pending definition equations when inputs and node outputs are ready."""
    if not has_execution_trace(task):
        return False

    changed = False
    for spec in _definition_equation_specs(reader, execution_order):
        if _equation_outputs_satisfied(task, spec):
            continue
        variables, unresolved = _resolve_equation_variables(task, reader, spec)
        if unresolved:
            continue
        fn = get_execution_function(spec.function_name)
        if fn is None:
            continue
        try:
            calculation = fn(node_dir=spec.node_dir, variables=variables)
        except Exception:  # noqa: BLE001
            continue
        final = calculation.final_result
        if final is None or final.value is None:
            continue
        value = float(final.value)
        unit = str(final.unit or "mm")
        for key in spec.output_keys:
            task.outputs[key] = value
            task.outputs[f"{key}_unit"] = unit
        changed = True

    if changed and not pending_definition_equation_inputs(task, reader, execution_order):
        task.status = TaskStatus.COMPLETED
        return True
    if changed:
        return True
    return False


def _definition_equation_specs(
    reader: StandardsReader,
    execution_order: tuple[str, ...] | list[str],
) -> list[DefinitionEquationSpec]:
    specs: list[DefinitionEquationSpec] = []
    for node_id in execution_order:
        try:
            record = reader.load(node_id)
        except FileNotFoundError:
            continue
        if str(record.metadata.get("type", "")) != "definition":
            continue
        for equation in record.metadata.get("equations", []) or []:
            if not isinstance(equation, dict):
                continue
            function_name = str(equation.get("execution_function", "")).strip()
            file_rel = equation.get("file")
            if not function_name or not file_rel:
                continue
            path = record.path.parent / str(file_rel)
            data = _parse_equation_frontmatter(path)
            variables = tuple(
                str(key)
                for key in (data.get("variables") or {}).keys()
                if str(key)
            )
            outputs = data.get("outputs") or []
            output_keys: list[str] = []
            if isinstance(outputs, list):
                for item in outputs:
                    if isinstance(item, dict):
                        for key in ("name", "symbol"):
                            value = str(item.get(key) or "").strip()
                            if value:
                                output_keys.append(value)
            if not output_keys:
                output_keys = ["minimum_required_thickness", "t_m"]
            specs.append(
                DefinitionEquationSpec(
                    node_id=record.node_id,
                    equation_id=str(equation.get("id") or path.stem),
                    function_name=function_name,
                    node_dir=record.path.parent,
                    variables=variables,
                    output_keys=tuple(dict.fromkeys(output_keys)),
                )
            )
    return specs


def _equation_outputs_satisfied(task: Task, spec: DefinitionEquationSpec) -> bool:
    return any(task.outputs.get(key) is not None for key in spec.output_keys)


def _missing_user_inputs_for_equation(
    task: Task,
    reader: StandardsReader,
    spec: DefinitionEquationSpec,
) -> list[str]:
    missing: list[str] = []
    nomenclature = _nomenclature_by_symbol(reader, spec.node_id)
    for symbol in spec.variables:
        if _resolve_output_value(task, symbol) is not None:
            continue
        entry = nomenclature.get(symbol) or {}
        input_id = str(entry.get("input_id") or "").strip()
        if not input_id:
            continue
        if not _input_value_ready(task, input_id):
            missing.append(input_id)
    return missing


def _resolve_equation_variables(
    task: Task,
    reader: StandardsReader,
    spec: DefinitionEquationSpec,
) -> tuple[dict[str, float], list[str]]:
    resolved: dict[str, float] = {}
    unresolved: list[str] = []
    nomenclature = _nomenclature_by_symbol(reader, spec.node_id)

    for symbol in spec.variables:
        output_value = _resolve_output_value(task, symbol)
        if output_value is not None:
            resolved[symbol] = float(output_value)
            continue

        entry = nomenclature.get(symbol) or {}
        input_id = str(entry.get("input_id") or "").strip()
        if not input_id:
            unresolved.append(symbol)
            continue
        if not _input_value_ready(task, input_id):
            unresolved.append(input_id)
            continue
        prepared = prepare_engineering_input(task.inputs[input_id])
        resolved[symbol] = float(prepared.value)

    return resolved, unresolved


def _nomenclature_by_symbol(reader: StandardsReader, node_id: str) -> dict[str, dict[str, Any]]:
    try:
        record = reader.load(node_id)
    except FileNotFoundError:
        return {}
    mapping: dict[str, dict[str, Any]] = {}
    for item in record.metadata.get("nomenclature", []) or []:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip()
        if symbol:
            mapping[symbol] = item
    return mapping


def _resolve_output_value(task: Task, symbol: str) -> float | None:
    for key in _OUTPUT_SYMBOL_KEYS.get(symbol, (symbol,)):
        value = task.outputs.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _input_value_ready(task: Task, input_id: str) -> bool:
    stored = task.inputs.get(input_id)
    if not isinstance(stored, EngineeringInput):
        return False
    if stored.status == InputStatus.PROPOSED_DEFAULT:
        return False
    if stored.requires_confirmation and not input_is_expansion_ready(stored):
        return False
    if stored.value is None:
        return False
    return True


def _parse_equation_frontmatter(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        parsed = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
