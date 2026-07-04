"""Build ordered display output blocks for the desktop UI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from engine.state.goal_projection import planning_projection
from api.equation_inputs_display import (
    build_formula_inputs_input_table,
    build_mawp_formula_inputs_input_table,
    build_mawp_pressure_design_input_table,
    build_mawp_substituted_equation,
    build_wall_thickness_substituted_equation,
    definitions_from_equation_variables,
    format_thickness_result_display,
    primary_formula_inputs_complete,
)
from api.node_display import build_activated_node_blocks
from api.node_provenance import definition_node_id_for_task, enrich_display_blocks_provenance
from api.workflow_bootstrap import resolve_activated_definition_node
from api.workflow_timeline import is_mawp_task, is_pipe_wall_thickness_task
from engine.reference.formula_display import (
    load_equation_context,
    resolve_equation_display_variables,
)
from engine.reference.standards_reader import StandardsReader
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.fact import FactClass, ValidationStatus, fact_scalar_value
from models.task import Task, TaskStatus

_NODE_REFERENCES: dict[str, dict[str, str]] = {
    "304.1.2-a": {
        "standard": "ASME B31.3",
        "paragraph": "304.1.2",
        "title": "Straight Pipe Under Internal Pressure",
        "excerpt": "The minimum required wall thickness for straight pipe under internal pressure shall be computed.",
    },
    "B313-table-A-1": {
        "standard": "ASME B31.3",
        "paragraph": "Table A-1",
        "title": "Allowable Stress Lookup",
        "excerpt": "Allowable stress values are selected from Table A-1 for the design material and temperature.",
    },
    "B313-MAWP-CALCULATION": {
        "standard": "ASME B31.3",
        "paragraph": "304.1.2",
        "title": "Maximum Allowable Working Pressure",
        "excerpt": "MAWP for straight pipe under internal pressure using the thin-wall equation.",
    },
}

_RESULT_KEYS: tuple[tuple[str, str, str], ...] = (
    ("required_thickness", "Required Thickness", "mm"),
    ("t", "Required Thickness", "mm"),
    ("minimum_required_thickness", "Minimum Required Pipe Wall Thickness", "mm"),
    ("t_m", "Minimum Required Pipe Wall Thickness", "mm"),
    ("mawp", "Maximum Allowable Working Pressure (MAWP)", "Pa"),
    ("MAWP", "Maximum Allowable Working Pressure (MAWP)", "Pa"),
)

_MAWP_FORMULA = "MAWP = 2SEWt / (D - 2Yt)"
_MAWP_PRESSURE_DESIGN_FORMULA = "t = t_actual - c"


_WALL_THICKNESS_FORMULA = "t = PD / 2(SEW + PY)"


def build_display_outputs(
    task: Task,
    *,
    standards_root: Path | None = None,
    reader: StandardsReader | None = None,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    planning = planning_projection(task)

    resolved_reader = reader or _reader_for(standards_root)
    resolved_standards_root = standards_root or resolved_reader.standards_root
    trace = task.outputs.get("_execution_trace")
    has_trace = isinstance(trace, list) and bool(trace)

    if is_pipe_wall_thickness_task(task):
        return _build_pipe_wall_display_outputs(
            task,
            planning,
            resolved_reader,
            trace if has_trace else None,
            has_trace=has_trace,
            standards_root=resolved_standards_root,
        )

    if is_mawp_task(task):
        return _build_mawp_display_outputs(
            task,
            planning,
            resolved_reader,
            trace if has_trace else None,
            has_trace=has_trace,
        )

    blocks.extend(_activated_definition_blocks(task, planning, resolved_reader))

    for warning in task.warnings:
        blocks.append(_warning_block(warning))

    blocks.extend(_result_blocks(task))

    if has_trace:
        blocks.extend(_blocks_from_execution_trace(trace, task))

    status_block = _planning_status_block(task, planning)
    if status_block:
        blocks.append(status_block)

    return _finalize_display_blocks(blocks, resolved_reader, task=task, planning=planning)


def _dedupe_blocks_by_id(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for block in blocks:
        block_id = str(block.get("id") or "")
        if block_id and block_id in seen:
            continue
        if block_id:
            seen.add(block_id)
        deduped.append(block)
    return deduped


def _finalize_display_blocks(
    blocks: list[dict[str, Any]],
    reader: StandardsReader,
    *,
    task: Task | None = None,
    planning: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    default_node_id = None
    if task is not None:
        default_node_id = definition_node_id_for_task(task, reader, planning)
    enrich_display_blocks_provenance(blocks, reader, default_node_id=default_node_id)
    return _dedupe_blocks_by_id(blocks)


def _reader_for(standards_root: Path | None) -> StandardsReader:
    if standards_root is not None:
        return StandardsReader(standards_root, standard="asme_b31.3")
    project_root = Path(__file__).resolve().parent.parent
    return StandardsReader(project_root / "standards", standard="asme_b31.3")


def _activated_definition_blocks(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    node_id = planning.get("active_definition_node")
    if not node_id:
        workflow_id = _task_workflow_id(task)
        if workflow_id:
            node_id = resolve_activated_definition_node(reader, workflow_id)
    if not node_id:
        for candidate in task.active_nodes:
            try:
                if str(reader.load(candidate).metadata.get("type", "")) == "definition":
                    node_id = candidate
                    break
            except FileNotFoundError:
                continue
    if not node_id:
        return []
    return build_activated_node_blocks(reader, str(node_id))


def _path_calculation_preview_blocks(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
    *,
    trace: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """After path expansion, preview the selected calculation node's governing equation."""
    selected_node = _resolve_calculation_node_id(task, planning, trace)
    if not selected_node:
        return []

    reference = _NODE_REFERENCES.get(str(selected_node))
    blocks: list[dict[str, Any]] = []
    if reference:
        blocks.append(_path_preview_intro_block(str(selected_node), reference))

    context = load_equation_context(reader, str(selected_node))
    display = context.get("display")
    if display:
        resolved = resolve_equation_display_variables(reader, str(selected_node))
        definition_overrides = definitions_from_equation_variables(resolved.get("variables"))
        equation_block: dict[str, Any] = {
            "id": f"path-preview-equation-{selected_node}",
            "type": "equation",
            "title": None,
            "content": _display_to_latex(str(display)),
            "display": str(display),
            "input_table": build_formula_inputs_input_table(
                task,
                definition_overrides=definition_overrides,
            ),
        }
        nomenclature_reference = resolved.get("nomenclature_reference")
        if nomenclature_reference:
            equation_block["nomenclature_reference"] = nomenclature_reference

        blocks.append(equation_block)

    return blocks


