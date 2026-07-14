"""Build canonical equation display traces from execution data and node metadata."""

from __future__ import annotations

from typing import Any

from engine.equation.equation_renderer import EquationRenderSteps
from engine.equation.latex_format import (
    display_text_to_latex,
    format_numeric_display,
    format_quantity_latex,
    format_substituted_equation,
    format_substituted_term,
)
from engine.graph.param_priority import require_target_id
from engine.graph.relationship_resolver import RequireBinding, resolve_require_bindings
from engine.equation.input_table import equation_parameter_description
from engine.reference.parameter_value_source import resolve_parameter_value_reference
from engine.reference.standards_reader import StandardsReader
from models.calculation import CalculationResult, CalculationStep
from models.equation_display_trace import (
    EquationDisplayInput,
    EquationDisplayLatexSource,
    EquationDisplayQuantity,
    EquationDisplaySourceType,
    EquationDisplayStatus,
    EquationDisplayTrace,
)
from models.fact import Fact, SourceType, fact_scalar_value, fact_unit
from models.task import Task


def _bindings_from_metadata(requires: Any) -> list[RequireBinding]:
    bindings: list[RequireBinding] = []
    for item in requires or []:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or item.get("alias") or "").strip()
        param_id = str(item.get("parameter") or require_target_id(item) or symbol or "").strip()
        if not symbol:
            continue
        if not param_id:
            continue
        bindings.append(
            RequireBinding(
                concept_id=param_id,
                param_id=param_id,
                sympy_symbol=symbol,
                metadata=dict(item),
            )
        )
    return bindings


def _resolve_bindings(
    store,
    requires: Any,
) -> list[RequireBinding]:
    if store.available:
        bindings = resolve_require_bindings(store, requires)
        if bindings:
            return bindings
    return _bindings_from_metadata(requires)


def _output_symbols(
    metadata: dict[str, Any],
    calculation: CalculationResult | None,
) -> frozenset[str]:
    symbols: set[str] = set()
    primary = _output_symbol(metadata, calculation)
    if primary:
        symbols.add(primary)
    for item in metadata.get("calculates") or []:
        if isinstance(item, dict):
            symbol = str(item.get("symbol") or "").strip()
            if symbol:
                symbols.add(symbol)
        elif item:
            symbol = str(item).strip()
            if symbol:
                symbols.add(symbol)
    return frozenset(symbols)


def _symbols_for_substitution(
    symbolic_latex: str,
    bindings: list[RequireBinding],
    resolved_values: dict[str, float],
    *,
    exclude_symbols: frozenset[str] | None = None,
) -> list[str]:
    excluded = exclude_symbols or frozenset()
    ordered = [
        binding.sympy_symbol
        for binding in bindings
        if binding.sympy_symbol and binding.sympy_symbol not in excluded
    ]
    extras = [
        symbol
        for symbol in resolved_values
        if symbol not in ordered and symbol not in excluded
    ]
    candidates = ordered + sorted(extras, key=len, reverse=True)
    return [
        symbol
        for symbol in candidates
        if symbol in symbolic_latex or not symbolic_latex
    ]


def resolve_symbolic_latex_from_metadata(
    metadata: dict[str, Any],
) -> tuple[str, EquationDisplayLatexSource]:
    display_latex = metadata.get("display_latex")
    if display_latex:
        text = str(display_latex).strip()
        if text:
            return text, "metadata_display_latex"

    nested = metadata.get("display")
    if isinstance(nested, dict):
        for key in ("latex", "text"):
            value = nested.get(key)
            if value:
                text = str(value).strip()
                if text:
                    return display_text_to_latex(text), "metadata_display_text"
    elif isinstance(nested, str) and nested.strip():
        return display_text_to_latex(nested.strip()), "metadata_display_text"

    sympy_expr = metadata.get("sympy")
    if sympy_expr:
        text = str(sympy_expr).strip()
        if text:
            return display_text_to_latex(text), "sympy_generated"

    return "", "sympy_generated"


def _param_unit(reader: StandardsReader, param_id: str, metadata: dict[str, Any]) -> str | None:
    unit = metadata.get("unit") or metadata.get("canonical_unit")
    if unit:
        return str(unit).strip() or None
    if not param_id:
        return None
    try:
        param = reader.load(param_id)
    except FileNotFoundError:
        return None
    meta = param.metadata
    resolved = str(meta.get("unit") or meta.get("canonical_unit") or "").strip()
    return resolved or None


