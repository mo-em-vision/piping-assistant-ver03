"""Graph-driven equation evaluation display for the desktop center panel."""

from __future__ import annotations

from typing import Any

from api.display_block_metadata import (
    _all_equation_trace_entries,
    equation_display_block_id,
    tag_equation_block,
)
from models.display_role import DisplayState, EquationContent, infer_equation_content
from engine.equation.input_table import (
    INPUT_TABLE_COLUMNS,
    build_base_input_row,
    finalize_equation_input_table_row,
    resolve_row_value_parts,
)
from api.equation_inputs_display import AWAITING_USER_INPUT, _input_display_value
from engine.graph.assumption_checker import field_value
from engine.graph.param_priority import require_target_id
from engine.messaging.formula_parameter_prompt import resolve_focus_calculation_node
from engine.reference.formula_display import (
    _resolve_equation_node_id,
    load_equation_context,
    resolve_equation_display_variables,
)
from engine.reference.parameter_keys import param_node_id_for_input
from engine.reference.parameter_value_source import (
    apply_value_provenance_to_row,
    resolve_parameter_value_reference,
)
from engine.reference.standards_reader import StandardsReader
from models.planning import NavigationPhase
from models.task import Task


_INPUT_TABLE_COLUMNS = INPUT_TABLE_COLUMNS


def resolve_focus_node_for_equation_display(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
) -> str | None:
    """Return the calculation or equation node driving the live equation preview."""
    path = planning.get("path_decision") or {}
    if isinstance(path, dict) and path.get("selected_node"):
        return str(path["selected_node"])

    from models.planning import NavigationPlan

    nav_plan = None
    if planning:
        try:
            nav_plan = NavigationPlan(
                path_decision=path if isinstance(path, dict) else None,
                selected_nodes=list(planning.get("selected_nodes") or []),
                current_phase=NavigationPhase(
                    str(planning.get("current_phase") or NavigationPhase.PARAMETER_GATHERING.value)
                ),
            )
        except ValueError:
            nav_plan = None

    focus = resolve_focus_calculation_node(
        nav_plan,
        reader,
        task_inputs=task.fact_store.active_facts(),
    )
    if focus:
        return focus

    for node_id in task.active_nodes:
        try:
            node_type = str(reader.load(str(node_id)).metadata.get("type", ""))
        except FileNotFoundError:
            continue
        if node_type in {"equation", "calculation", "paragraph"}:
            return str(node_id)
    return None


def equation_evaluation_in_progress(
    task: Task,
    *,
    focus_node_id: str,
    reader: StandardsReader,
) -> bool:
    """True while the focus equation is active and its inputs are still being collected."""
    equation_id = resolve_equation_node_for_display(reader, focus_node_id, task)
    if not equation_id:
        return False

    try:
        eq_record = reader.load(equation_id)
    except FileNotFoundError:
        return False

    eq_type = str(eq_record.metadata.get("type", ""))
    if eq_type != "equation":
        return True

    for item in eq_record.metadata.get("requires") or []:
        if not isinstance(item, dict):
            continue
        param_id = str(item.get("parameter") or require_target_id(item) or "").strip()
        input_id = _param_input_id(reader, param_id)
        if not input_id:
            continue
        if field_value(input_id, task.fact_store.active_facts()) is None:
            if _output_display_value(task, input_id) is None:
                return True
    return False


def _equation_display_heading(metadata: dict[str, Any]) -> tuple[str | None, str | None]:
    """User-facing equation title and description from equation node metadata."""
    title = str(metadata.get("name") or metadata.get("title") or "").strip() or None
    description = str(metadata.get("description") or metadata.get("purpose") or "").strip() or None
    return title, description


