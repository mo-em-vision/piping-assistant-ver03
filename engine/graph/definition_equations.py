"""Track and evaluate definition-node equations after calculation nodes complete."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from engine.graph.param_priority import normalize_require_ids
from engine.graph.relationship_resolver import resolve_require_bindings
from engine.executor.functions import get_execution_function
from engine.equation.sympy_evaluator import evaluate_equation
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
    sympy_expr: str | None = None
    display_latex: str | None = None
    requires_param_nodes: tuple[str, ...] = ()
    require_bindings: tuple[tuple[str, str], ...] = ()
    calculates_param_nodes: tuple[str, ...] = ()


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
        if spec.function_name == "sympy" and spec.sympy_expr:
            try:
                result = evaluate_equation(
                    sympy_expr=spec.sympy_expr,
                    display_latex=spec.display_latex or spec.sympy_expr,
                    symbol_values=variables,
                )
            except Exception:  # noqa: BLE001
                continue
            value = next(iter(result.outputs.values()), None)
            if value is None:
                continue
            unit = "mm"
            for key in spec.output_keys:
                task.outputs[key] = float(value)
                task.outputs[f"{key}_unit"] = unit
            task.outputs.setdefault("_equation_substitution", result.substitution)
            changed = True
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
        if str(record.metadata.get("type", "")) == "equation":
            sympy_expr = str(record.metadata.get("sympy", "")).strip()
            if sympy_expr:
                variables: list[str] = []
                output_keys: list[str] = []
                requires_nodes = tuple(normalize_require_ids(record.metadata.get("requires")))
                store = reader.graph_store
                bindings = resolve_require_bindings(store, record.metadata.get("requires"))
                binding_pairs = tuple((b.param_id, b.sympy_symbol) for b in bindings)
                variables = [symbol for _, symbol in binding_pairs]
                if not variables:
                    for param_id in requires_nodes:
                        try:
                            param = reader.load(param_id)
                        except FileNotFoundError:
                            continue
                        symbol = str(param.metadata.get("symbol", "")).strip()
                        if symbol:
                            variables.append(symbol)
                            binding_pairs = (*binding_pairs, (param_id, symbol))
                calculates_nodes = tuple(str(item) for item in (record.metadata.get("calculates") or []))
                for param_id in calculates_nodes:
                    try:
                        param = reader.load(param_id)
                    except FileNotFoundError:
                        continue
                    input_id = str(param.metadata.get("input_id", "")).strip()
                    symbol = str(param.metadata.get("symbol", "")).strip()
                    if input_id:
                        output_keys.append(input_id)
                    if symbol:
                        output_keys.append(symbol)
                if not output_keys:
                    output_keys = ["minimum_required_thickness", "t_m"]
                specs.append(
                    DefinitionEquationSpec(
                        node_id=record.node_id,
                        equation_id=str(record.metadata.get("equation_id") or record.node_id),
                        function_name="sympy",
                        node_dir=record.path.parent,
                        variables=tuple(variables),
                        output_keys=tuple(dict.fromkeys(output_keys)),
                        sympy_expr=sympy_expr,
                        display_latex=str(record.metadata.get("display_latex") or sympy_expr),
                        requires_param_nodes=requires_nodes,
                        require_bindings=binding_pairs,
                        calculates_param_nodes=calculates_nodes,
                    )
                )
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
            path = reader.resolve_asset_path(record, str(file_rel))
            if path is not None and path.is_file():
                data = _parse_equation_frontmatter(path)
            else:
                text = reader.read_asset_text(record, str(file_rel))
                data = _parse_equation_frontmatter_text(text) if text else {}
            if not data:
                continue
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
            equation_stem = path.stem if path is not None else Path(str(file_rel)).stem
            specs.append(
                DefinitionEquationSpec(
                    node_id=record.node_id,
                    equation_id=str(equation.get("id") or equation_stem),
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
    if spec.require_bindings:
        for param_id, symbol in spec.require_bindings:
            if symbol and _resolve_output_value(task, symbol) is not None:
                continue
            try:
                param = reader.load(param_id)
            except FileNotFoundError:
                continue
            input_id = str(param.metadata.get("input_id", "")).strip()
            if input_id and not _input_value_ready(task, input_id):
                missing.append(input_id)
        return missing
    if spec.requires_param_nodes:
        for param_id in spec.requires_param_nodes:
            try:
                param = reader.load(param_id)
            except FileNotFoundError:
                continue
            symbol = str(param.metadata.get("symbol", "")).strip()
            if symbol and _resolve_output_value(task, symbol) is not None:
                continue
            input_id = str(param.metadata.get("input_id", "")).strip()
            if input_id and not _input_value_ready(task, input_id):
                missing.append(input_id)
        return missing

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

    if spec.require_bindings:
        for param_id, symbol in spec.require_bindings:
            output_value = _resolve_output_value(task, symbol)
            if output_value is not None:
                resolved[symbol] = float(output_value)
                continue
            try:
                param = reader.load(param_id)
            except FileNotFoundError:
                unresolved.append(param_id)
                continue
            input_id = str(param.metadata.get("input_id", "")).strip()
            if not input_id:
                unresolved.append(symbol)
                continue
            if not _input_value_ready(task, input_id):
                unresolved.append(input_id)
                continue
            prepared = prepare_engineering_input(task.inputs[input_id])
            resolved[symbol] = float(prepared.value)
        return resolved, unresolved

    if spec.requires_param_nodes:
        for param_id in spec.requires_param_nodes:
            try:
                param = reader.load(param_id)
            except FileNotFoundError:
                unresolved.append(param_id)
                continue
            symbol = str(param.metadata.get("symbol", "")).strip()
            if not symbol:
                continue
            output_value = _resolve_output_value(task, symbol)
            if output_value is not None:
                resolved[symbol] = float(output_value)
                continue
            input_id = str(param.metadata.get("input_id", "")).strip()
            if not input_id:
                unresolved.append(symbol)
                continue
            if not _input_value_ready(task, input_id):
                unresolved.append(input_id)
                continue
            prepared = prepare_engineering_input(task.inputs[input_id])
            resolved[symbol] = float(prepared.value)
        return resolved, unresolved

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
    return _parse_equation_frontmatter_text(path.read_text(encoding="utf-8"))


def _parse_equation_frontmatter_text(text: str) -> dict[str, Any]:
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