def _classify_source_type(
    *,
    reader: StandardsReader,
    param_id: str,
    param_meta: dict[str, Any],
    symbol: str,
    fact_key: str,
    dependency_outputs: dict[str, Any],
    task_inputs: dict[str, Fact],
    task: Task | None,
) -> tuple[EquationDisplaySourceType | None, str | None]:
    for key in (symbol, fact_key):
        if key and key in dependency_outputs and dependency_outputs[key] is not None:
            ref = None
            if task is not None and param_id:
                value_ref = resolve_parameter_value_reference(reader, param_id, task)
                if value_ref:
                    ref = value_ref.get("node_id")
            return "equation_output", ref

    resolution = param_meta.get("resolution") or {}
    if isinstance(resolution, dict):
        method = str(resolution.get("method", "")).strip()
        if method == "table_lookup":
            table_id = str(resolution.get("table_id") or "").strip()
            return "table_lookup", table_id or None

    fact = task_inputs.get(fact_key) if fact_key else None
    if fact is not None:
        source = fact.source.source_type if fact.source else None
        if source == SourceType.USER_INPUT:
            return "user_input", None
        if source == SourceType.DEFAULT_CONFIRMED:
            return "default", fact.source.source_id if fact.source else None
        if source == SourceType.SYSTEM:
            return "system", fact.source.source_id if fact.source else None

    if task is not None and param_id:
        value_ref = resolve_parameter_value_reference(reader, param_id, task)
        if value_ref:
            kind = value_ref.get("reference_kind")
            if kind == "table":
                return "table_lookup", value_ref.get("node_id")
            return "equation_output", value_ref.get("node_id")

    return None, None


def _intermediate_quantities(
    calculation: CalculationResult | None,
    output_symbol: str,
) -> tuple[EquationDisplayQuantity, ...]:
    if calculation is None:
        return ()
    quantities: list[EquationDisplayQuantity] = []
    seen: set[str] = set()
    for step in calculation.steps:
        if not isinstance(step, CalculationStep):
            continue
        result = step.result
        if not isinstance(result, dict):
            continue
        for name, value in result.items():
            if name == output_symbol or name in seen:
                continue
            if not isinstance(value, (int, float)):
                continue
            seen.add(str(name))
            numeric = float(value)
            quantities.append(
                EquationDisplayQuantity(
                    symbol=str(name),
                    value=numeric,
                    unit="",
                    display_value=format_numeric_display(numeric),
                )
            )
    return tuple(quantities)


def _output_symbol(metadata: dict[str, Any], calculation: CalculationResult | None) -> str:
    if calculation and calculation.final_result and calculation.final_result.symbol:
        return str(calculation.final_result.symbol)
    calculates = metadata.get("calculates") or []
    for item in calculates:
        if isinstance(item, dict):
            symbol = str(item.get("symbol") or "").strip()
            if symbol:
                return symbol
        elif item:
            try:
                symbol = str(item).strip()
            except Exception:
                continue
            if symbol:
                return symbol
    outputs = metadata.get("outputs") or []
    for spec in outputs:
        if isinstance(spec, dict):
            symbol = str(spec.get("symbol") or "").strip()
            if symbol:
                return symbol
    return ""


def _resolve_output_value(
    output_symbol: str,
    *,
    resolved_values: dict[str, float],
    deps: dict[str, Any],
    calculation: CalculationResult | None,
) -> tuple[float | None, str]:
    if calculation and calculation.final_result and calculation.final_result.value is not None:
        return float(calculation.final_result.value), str(calculation.final_result.unit or "")

    if output_symbol and output_symbol in resolved_values:
        return float(resolved_values[output_symbol]), str(deps.get(f"{output_symbol}_unit") or "")

    if output_symbol:
        raw = deps.get(output_symbol)
        if isinstance(raw, (int, float)):
            return float(raw), str(deps.get(f"{output_symbol}_unit") or "")

    return None, ""


def _build_substituted_latex(
    *,
    symbolic_latex: str,
    bindings: list[RequireBinding],
    resolved_values: dict[str, float],
    inputs: list[EquationDisplayInput],
    exclude_symbols: frozenset[str] | None = None,
) -> str | None:
    excluded = exclude_symbols or frozenset()
    substitutions: dict[str, str] = {}
    substitution_symbols = _symbols_for_substitution(
        symbolic_latex,
        bindings,
        resolved_values,
        exclude_symbols=excluded,
    )
    for symbol in substitution_symbols:
        if symbol in excluded:
            continue
        value = resolved_values.get(symbol)
        if value is None:
            continue
        unit = next((item.unit for item in inputs if item.symbol == symbol), None)
        substitutions[symbol] = format_substituted_term(value, unit)

    if substitutions and symbolic_latex:
        return format_substituted_equation(
            symbolic_latex,
            substitutions,
            symbol_order=substitution_symbols,
        )
    return None