def build_equation_evaluation_block(
    task: Task,
    reader: StandardsReader,
    focus_node_id: str,
    *,
    block_id: str | None = None,
    display_state: str | None = None,
    display_channel: str | None = None,
    attach_paragraph_context: bool = True,
) -> dict[str, Any] | None:
    """Build a desktop equation block with live symbol table and definition links."""
    equation_id = resolve_equation_node_for_display(reader, focus_node_id, task)
    if not equation_id:
        return None
    try:
        eq_record = reader.load(equation_id)
    except FileNotFoundError:
        return None

    display = _equation_display(eq_record.metadata)
    if not display:
        context = load_equation_context(reader, equation_id)
        display = str(context.get("display") or "").strip()
    if not display:
        return None

    rows = _equation_input_rows(reader, eq_record.metadata, task)
    if not rows:
        resolved = resolve_equation_display_variables(reader, equation_id)
        rows = _legacy_variable_rows(reader, resolved.get("variables") or [], task)

    resolved_block_id = block_id or equation_display_block_id(equation_id)
    equation_title, equation_description = _equation_display_heading(eq_record.metadata)

    block: dict[str, Any] = {
        "id": resolved_block_id,
        "type": "equation",
        "title": equation_title,
        "content": _display_to_latex(display),
        "display": display,
        "input_table": {
            "columns": list(_INPUT_TABLE_COLUMNS),
            "rows": rows,
        },
    }
    if equation_description:
        block["context_intro"] = equation_description

    nomenclature_reference = resolve_equation_display_variables(reader, equation_id).get(
        "nomenclature_reference"
    )
    if nomenclature_reference and not rows:
        block["nomenclature_reference"] = nomenclature_reference

    from api.equation_display_trace_serializer import enrich_equation_block, find_trace_for_equation

    execution_trace = find_trace_for_equation(task, equation_id)
    if execution_trace is None:
        execution_trace = _live_equation_display_trace(
            task,
            reader,
            equation_id=equation_id,
            equation_metadata=eq_record.metadata,
            source_node_id=focus_node_id,
        )

    resolved_state = display_state
    if resolved_state is None:
        if execution_trace is not None and execution_trace.status == "evaluated":
            resolved_state = DisplayState.evaluated.value
        else:
            resolved_state = DisplayState.preview.value

    tagged = tag_equation_block(
        block,
        display_state=resolved_state,
        equation_node_id=equation_id,
        source_node_id=focus_node_id,
        display_channel=display_channel,
    )
    tagged.pop("display_channel", None)
    if tagged.get("input_table") and tagged.get("variables"):
        tagged.pop("variables", None)

    if execution_trace is not None:
        tagged = enrich_equation_block(tagged, execution_trace, reader=reader, task=task)
        tagged["display_state"] = (
            DisplayState.evaluated.value
            if execution_trace.status == "evaluated"
            else resolved_state
        )
        tagged["equation_content"] = infer_equation_content(tagged)

    if attach_paragraph_context:
        from api.paragraph_display import build_equation_context_from_paragraph

        context = build_equation_context_from_paragraph(reader, focus_node_id)
        if context:
            paragraph_intro = str(context.get("context_intro") or "").strip()
            if paragraph_intro and not str(tagged.get("context_intro") or "").strip():
                tagged["context_intro"] = paragraph_intro
            lead = str(context.get("context_lead") or "").strip()
            if lead:
                tagged["context_lead"] = lead

    return tagged


def _live_equation_display_trace(
    task: Task,
    reader: StandardsReader,
    *,
    equation_id: str,
    equation_metadata: dict[str, Any],
    source_node_id: str,
):
    from engine.equation.equation_display_trace_builder import build_equation_display_trace
    from engine.graph.assumption_checker import field_value
    from engine.graph.relationship_resolver import resolve_require_bindings

    store = reader.graph_store
    if not store.available:
        return None

    bindings = resolve_require_bindings(store, equation_metadata.get("requires"))
    symbol_values: dict[str, float] = {}
    facts = task.fact_store.active_facts()
    for binding in bindings:
        input_id = _param_input_id(reader, binding.param_id)
        value = None
        if input_id:
            raw = field_value(input_id, facts)
            if raw is not None:
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    value = None
            if value is None:
                output_value = task.outputs.get(input_id)
                if output_value is None:
                    output_value = task.outputs.get(binding.sympy_symbol)
                if isinstance(output_value, (int, float)):
                    value = float(output_value)
        if value is not None:
            symbol_values[binding.sympy_symbol] = value

    return build_equation_display_trace(
        reader=reader,
        equation_id=equation_id,
        equation_metadata=equation_metadata,
        symbol_values=symbol_values,
        source_node_id=source_node_id,
        task_inputs=facts,
        dependency_outputs=dict(task.outputs),
        task=task,
    )


def build_equation_trace_block(
    task: Task,
    reader: StandardsReader,
    source_node_id: str,
) -> dict[str, Any] | None:
    """Build a durable equation block rebuilt from current task state."""
    return build_equation_evaluation_block(
        task,
        reader,
        source_node_id,
        display_state=DisplayState.evaluated.value,
    )