def _resolve_calculation_node_id(
    task: Task,
    planning: dict[str, Any],
    trace: list[Any] | None,
) -> str | None:
    path = planning.get("path_decision") or {}
    if isinstance(path, dict) and path.get("selected_node"):
        return str(path["selected_node"])

    loading = task.fact_store.active_fact("pressure_loading")
    loading_value = fact_scalar_value(loading) if loading is not None else None
    if loading_value == "internal_pressure":
        return "304.1.2-a"
    if loading_value == "external_pressure":
        return "B313-304.1.3"

    if isinstance(trace, list):
        for entry in trace:
            if not isinstance(entry, dict):
                continue
            node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
            if node_trace.get("calculation"):
                node_id = entry.get("node_id")
                if node_id:
                    return str(node_id)
    return None


def _build_mawp_display_outputs(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
    trace: list[Any] | None,
    *,
    has_trace: bool,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    if _mawp_calculated(task, has_trace=has_trace):
        blocks.extend(_mawp_equation_preview_blocks(task, reader))
        substituted = _mawp_substituted_equation_block(trace)
        if substituted:
            blocks.append(substituted)
        conclusion = _mawp_conclusion_block(task)
        if conclusion:
            blocks.append(conclusion)
        return _finalize_display_blocks(blocks, reader, task=task, planning=planning)

    blocks.extend(_activated_definition_blocks(task, planning, reader))
    blocks.extend(_mawp_equation_preview_blocks(task, reader))
    status_block = _planning_status_block(task, planning)
    if status_block:
        blocks.append(status_block)
    return _finalize_display_blocks(blocks, reader, task=task, planning=planning)


def _mawp_calculated(task: Task, *, has_trace: bool) -> bool:
    if not has_trace:
        return False
    return task.outputs.get("mawp") is not None or task.outputs.get("MAWP") is not None


def _mawp_equation_preview_blocks(task: Task, reader: StandardsReader) -> list[dict[str, Any]]:
    del reader
    blocks: list[dict[str, Any]] = []
    reference = _NODE_REFERENCES.get("B313-MAWP-CALCULATION")
    if reference:
        blocks.append(_path_preview_intro_block("B313-MAWP-CALCULATION", reference))

    blocks.append(
        {
            "id": "mawp-pressure-design-equation",
            "type": "equation",
            "title": None,
            "content": _display_to_latex(_MAWP_PRESSURE_DESIGN_FORMULA),
            "display": _MAWP_PRESSURE_DESIGN_FORMULA,
            "input_table": build_mawp_pressure_design_input_table(task),
        }
    )
    blocks.append(
        {
            "id": "mawp-formula-equation",
            "type": "equation",
            "title": None,
            "content": _display_to_latex(_MAWP_FORMULA),
            "display": _MAWP_FORMULA,
            "input_table": build_mawp_formula_inputs_input_table(task),
            "nomenclature_reference": {
                "standard": "ASME B31.3",
                "paragraph": "304.1.2",
            },
        }
    )
    return blocks


def _mawp_substituted_equation_block(trace: list[Any] | None) -> dict[str, Any] | None:
    if not isinstance(trace, list):
        return None
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("node_id")) != "B313-MAWP-CALCULATION":
            continue
        node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
        calc = node_trace.get("calculation") if isinstance(node_trace.get("calculation"), dict) else {}
        variables_si = node_trace.get("variables_si") if isinstance(node_trace.get("variables_si"), dict) else {}
        final = calc.get("final_result") if isinstance(calc.get("final_result"), dict) else {}
        value = final.get("value")
        if value is None or not variables_si:
            return None
        display, latex = build_mawp_substituted_equation(
            result_value_pa=float(value),
            variables_si={k: float(v) for k, v in variables_si.items()},
        )
        return {
            "id": "mawp-substituted-equation",
            "type": "equation",
            "title": None,
            "content": latex,
            "display": display,
        }
    return None