def build_equation_display_trace(
    *,
    reader: StandardsReader,
    equation_id: str,
    equation_metadata: dict[str, Any],
    symbol_values: dict[str, float] | None = None,
    source_node_id: str = "",
    dependency_outputs: dict[str, Any] | None = None,
    task_inputs: dict[str, Fact] | None = None,
    calculation: CalculationResult | None = None,
    render_steps: EquationRenderSteps | None = None,
    task: Task | None = None,
    status: EquationDisplayStatus | None = None,
) -> EquationDisplayTrace:
    """Build a generic equation display trace from execution context."""
    metadata = equation_metadata
    symbolic_latex, latex_source = resolve_symbolic_latex_from_metadata(metadata)
    paragraph = str(metadata.get("paragraph_number") or metadata.get("paragraph") or "").strip() or None
    title = str(metadata.get("name") or metadata.get("title") or "").strip() or None

    resolved_values = dict(symbol_values or {})
    deps = dependency_outputs or {}
    facts = task_inputs or {}

    output_symbol_hint = _output_symbol(metadata, calculation)
    if output_symbol_hint:
        for key in (output_symbol_hint,):
            raw = deps.get(key)
            if isinstance(raw, (int, float)):
                resolved_values.setdefault(output_symbol_hint, float(raw))

    store = reader.graph_store
    bindings = _resolve_bindings(store, metadata.get("requires"))

    inputs: list[EquationDisplayInput] = []
    missing_required = False
    symbol_order: list[str] = []

    for binding in bindings:
        symbol = binding.sympy_symbol
        symbol_order.append(symbol)
        param_id = binding.param_id
        try:
            param_meta = reader.load(param_id).metadata
        except FileNotFoundError:
            param_meta = {}

        label = equation_parameter_description(reader, param_id)
        fact_key = str(param_meta.get("input_id") or param_meta.get("key") or "").strip()
        unit = _param_unit(reader, param_id, param_meta)

        value = resolved_values.get(symbol)
        if value is None and fact_key:
            fact = facts.get(fact_key)
            if fact is not None:
                scalar = fact_scalar_value(fact)
                if scalar is not None:
                    try:
                        value = float(scalar)
                    except (TypeError, ValueError):
                        value = None
                if unit is None:
                    resolved_unit = fact_unit(fact)
                    if resolved_unit:
                        unit = resolved_unit

        source_type, source_ref = _classify_source_type(
            reader=reader,
            param_id=param_id,
            param_meta=param_meta,
            symbol=symbol,
            fact_key=fact_key,
            dependency_outputs=deps,
            task_inputs=facts,
            task=task,
        )

        display_value = None
        if value is not None:
            resolved_values[symbol] = value
            display_value = format_quantity_latex(value, unit)

        item_required = True
        for req_item in metadata.get("requires") or []:
            if not isinstance(req_item, dict):
                continue
            req_param = str(req_item.get("parameter") or require_target_id(req_item) or "")
            if req_param == param_id and req_item.get("required") is False:
                item_required = False
                break

        if item_required and value is None:
            missing_required = True

        inputs.append(
            EquationDisplayInput(
                symbol=symbol,
                parameter_id=param_id or None,
                label=label,
                value=value,
                unit=unit,
                display_value=display_value,
                source_type=source_type,
                source_ref=source_ref,
            )
        )

    trace_status: EquationDisplayStatus
    if status is not None:
        trace_status = status
    elif missing_required:
        trace_status = "blocked"
    else:
        trace_status = "evaluated"

    output_symbol = _output_symbol(metadata, calculation)
    output_symbols = _output_symbols(metadata, calculation)
    result_quantity: EquationDisplayQuantity | None = None
    result_latex: str | None = None
    substituted_latex: str | None = None

    partial_substituted = _build_substituted_latex(
        symbolic_latex=symbolic_latex,
        bindings=bindings,
        resolved_values=resolved_values,
        inputs=inputs,
        exclude_symbols=output_symbols,
    )

    if trace_status == "evaluated":
        final_value, final_unit = _resolve_output_value(
            output_symbol,
            resolved_values=resolved_values,
            deps=deps,
            calculation=calculation,
        )
        if final_value is None and output_symbol and output_symbol in resolved_values:
            final_value = float(resolved_values[output_symbol])
        elif final_value is None and resolved_values:
            for key, val in resolved_values.items():
                if key not in {item.symbol for item in inputs}:
                    final_value = float(val)
                    output_symbol = key
                    break

        if final_value is not None and output_symbol:
            result_quantity = EquationDisplayQuantity(
                symbol=output_symbol,
                value=final_value,
                unit=final_unit,
                display_value=format_quantity_latex(final_value, final_unit or None),
            )
            result_latex = format_quantity_latex(final_value, final_unit or None)

        substituted_latex = partial_substituted

        if render_steps is not None and render_steps.evaluated:
            evaluated = str(render_steps.evaluated).strip()
            if " = " in evaluated:
                _, rhs = evaluated.split(" = ", 1)
                result_latex = rhs.strip()
    elif partial_substituted:
        substituted_latex = partial_substituted

    return EquationDisplayTrace(
        equation_id=equation_id,
        node_id=source_node_id or equation_id,
        paragraph=paragraph,
        title=title,
        symbolic_latex=symbolic_latex,
        substituted_latex=substituted_latex,
        result_latex=result_latex,
        latex_source=latex_source,
        result=result_quantity,
        inputs=tuple(inputs),
        intermediate_values=_intermediate_quantities(calculation, output_symbol),
        status=trace_status,
    )


def trace_from_execution_payload(
    payload: dict[str, Any],
) -> EquationDisplayTrace | None:
    trace_data = payload.get("equation_display_trace")
    if isinstance(trace_data, dict):
        return EquationDisplayTrace.from_dict(trace_data)
    return None
