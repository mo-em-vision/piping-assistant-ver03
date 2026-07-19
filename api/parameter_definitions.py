"""Build UI parameter definitions and handle structured input submission."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.executor.allowable_stress_resolver import apply_allowable_stress_lookup
from engine.executor.coefficient_lookup import apply_coefficient_lookups
from engine.executor.metallurgical_group_resolver import apply_metallurgical_group_lookup
from engine.executor.mawp_geometry_resolver import (
    apply_pipe_schedule_lookup,
    store_outside_diameter_resolution_branch,
)
from engine.graph.resolution_branches import (
    clear_conflicting_branch_facts,
    clear_outside_diameter_lookup_output,
    resolution_branch_fact_key,
)
from engine.executor.nps_input_resolver import apply_nominal_pipe_size_lookup
from engine.executor.unit_manager import normalize_unit
from engine.state.goal_projection import planning_projection
from engine.reference.material_resolver import canonical_material_id
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.state.state_manager import TaskStateManager
from engine.state.task_facts import deactivate_fact, store_system_categorical_fact
from engine.inspection.performance_trace import perf_span
from models.fact import FactClass, ValidationStatus, fact_from_user_submission, fact_scalar_value
from models.task import Task

from api.parameter_edit import active_edit_parameter, clear_edit_session
from api.node_provenance import param_node_index, parameter_input_provenance, provenance_for_node
from api.workflow_timeline import (
    is_mawp_task,
    is_pipe_wall_thickness_task,
    revealed_input_ids,
    revealed_pipe_wall_input_ids,
    submittable_parameter_ids,
)
from engine.messaging.parameter_input_prompt import build_parameter_input_prompt
from engine.messaging.parameter_prompt_context import parameter_metadata_context, parameter_prompt_from_metadata
from engine.navigation.active_input_projection import (
    composer_parameter_ids_for_task,
    uses_planner_input_projection,
)
from engine.reference.parameter_composer_spec import build_composer_parameter_spec
from engine.reference.table_options_resolver import resolve_table_dropdown_options
from engine.reference.parameter_keys import (
    LEGACY_PARAMETER_KEY_ALIASES,
    active_fact_for_key,
    api_parameter_id,
    canonical_parameter_key,
    is_material_grade_parameter,
)
from engine.reference.standards_reader import StandardsReader

_DIAMETER_INPUT_PARAMETERS = frozenset({"nominal_pipe_size", "outside_diameter", "inside_diameter"})

def _parameter_status(task: Task, parameter_id: str) -> str:
    if active_edit_parameter(task) == parameter_id:
        return "pending"

    existing = active_fact_for_key(task, api_parameter_id(parameter_id))
    if existing is None:
        return "pending"
    if (
        existing.fact_class == FactClass.DEFAULT_CONFIRMED
        and existing.validation.status == ValidationStatus.PENDING
    ):
        return "confirmation_required"
    if existing.validation.status in {ValidationStatus.CONFIRMED, ValidationStatus.VALIDATED}:
        return "confirmed"
    if fact_scalar_value(existing) is not None:
        return "pending"
    return "pending"


def _current_value(task: Task, parameter_id: str) -> Any:
    existing = active_fact_for_key(task, api_parameter_id(parameter_id))
    if existing is None:
        return None
    return fact_scalar_value(existing)


def build_parameter_definitions(
    task: Task,
    *,
    reader: StandardsReader | None = None,
) -> list[dict[str, Any]]:
    planning = planning_projection(task)

    requested_ids = _requested_parameter_ids(task, planning, reader=reader)
    if not uses_planner_input_projection(task) and _DIAMETER_INPUT_PARAMETERS & set(requested_ids):
        from api.workflow_timeline import _pipe_wall_uses_inside_diameter, is_pipe_wall_thickness_task

        for diameter_id in _DIAMETER_INPUT_PARAMETERS:
            if diameter_id in requested_ids:
                continue
            if (
                is_pipe_wall_thickness_task(task)
                and diameter_id == "inside_diameter"
                and not _pipe_wall_uses_inside_diameter(task)
            ):
                continue
            if (
                is_pipe_wall_thickness_task(task)
                and diameter_id in {"nominal_pipe_size", "outside_diameter"}
                and _pipe_wall_uses_inside_diameter(task)
            ):
                continue
            requested_ids = [*requested_ids, diameter_id]
    submittable_ids = set(submittable_parameter_ids(task, planning))
    canonical_submittable_ids = {canonical_parameter_key(item) for item in submittable_ids}
    param_index = param_node_index(reader, task) if reader is not None else {}

    parameters: list[dict[str, Any]] = []
    editing = active_edit_parameter(task)
    for parameter_id in requested_ids:
        parameter_id = api_parameter_id(parameter_id)
        spec = build_composer_parameter_spec(
            parameter_id,
            reader=reader,
            param_index=param_index,
            task=task,
            standards_root=reader.standards_root if reader is not None else None,
        )
        options = list(spec.get("options") or [])
        if reader is not None:
            table_options = resolve_table_dropdown_options(
                task,
                parameter_id,
                standards_root=reader.standards_root,
            )
            if table_options:
                options = table_options
        if options and spec.get("type") not in {"material", "checkbox"}:
            spec["type"] = "dropdown"
        existing = active_fact_for_key(task, parameter_id)
        metadata_ctx = parameter_metadata_context(reader, parameter_id) if reader is not None else None
        payload: dict[str, Any] = {
            "name": parameter_id,
            "label": spec["label"],
            "type": spec["type"],
            "required": True,
            "units": list(spec.get("units") or []),
            "default_unit": spec.get("default_unit", "dimensionless"),
            "default_value": existing.default if existing and existing.default is not None else spec.get("default_value"),
            "value": _current_value(task, parameter_id),
            "options": options or None,
            "validation": spec.get("validation"),
            "status": _parameter_status(task, parameter_id),
            "requires_confirmation": bool(existing.requires_confirmation) if existing else False,
            "guidance": _parameter_guidance(task, planning, parameter_id, reader),
            "editing": editing == parameter_id,
            "submittable": canonical_parameter_key(parameter_id) in canonical_submittable_ids,
        }
        if metadata_ctx is not None:
            if metadata_ctx.prompt:
                payload["prompt"] = metadata_ctx.prompt
            if metadata_ctx.help_text:
                payload["help_text"] = metadata_ctx.help_text
        if spec.get("resolution_ui"):
            payload["resolution_ui"] = spec["resolution_ui"]
        if reader is not None:
            provenance = parameter_input_provenance(reader, task, parameter_id)
            if provenance is None:
                param_node_id = param_index.get(parameter_id)
                if param_node_id:
                    guidance = payload.get("guidance")
                    source_field = "user_prompt.prompt" if guidance else "title"
                    provenance = provenance_for_node(reader, param_node_id, source_field=source_field)
            if provenance:
                payload["provenance"] = provenance
        parameters.append(payload)

    return parameters


def _requested_parameter_ids(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    if uses_planner_input_projection(task):
        return composer_parameter_ids_for_task(
            task,
            planning,
            reader=reader,
            editing_parameter=active_edit_parameter(task),
        )

    if is_pipe_wall_thickness_task(task) or is_mawp_task(task):
        requested = revealed_input_ids(task, planning, reader=reader)
        editing = active_edit_parameter(task)
        if editing and editing not in requested:
            requested = [editing, *requested]
        return requested

    requested_ids: list[str] = []
    for key in ("missing_assumptions", "missing_execution_assumptions", "missing_inputs"):
        for item in planning.get(key) or []:
            item_id = str(item)
            if item_id not in requested_ids:
                requested_ids.append(item_id)

    for input_id, existing in task.fact_store.active_facts().items():
        if (
            existing.fact_class == FactClass.DEFAULT_CONFIRMED
            and existing.validation.status == ValidationStatus.PENDING
            and input_id not in requested_ids
        ):
            requested_ids.append(input_id)

    return requested_ids


def _parameter_guidance(
    task: Task,
    planning: dict[str, Any],
    parameter_id: str,
    reader: StandardsReader | None,
) -> str | None:
    if reader is not None:
        prompt = build_parameter_input_prompt(reader, task, parameter_id, planning=planning)
        if prompt:
            return prompt

    phase_missing = planning.get("phase_missing") or {}
    phase_questions = planning.get("phase_questions") or {}
    if not isinstance(phase_missing, dict) or not isinstance(phase_questions, dict):
        return _parameter_prompt_from_metadata(parameter_id, reader)
    for phase, fields in phase_missing.items():
        if not isinstance(fields, list):
            continue
        canonical_fields = [api_parameter_id(str(item)) for item in fields]
        if api_parameter_id(parameter_id) not in canonical_fields:
            continue
        questions = phase_questions.get(phase)
        if isinstance(questions, dict):
            prompt = questions.get(parameter_id) or questions.get(api_parameter_id(parameter_id))
            if isinstance(prompt, str) and prompt.strip():
                return prompt.strip()
            continue
        if isinstance(questions, list):
            index = canonical_fields.index(api_parameter_id(parameter_id))
            if index < len(questions):
                prompt = questions[index]
                if isinstance(prompt, str) and prompt.strip():
                    return prompt.strip()
    return _parameter_prompt_from_metadata(parameter_id, reader)


def _parameter_prompt_from_metadata(
    parameter_id: str,
    reader: StandardsReader | None,
) -> str | None:
    ctx = parameter_metadata_context(reader, parameter_id)
    return parameter_prompt_from_metadata(ctx)


def _task_workflow_id(task: Task) -> str:
    workflow = task.outputs.get("workflow")
    return str(workflow) if workflow else ""


def _coerce_value(parameter: dict[str, Any], raw_value: Any) -> Any:
    param_type = parameter["type"]
    if param_type == "checkbox":
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, str):
            return raw_value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(raw_value)
    if param_type == "number":
        if raw_value is None or raw_value == "":
            raise ValueError("A numeric value is required.")
        return float(raw_value)
    if param_type == "multi_select":
        if not isinstance(raw_value, list):
            raise ValueError("Expected a list of selected values.")
        return [str(item) for item in raw_value]
    return raw_value


def _resolve_pipe_construction_type_value(
    raw_value: Any,
    options: list[Any],
) -> str:
    """Map short aliases (e.g. seamless) to dropdown option labels."""
    from engine.reference.coefficient_resolver import _normalize_joint_category

    value = str(raw_value).strip()
    allowed = {
        str(item["value"] if isinstance(item, dict) else item).strip()
        for item in options
        if item is not None
    }
    if value in allowed:
        return value
    target = _normalize_joint_category(value)
    for option in allowed:
        if _normalize_joint_category(option) == target:
            return option
    return value


def _validate_against_spec(parameter: dict[str, Any], value: Any) -> None:
    validation = parameter.get("validation") or {}
    if parameter["type"] == "number" and isinstance(value, (int, float)):
        minimum = validation.get("min")
        maximum = validation.get("max")
        if minimum is not None and value < minimum:
            raise ValueError(f"Value must be at least {minimum}.")
        if maximum is not None and value > maximum:
            raise ValueError(f"Value must be at most {maximum}.")
    options = parameter.get("options") or []
    if options and parameter["type"] in {"dropdown", "multi_select"}:
        allowed = {item["value"] if isinstance(item, dict) else item for item in options}
        if parameter["type"] == "dropdown" and str(value) not in allowed:
            raise ValueError("Selected value is not allowed.")
        if parameter["type"] == "multi_select":
            invalid = [item for item in value if item not in allowed]
            if invalid:
                raise ValueError("One or more selected values are not allowed.")


def _canonical_submit_parameter(parameter: str) -> str:
    return canonical_parameter_key(parameter)


def _expand_allowed_parameter_ids(allowed_ids: set[str]) -> set[str]:
    expanded = set(allowed_ids)
    for legacy, target in LEGACY_PARAMETER_KEY_ALIASES.items():
        if target in allowed_ids:
            expanded.add(legacy)
        if legacy in allowed_ids:
            expanded.add(target)
    return expanded


def _definition_for_parameter(
    definitions: dict[str, dict[str, Any]],
    parameter: str,
) -> dict[str, Any] | None:
    if parameter in definitions:
        return definitions[parameter]
    for name, definition in definitions.items():
        if _canonical_submit_parameter(name) == parameter:
            return definition
    return None


def submit_task_input(
    manager: TaskStateManager,
    task_id: str,
    *,
    parameter: str,
    value: Any,
    unit: str | None,
    standards_root: Path | None = None,
) -> Task:
    with perf_span("submit_task_input", "state", notes=f"parameter={parameter}"):
        return _submit_task_input_impl(
            manager,
            task_id,
            parameter=parameter,
            value=value,
            unit=unit,
            standards_root=standards_root,
        )


def _submit_task_input_impl(
    manager: TaskStateManager,
    task_id: str,
    *,
    parameter: str,
    value: Any,
    unit: str | None,
    standards_root: Path | None = None,
) -> Task:
    task = manager.get_task(task_id)
    planning = planning_projection(task)
    original_parameter = parameter
    parameter = _canonical_submit_parameter(parameter)
    submittable = submittable_parameter_ids(task, planning)
    allowed_ids = _expand_allowed_parameter_ids(set(submittable))
    if "pipe_construction_type" in allowed_ids:
        allowed_ids.add("joint_category")
    if (
        parameter in _DIAMETER_INPUT_PARAMETERS
        and _DIAMETER_INPUT_PARAMETERS & allowed_ids
    ):
        allowed_ids |= _DIAMETER_INPUT_PARAMETERS
    branch_fact_key = resolution_branch_fact_key("outside_diameter")
    if "outside_diameter" in allowed_ids:
        allowed_ids.add(branch_fact_key)
    if original_parameter not in allowed_ids and parameter not in allowed_ids:
        raise ValueError(f"Parameter is not currently requested: {original_parameter}")

    if parameter == branch_fact_key or parameter.endswith("__resolution_branch"):
        store_system_categorical_fact(task, key=branch_fact_key, label=str(value))
        anchor_key = branch_fact_key.replace("__resolution_branch", "")
        clear_conflicting_branch_facts(task, anchor_key=anchor_key, branch_id=str(value))
        manager.replace_task(task_id, task)
        return manager.get_task(task_id)

    definitions = {
        item["name"]: item
        for item in build_parameter_definitions(
            task,
            reader=StandardsReader(standards_root) if standards_root is not None else None,
        )
    }
    definition = _definition_for_parameter(definitions, parameter)
    if definition is None:
        if parameter in submittable or canonical_parameter_key(parameter) in {
            canonical_parameter_key(item) for item in submittable
        }:
            raise AssertionError(
                f"navigation projection inconsistent: {parameter!r} is submittable "
                f"but missing from parameter definitions"
            )
        raise ValueError(f"Parameter is not currently requested: {parameter}")
    coerced = _coerce_value(definition, value)
    if parameter == "pipe_construction_type" and definition.get("options"):
        coerced = _resolve_pipe_construction_type_value(coerced, definition["options"])
    if parameter == "outside_diameter" and definition["type"] == "dropdown":
        coerced = float(coerced)
    if not (parameter == "nominal_pipe_size" and str(unit or "").strip().upper() == "DN"):
        _validate_against_spec(definition, coerced)

    if is_material_grade_parameter(parameter):
        if standards_root is None:
            raise ValueError("Standards root is required to resolve material.")
        resolved_material = canonical_material_id(str(coerced), standards_root=standards_root)
        if resolved_material is None:
            raise ValueError("Select a material from the available options.")
        coerced = resolved_material

    resolved_unit = unit or definition.get("default_unit") or "dimensionless"
    if parameter == "nominal_pipe_size":
        unit_text = str(unit or definition.get("default_unit") or "NPS").strip().upper()
        resolved_unit = "DN" if unit_text == "DN" else "NPS"
    elif definition["type"] == "number" and definition.get("units"):
        resolved_unit = normalize_unit(resolved_unit)
    elif definition["type"] == "text" and definition.get("units"):
        resolved_unit = str(resolved_unit).strip().upper()
    elif definition["type"] in {"dropdown", "checkbox", "material", "multi_select"}:
        resolved_unit = definition.get("default_unit", "dimensionless")

    original_unit = resolved_unit if resolved_unit not in {"dimensionless", "1", ""} else None
    original_value = value if not isinstance(value, bool) else None

    fact_key = canonical_parameter_key(parameter)
    fact = fact_from_user_submission(
        key=fact_key,
        value=coerced,
        unit=resolved_unit,
        task_id=task.task_id,
        workflow_id=_task_workflow_id(task) or None,
        original_value=original_value,
        original_unit=original_unit,
    )
    manager.store_input(task_id, fact)

    task = manager.get_task(task_id)
    workflow_id = _task_workflow_id(task)

    with perf_span("lookup_side_effects", "lookup", notes=f"parameter={parameter}"):
        if parameter == "outside_diameter":
            clear_outside_diameter_lookup_output(task)
            store_outside_diameter_resolution_branch(task, "direct_od")
            deactivate_fact(task, "inside_diameter")
            manager.replace_task(task_id, task)
            task = manager.get_task(task_id)

        if parameter == "inside_diameter":
            deactivate_fact(task, "outside_diameter")
            deactivate_fact(task, "nominal_pipe_size")
            manager.replace_task(task_id, task)
            task = manager.get_task(task_id)

        if parameter == "nominal_pipe_size":
            if standards_root is None:
                raise ValueError("Standards root is required to resolve nominal pipe size.")
            apply_nominal_pipe_size_lookup(task, standards_root)
            deactivate_fact(task, "inside_diameter")
            manager.replace_task(task_id, task)
            task = manager.get_task(task_id)

        if parameter == "pipe_schedule" and workflow_id == MAWP_DESIGN:
            if standards_root is None:
                raise ValueError("Standards root is required to resolve pipe schedule.")
            apply_pipe_schedule_lookup(task, standards_root)
            manager.replace_task(task_id, task)
            task = manager.get_task(task_id)

        if is_material_grade_parameter(parameter) or parameter == "design_temperature":
            if standards_root is None:
                raise ValueError("Standards root is required to resolve allowable stress.")
            apply_allowable_stress_lookup(task, standards_root)
            manager.replace_task(task_id, task)
            task = manager.get_task(task_id)

        if is_material_grade_parameter(parameter):
            if standards_root is None:
                raise ValueError("Standards root is required to resolve metallurgical group.")
            apply_metallurgical_group_lookup(task, standards_root)
            manager.replace_task(task_id, task)
            task = manager.get_task(task_id)

        if is_material_grade_parameter(parameter) or parameter in {
            "design_temperature",
            "pipe_construction_type",
            "joint_category",
        }:
            if standards_root is None:
                raise ValueError("Standards root is required to resolve weld joint coefficients.")
            apply_coefficient_lookups(task, standards_root)
            manager.replace_task(task_id, task)
            task = manager.get_task(task_id)

    if active_edit_parameter(task) == parameter:
        clear_edit_session(task)

    return manager.get_task(task_id)