def _mawp_conclusion_block(task: Task) -> dict[str, Any] | None:
    mawp = task.outputs.get("mawp")
    if mawp is None:
        mawp = task.outputs.get("MAWP")
    if mawp is None:
        return None
    from api.equation_inputs_display import format_value_with_unit_for_display

    pressure_display = format_value_with_unit_for_display(float(mawp) / 1_000_000, "MPa")
    return {
        "id": "mawp-conclusion",
        "type": "text",
        "title": None,
        "content": (
            f"Maximum Allowable Working Pressure (MAWP): {pressure_display} "
            "(per ASME B31.3 §304.1.2)."
        ),
        "variant": "body",
    }


def _build_pipe_wall_display_outputs(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
    trace: list[Any] | None,
    *,
    has_trace: bool,
    standards_root: Path,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    if _pipe_wall_t_calculated(task, has_trace=has_trace):
        blocks.extend(_path_calculation_preview_blocks(task, planning, reader, trace=trace))
        substituted = _substituted_calculation_equation_block(trace)
        if substituted:
            blocks.append(substituted)
        applicability = _thin_wall_applicability_block(task, trace)
        if applicability:
            blocks.append(applicability)
        minimum_equation = _minimum_thickness_equation_block(task)
        if minimum_equation:
            blocks.append(minimum_equation)
        conclusion = _minimum_thickness_conclusion_block(task)
        if conclusion:
            blocks.append(conclusion)
        schedule = _pipe_schedule_recommendation_block(task, standards_root)
        if schedule:
            blocks.append(schedule)
        return _finalize_display_blocks(blocks, reader, task=task, planning=planning)

    blocks.extend(_activated_definition_blocks(task, planning, reader))
    blocks.extend(_path_calculation_preview_blocks(task, planning, reader, trace=trace))
    status_block = _planning_status_block(task, planning)
    if status_block:
        blocks.append(status_block)
    return _finalize_display_blocks(blocks, reader, task=task, planning=planning)


def _pipe_wall_t_calculated(task: Task, *, has_trace: bool) -> bool:
    if not has_trace:
        return False
    return task.outputs.get("required_thickness") is not None or task.outputs.get("t") is not None


def _pipe_wall_tm_complete(task: Task) -> bool:
    return (
        task.outputs.get("minimum_required_thickness") is not None
        or task.outputs.get("t_m") is not None
    )


def _required_thickness_summary_block(task: Task) -> dict[str, Any] | None:
    thickness = task.outputs.get("required_thickness")
    if thickness is None:
        thickness = task.outputs.get("t")
    if thickness is None:
        return None
    unit = str(
        task.outputs.get("required_thickness_unit")
        or task.outputs.get("t_unit")
        or task.outputs.get("thickness_unit")
        or "mm"
    )
    from api.equation_inputs_display import format_thickness_result_display

    return {
        "id": "required-thickness-summary",
        "type": "text",
        "title": None,
        "content": f"Required wall thickness: {format_thickness_result_display(float(thickness), unit)}.",
        "variant": "body",
    }


def _minimum_thickness_equation_block(task: Task) -> dict[str, Any] | None:
    thickness = task.outputs.get("required_thickness")
    if thickness is None:
        thickness = task.outputs.get("t")
    if thickness is None:
        return None

    from api.equation_inputs_display import build_minimum_thickness_equation

    t_value = float(thickness)
    unit = str(
        task.outputs.get("required_thickness_unit")
        or task.outputs.get("t_unit")
        or task.outputs.get("thickness_unit")
        or "mm"
    )
    c_value = _corrosion_allowance_mm(task)
    t_m_value = task.outputs.get("t_m")
    if t_m_value is None:
        t_m_value = task.outputs.get("minimum_required_thickness")

    display, latex = build_minimum_thickness_equation(
        t_value=t_value,
        c_value=c_value,
        t_m_value=float(t_m_value) if isinstance(t_m_value, (int, float)) else None,
        unit=unit,
    )
    return {
        "id": "minimum-thickness-equation",
        "type": "equation",
        "title": None,
        "content": latex,
        "display": display,
    }


def _minimum_thickness_conclusion_block(task: Task) -> dict[str, Any] | None:
    if not _pipe_wall_tm_complete(task):
        return None
    t_m = task.outputs.get("t_m")
    if t_m is None:
        t_m = task.outputs.get("minimum_required_thickness")
    if t_m is None:
        return None

    from api.equation_inputs_display import format_thickness_result_display

    unit = str(
        task.outputs.get("t_m_unit")
        or task.outputs.get("minimum_required_thickness_unit")
        or "mm"
    )
    return {
        "id": "minimum-thickness-conclusion",
        "type": "text",
        "title": None,
        "content": (
            f"Minimum required pipe wall thickness is "
            f"{format_thickness_result_display(float(t_m), unit)}. "
            "The selected pipe wall thickness must be not less than t_m per §304.1.1-a."
        ),
        "variant": "body",
    }


def _pipe_schedule_recommendation_block(
    task: Task,
    standards_root: Path,
) -> dict[str, Any] | None:
    if not _pipe_wall_tm_complete(task):
        return None

    from engine.executor.pipe_schedule_recommendation import (
        format_schedule_recommendation_text,
        recommend_pipe_schedule_for_task,
    )

    recommendation = recommend_pipe_schedule_for_task(task, standards_root)
    if recommendation is None:
        return None

    return {
        "id": "pipe-schedule-recommendation",
        "type": "text",
        "title": None,
        "content": format_schedule_recommendation_text(recommendation),
        "variant": "body",
        "pipe_schedule_recommendation": {
            "nps": recommendation.nps,
            "schedule": recommendation.schedule,
            "wall_thickness_mm": recommendation.wall_thickness_mm,
            "minimum_required_thickness_mm": recommendation.minimum_required_thickness_mm,
            "standard": recommendation.standard_display,
            "standard_slug": recommendation.standard_slug,
            "table_id": recommendation.table_id,
        },
    }


def _corrosion_allowance_mm(task: Task) -> float | None:
    from engine.executor.unit_manager import prepare_fact

    fact = task.fact_store.active_fact("corrosion_allowance")
    if fact is None or fact_scalar_value(fact) is None:
        return None
    if fact.fact_class == FactClass.DEFAULT_CONFIRMED and fact.validation.status == ValidationStatus.PENDING:
        return None
    return float(fact_scalar_value(prepare_fact(fact)))


def _pipe_wall_calculation_complete(task: Task, *, has_trace: bool) -> bool:
    return _pipe_wall_t_calculated(task, has_trace=has_trace)


def _thin_wall_applicability_block(task: Task, trace: list[Any]) -> dict[str, Any] | None:
    """Show §304.1.2 thin-wall criterion result after thickness is calculated."""
    if trace is None:
        return None
    thin_wall = task.outputs.get("thin_wall")
    if thin_wall is None:
        return None
    if not _pipe_wall_t_calculated(task, has_trace=True):
        return None

    if bool(thin_wall):
        content = "ASME B31.3 paragraph §304.1.2 condition (t < D/6) is valid."
    else:
        content = (
            "ASME B31.3 paragraph §304.1.2 condition (t < D/6) is NOT valid. "
            "continuing with thick wall condition (t > D/6)"
        )

    return {
        "id": "thin-wall-applicability-check",
        "type": "text",
        "title": None,
        "content": content,
        "variant": "body",
    }


def _substituted_calculation_equation_block(trace: list[Any]) -> dict[str, Any] | None:
    calc_entry = _wall_thickness_calculation_trace_entry(trace)
    if not calc_entry:
        return None

    node_trace = calc_entry.get("trace") if isinstance(calc_entry.get("trace"), dict) else {}
    substitution = node_trace.get("substitution")
    if isinstance(substitution, str) and substitution.strip():
        display = substitution.strip()
        return {
            "id": "path-calculation-substituted-equation",
            "type": "equation",
            "title": None,
            "content": display,
            "display": display,
        }

    calculation = node_trace.get("calculation")
    if not isinstance(calculation, dict):
        return None

    variables_si = node_trace.get("variables_si")
    if not isinstance(variables_si, dict):
        return None

    final = calculation.get("final_result")
    if not isinstance(final, dict) or final.get("value") is None:
        return None

    variables = {
        key: float(value)
        for key, value in variables_si.items()
        if isinstance(value, (int, float))
    }
    if not {"P", "D", "S", "E", "W", "Y"}.issubset(variables):
        return None

    result_unit = str(final.get("unit") or "mm")
    display, latex = build_wall_thickness_substituted_equation(
        result_value=float(final["value"]),
        result_unit=result_unit,
        variables_si=variables,
    )

    return {
        "id": "path-calculation-substituted-equation",
        "type": "equation",
        "title": None,
        "content": latex,
        "display": display,
    }


def _wall_thickness_calculation_trace_entry(trace: list[Any]) -> dict[str, Any] | None:
    preferred = ("B313-eq-wall-thickness", "304.1.2-a", "B313-304.1.3")
    for node_id in preferred:
        for entry in trace:
            if isinstance(entry, dict) and entry.get("node_id") == node_id:
                node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
                if node_trace.get("calculation"):
                    return entry

    for entry in trace:
        if not isinstance(entry, dict):
            continue
        node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
        if node_trace.get("calculation") or node_trace.get("substitution"):
            return entry
    return None


def _path_preview_intro_block(selected_node: str, reference: dict[str, str]) -> dict[str, Any]:
    paragraph = str(reference.get("paragraph", "")).strip()
    excerpt = str(reference.get("excerpt", "")).strip().rstrip(".")
    label = f"§{paragraph}" if paragraph else selected_node
    return {
        "id": f"path-preview-intro-{selected_node}",
        "type": "text",
        "title": None,
        "content": f"{excerpt} based on",
        "content_suffix": " with the following equation:",
        "variant": "body",
        "reference_links": [
            {
                "node_id": selected_node,
                "label": label,
                "paragraph": paragraph or None,
            }
        ],
        "reference_links_placement": "inline",
    }


def _task_workflow_id(task: Task) -> str:
    workflow = task.outputs.get("workflow")
    return str(workflow) if workflow else ""


def _planning_status_block(task: Task, planning: dict[str, Any]) -> dict[str, Any] | None:
    action = planning.get("action")
    if not action and task.status != TaskStatus.AWAITING_INPUT:
        return None

    if action == "request_input" or task.status == TaskStatus.AWAITING_INPUT:
        return {
            "id": "planning-status",
            "type": "text",
            "title": "Task status:",
            "content": "Complete the fields below to continue.",
            "variant": "body",
        }

    parts: list[str] = []
    if action:
        parts.append(f"Planner action: {action}.")
    elif task.status == TaskStatus.COMPLETED:
        parts.append("Calculation workflow completed.")

    if not parts:
        return None

    return {
        "id": "planning-status",
        "type": "text",
        "title": "Task status:",
        "content": " ".join(parts),
        "variant": "body",
    }


def _warning_block(message: str) -> dict[str, Any]:
    return {
        "id": f"warning-{abs(hash(message)) % 10_000}",
        "type": "text",
        "title": "Warning",
        "content": message,
        "variant": "warning",
    }


def _result_blocks(task: Task) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    seen_labels: set[str] = set()

    for key, label, default_unit in _RESULT_KEYS:
        if key not in task.outputs or label in seen_labels:
            continue
        value = task.outputs[key]
        if value is None:
            continue
        seen_labels.add(label)
        unit = str(task.outputs.get(f"{key}_unit") or default_unit)
        status = "pass" if task.status == TaskStatus.COMPLETED else "info"
        blocks.append(
            {
                "id": f"result-{key}",
                "type": "result",
                "title": label,
                "label": label,
                "value": _format_number(value),
                "unit": unit,
                "status": status,
            }
        )

    return blocks


def _blocks_from_execution_trace(trace: list[Any], task: Task) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    for index, entry in enumerate(trace):
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node_id") or f"node-{index}")
        node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
        outputs = entry.get("outputs") if isinstance(entry.get("outputs"), dict) else {}

        reference = _NODE_REFERENCES.get(node_id)
        if reference:
            blocks.append(
                {
                    "id": f"reference-{node_id}",
                    "type": "reference",
                    "title": reference["title"],
                    "standard": reference["standard"],
                    "paragraph": reference.get("paragraph"),
                    "excerpt": reference.get("excerpt"),
                    "source_node": node_id,
                }
            )

        calculation = node_trace.get("calculation")
        if isinstance(calculation, dict):
            blocks.extend(_calculation_blocks(node_id, calculation, outputs))

        lookup = node_trace.get("lookup")
        if isinstance(lookup, dict):
            table_block = _lookup_table_block(node_id, lookup)
            if table_block:
                blocks.append(table_block)

    graph_block = _intermediate_graph_block(trace)
    if graph_block:
        blocks.append(graph_block)

    if task.status == TaskStatus.COMPLETED and not any(block["type"] == "result" for block in blocks):
        blocks.extend(_result_blocks(task))

    return blocks


def _calculation_blocks(
    node_id: str,
    calculation: dict[str, Any],
    outputs: dict[str, Any],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    formula = str(calculation.get("formula_display") or _WALL_THICKNESS_FORMULA)
    variables = _variable_rows(calculation, outputs)

    blocks.append(
        {
            "id": f"equation-{node_id}",
            "type": "equation",
            "title": "Governing equation",
            "content": _display_to_latex(formula),
            "display": formula,
            "variables": variables,
            "result": _equation_result(outputs),
        }
    )

    steps = calculation.get("steps")
    if isinstance(steps, list) and steps:
        rows: list[dict[str, Any]] = []
        for step_index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            result = step.get("result")
            rows.append(
                {
                    "step": step.get("name") or f"Step {step_index + 1}",
                    "description": step.get("description") or "",
                    "result": _format_step_result(result),
                }
            )
        if rows:
            blocks.append(
                {
                    "id": f"table-steps-{node_id}",
                    "type": "table",
                    "title": "Calculation steps",
                    "columns": [
                        {"key": "step", "label": "Step", "sortable": True},
                        {"key": "description", "label": "Description", "sortable": True},
                        {"key": "result", "label": "Result", "sortable": False},
                    ],
                    "rows": rows,
                    "searchable": True,
                }
            )

    intermediates = calculation.get("intermediate_values")
    if isinstance(intermediates, dict) and intermediates:
        rows = [
            {"symbol": key, "value": _format_number(value)}
            for key, value in intermediates.items()
            if isinstance(value, (int, float))
        ]
        if rows:
            blocks.append(
                {
                    "id": f"table-intermediates-{node_id}",
                    "type": "table",
                    "title": "Intermediate values",
                    "columns": [
                        {"key": "symbol", "label": "Symbol", "sortable": True},
                        {"key": "value", "label": "Value", "sortable": True},
                    ],
                    "rows": rows,
                    "searchable": False,
                }
            )

    return blocks


def _lookup_table_block(node_id: str, lookup: dict[str, Any]) -> dict[str, Any] | None:
    rows = lookup.get("rows") or lookup.get("matches")
    if not isinstance(rows, list) or not rows:
        return None

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized_rows.append({str(key): value for key, value in row.items()})
        else:
            normalized_rows.append({"value": row})

    if not normalized_rows:
        return None

    columns = [{"key": key, "label": key.replace("_", " ").title(), "sortable": True} for key in normalized_rows[0]]
    return {
        "id": f"table-lookup-{node_id}",
        "type": "table",
        "title": "Lookup results",
        "columns": columns,
        "rows": normalized_rows,
        "searchable": True,
    }


def _intermediate_graph_block(trace: list[Any]) -> dict[str, Any] | None:
    points: list[dict[str, Any]] = []

    for entry in trace:
        if not isinstance(entry, dict):
            continue
        node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
        intermediates = node_trace.get("intermediates")
        if isinstance(intermediates, dict):
            for key, value in intermediates.items():
                if isinstance(value, (int, float)):
                    points.append({"x": key, "y": float(value)})

        calculation = node_trace.get("calculation")
        if isinstance(calculation, dict):
            final = calculation.get("final_result")
            if isinstance(final, dict) and isinstance(final.get("value"), (int, float)):
                points.append({"x": "t", "y": float(final["value"])})

    if len(points) < 2:
        return None

    return {
        "id": "graph-intermediates",
        "type": "graph",
        "title": "Calculation terms",
        "chart_type": "bar",
        "x_label": "Term",
        "y_label": "SI value",
        "series": [{"name": "Values", "points": points}],
    }


def _variable_rows(calculation: dict[str, Any], outputs: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    variables = calculation.get("variables")
    if isinstance(variables, dict):
        for symbol, payload in variables.items():
            if not isinstance(payload, dict):
                continue
            rows.append(
                {
                    "symbol": str(payload.get("symbol") or symbol),
                    "name": str(payload.get("description") or payload.get("name") or symbol),
                    "value": _format_number(payload.get("value")) if payload.get("value") is not None else None,
                    "unit": payload.get("unit"),
                }
            )

    if not rows and outputs:
        for key, value in outputs.items():
            if key in {"thin_wall"}:
                continue
            if isinstance(value, (int, float, str)):
                rows.append({"symbol": key, "name": key.replace("_", " ").title(), "value": _format_number(value)})

    return rows


def _equation_result(outputs: dict[str, Any]) -> dict[str, Any] | None:
    for key, label, unit in _RESULT_KEYS:
        if key in outputs and outputs[key] is not None:
            return {
                "label": label,
                "value": _format_number(outputs[key]),
                "unit": unit,
            }
    return None


def _format_step_result(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, dict):
        parts = [f"{key}={_format_number(value)}" for key, value in result.items()]
        return ", ".join(parts)
    return str(result)


def _format_number(value: Any) -> str:
    if isinstance(value, float):
        text = f"{value:.6g}"
        return text
    return str(value)


def _display_to_latex(display: str) -> str:
    text = display.strip()
    if " = " in text and " / " in text:
        left, right = text.split(" = ", 1)
        numerator, denominator = right.split(" / ", 1)
        return f"{left.strip()} = \\frac{{{numerator.strip()}}}{{{denominator.strip()}}}"
    return re.sub(r"\s+", " ", text)