def equation_display_blocks_from_trace(
    task: Task,
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    """Canonical equation blocks from evaluated execution trace entries."""
    blocks: list[dict[str, Any]] = []
    built: set[str] = set()
    for item in _all_equation_trace_entries(task):
        equation_node_id = item["equation_node_id"]
        if equation_node_id in built:
            continue
        block = build_equation_evaluation_block(
            task,
            reader,
            item["source_node_id"],
            attach_paragraph_context=False,
        )
        if block is not None and str(block.get("equation_node_id") or "") == equation_node_id:
            blocks.append(block)
            built.add(equation_node_id)
    return blocks


def equation_display_blocks_for_task(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
    *,
    paragraph_node_ids: set[str] | frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Emit evaluated trace equations plus the current focus equation."""
    entries: dict[str, str] = {}
    for item in _all_equation_trace_entries(task):
        entries[item["equation_node_id"]] = item["source_node_id"]

    focus_node = resolve_focus_node_for_equation_display(task, planning, reader)
    if focus_node:
        equation_id = resolve_equation_node_for_display(reader, focus_node, task)
        if equation_id:
            entries[equation_id] = focus_node

    paragraph_ids = set(paragraph_node_ids or ())
    blocks: list[dict[str, Any]] = []
    for equation_id, source_node_id in entries.items():
        attach_context = source_node_id not in paragraph_ids
        block = build_equation_evaluation_block(
            task,
            reader,
            source_node_id,
            attach_paragraph_context=attach_context,
        )
        if block is not None and str(block.get("equation_node_id") or "") == equation_id:
            blocks.append(block)
    return blocks


def resolve_equation_node_for_display(
    reader: StandardsReader,
    focus_node_id: str,
    task: Task,
) -> str | None:
    """Resolve the executable equation node referenced by a paragraph or section."""
    resolved_id = _resolve_equation_node_id(reader, focus_node_id)
    try:
        record = reader.load(resolved_id)
    except FileNotFoundError:
        return None

    node_type = str(record.metadata.get("type", ""))
    if node_type == "equation" and (
        record.metadata.get("requires") or _equation_display(record.metadata)
    ):
        return resolved_id

    facts = task.fact_store.active_facts()
    for edge in record.metadata.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        if str(edge.get("type", "")) != "references_equation":
            continue
        target = str(edge.get("target", "")).strip()
        if not target:
            continue
        when = edge.get("when")
        if isinstance(when, dict) and not _edge_when_applies(when, facts):
            continue
        try:
            target_record = reader.load(target)
        except FileNotFoundError:
            continue
        if str(target_record.metadata.get("type", "")) == "equation":
            return target

    for ref in record.metadata.get("contains", []) or []:
        ref_id = str(ref).strip()
        if not ref_id:
            continue
        try:
            child = reader.load(ref_id)
        except FileNotFoundError:
            continue
        if str(child.metadata.get("type", "")) == "equation":
            return ref_id

    return None


def _edge_when_applies(when: dict[str, Any], facts: dict[str, Any]) -> bool:
    field_name = str(when.get("field", "")).strip()
    if when.get("absent"):
        return field_value(field_name, facts) is None
    if when.get("present"):
        return field_value(field_name, facts) is not None
    allowed = when.get("in")
    if field_name and isinstance(allowed, list):
        value = field_value(field_name, facts)
        return value in allowed
    equals = when.get("equals")
    if field_name and equals is not None:
        return field_value(field_name, facts) == equals
    return True


def _dedupe_equation_input_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in rows:
        param_id = str(row.get("parameter_id") or "").strip()
        symbol = str(row.get("symbol") or "").strip()
        key = param_id or symbol
        if not key:
            continue
        existing = seen.get(key)
        if existing is None:
            seen[key] = row
            order.append(key)
            continue
        if len(str(row.get("description") or row.get("definition") or "")) > len(
            str(existing.get("description") or existing.get("definition") or "")
        ):
            seen[key] = row
    return [seen[key] for key in order]


def _equation_input_rows(
    reader: StandardsReader,
    equation_metadata: dict[str, Any],
    task: Task,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in equation_metadata.get("requires") or []:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or item.get("alias") or "").strip()
        param_id = str(item.get("parameter") or require_target_id(item) or "").strip()
        input_id = _param_input_id(reader, param_id)
        value_text, unit_text, provenance_display = resolve_row_value_parts(
            task,
            reader,
            param_id=param_id,
            input_id=input_id,
            symbol=symbol,
        )
        row = build_base_input_row(reader=reader, symbol=symbol, param_id=param_id)
        row["value"] = value_text
        row["unit"] = unit_text
        if param_id:
            row = apply_value_provenance_to_row(
                row,
                reader,
                param_id,
                task,
                display_value=provenance_display or value_text,
            )
        elif value_text:
            row["value_status"] = "user_supplied"
        else:
            row["value"] = AWAITING_USER_INPUT
            row["value_status"] = "unresolved_user_input"
        definition_reference = _definition_reference_for_parameter(reader, param_id)
        if definition_reference is not None:
            row["definition_reference"] = definition_reference
        rows.append(finalize_equation_input_table_row(row))
    return _dedupe_equation_input_rows(rows)


def _legacy_variable_rows(
    reader: StandardsReader,
    variables: list[dict[str, Any]],
    task: Task,
) -> list[dict[str, Any]]:
    from api.equation_inputs_display import _SYMBOL_TO_INPUT_ID

    rows: list[dict[str, Any]] = []
    for variable in variables:
        symbol = str(variable.get("symbol", "")).strip()
        if not symbol:
            continue
        input_id = _SYMBOL_TO_INPUT_ID.get(symbol)
        param_id = param_node_id_for_input(input_id) if input_id else None
        value_text, unit_text, provenance_display = resolve_row_value_parts(
            task,
            reader,
            param_id=param_id or "",
            input_id=input_id,
            symbol=symbol,
        )
        if not value_text and variable.get("value"):
            value_text = str(variable.get("value") or "").strip()
        row = build_base_input_row(
            reader=reader,
            symbol=symbol,
            param_id=param_id or "",
        )
        row["value"] = value_text
        row["unit"] = unit_text
        if param_id:
            row = apply_value_provenance_to_row(
                row,
                reader,
                param_id,
                task,
                display_value=provenance_display or value_text,
            )
        elif value_text:
            row["value_status"] = "user_supplied"
        else:
            row["value"] = AWAITING_USER_INPUT
            row["value_status"] = "unresolved_user_input"
        if param_id:
            definition_reference = _definition_reference_for_parameter(reader, param_id)
            if definition_reference is not None:
                row["definition_reference"] = definition_reference
        rows.append(finalize_equation_input_table_row(row))
    return _dedupe_equation_input_rows(rows)


def _definition_reference_for_parameter(
    reader: StandardsReader,
    param_id: str,
) -> dict[str, str] | None:
    from api.reference_links import _display_paragraph_label

    try:
        param = reader.load(param_id)
    except FileNotFoundError:
        return None

    introduced = param.metadata.get("introduced_by") or []
    if not introduced:
        return None

    def_node_id = str(introduced[0]).strip()
    if not def_node_id:
        return None

    paragraph = ""
    try:
        def_record = reader.load(def_node_id)
        paragraph = str(
            def_record.metadata.get("paragraph_number")
            or def_record.metadata.get("paragraph")
            or ""
        ).strip()
        label = _display_paragraph_label(paragraph) if paragraph else def_node_id
    except FileNotFoundError:
        label = def_node_id

    return {
        "node_id": def_node_id,
        "label": label,
        "paragraph": paragraph or None,
    }


def _param_input_id(reader: StandardsReader, param_id: str) -> str | None:
    if not param_id:
        return None
    try:
        param = reader.load(param_id)
    except FileNotFoundError:
        return None
    key = str(param.metadata.get("key") or param.metadata.get("input_id") or "").strip()
    return key or None


def _output_display_value(task: Task, input_id: str) -> str | None:
    from api.equation_inputs_display import format_thickness_result_display, format_value_with_unit_for_display

    if input_id in {"required_wall_thickness", "pressure_design_thickness"}:
        value = (
            task.outputs.get("t")
            or task.outputs.get("required_thickness")
            or task.outputs.get("pressure_design_thickness")
        )
        if value is None:
            return None
        return format_thickness_result_display(float(value), "mm")
    output_key_groups: dict[str, tuple[str, ...]] = {
        "allowable_stress": ("allowable_stress", "S"),
        "weld_joint_efficiency": ("weld_joint_efficiency", "E"),
        "weld_joint_strength_reduction_factor_W": ("weld_joint_strength_reduction_factor_W", "W"),
        "temperature_coefficient_Y": ("temperature_coefficient_Y", "Y"),
        "internal_design_gage_pressure": ("internal_design_gage_pressure", "P"),
        "outside_diameter": ("outside_diameter", "D"),
    }
    for key in output_key_groups.get(input_id, ()):
        raw = task.outputs.get(key)
        if raw is None:
            continue
        formatted = _input_display_value(task, input_id)
        if formatted:
            return formatted
        unit = str(task.outputs.get(f"{key}_unit") or "")
        if isinstance(raw, (int, float)):
            return format_value_with_unit_for_display(float(raw), unit or None) or str(raw)
        return str(raw)
    return None


def _equation_display(metadata: dict[str, Any]) -> str:
    display = metadata.get("display_latex") or metadata.get("sympy")
    if display:
        return str(display).strip()
    nested = metadata.get("display")
    if isinstance(nested, dict):
        text = nested.get("text") or nested.get("latex")
        if text:
            return str(text).strip()
    if isinstance(nested, str):
        return nested.strip()
    return ""


def _display_to_latex(display: str) -> str:
    import re

    text = display.strip()
    if " = " in text and " / " in text:
        left, right = text.split(" = ", 1)
        numerator, denominator = right.split(" / ", 1)
        return f"{left.strip()} = \\frac{{{numerator.strip()}}}{{{denominator.strip()}}}"
    return re.sub(r"\s+", " ", text)
