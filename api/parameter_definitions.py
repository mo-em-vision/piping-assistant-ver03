"""Build UI parameter definitions and handle structured input submission."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.executor.allowable_stress_resolver import apply_allowable_stress_lookup
from engine.executor.coefficient_lookup import apply_coefficient_lookups
from engine.executor.metallurgical_group_resolver import apply_metallurgical_group_lookup
from engine.executor.mawp_geometry_resolver import (
    apply_direct_geometry_mode,
    apply_nominal_pipe_size_for_mawp,
    apply_pipe_schedule_lookup,
)
from engine.executor.nps_input_resolver import apply_nominal_pipe_size_lookup
from engine.executor.pipe_dimension_lookup import PipeDimensionLookup
from engine.executor.unit_manager import normalize_unit
from engine.state.goal_projection import planning_projection
from engine.reference.material_resolver import canonical_material_id
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.state.state_manager import TaskStateManager
from engine.state.task_facts import deactivate_fact
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
from engine.messaging.workflow_parameter_prompts import default_workflow_parameter_prompt
from engine.reference.coefficient_resolver import list_pipe_construction_type_options
from engine.reference.parameter_composer_spec import build_composer_parameter_spec
from engine.reference.parameter_keys import (
    LEGACY_PARAMETER_KEY_ALIASES,
    MATERIAL_GRADE_KEY,
    active_fact_for_key,
    api_parameter_id,
    canonical_parameter_key,
    is_material_grade_parameter,
    read_fact_value,
)
from engine.reference.standards_paths import resolve_standard_pack
from engine.reference.standards_reader import StandardsReader

_DIAMETER_INPUT_PARAMETERS = frozenset({"nominal_pipe_size", "outside_diameter", "inside_diameter"})
_DIAMETER_INPUT_MODES: list[dict[str, str]] = [
    {"value": "nps_lookup", "label": "NPS"},
    {"value": "direct_od", "label": "Outside diameter"},
    {"value": "direct_id", "label": "Inside diameter"},
]


def _nps_dropdown_options(standards_root: Path) -> list[dict[str, str]]:
    lookup = PipeDimensionLookup(standards_root)
    return [
        {"value": nps, "label": f"NPS {nps}"}
        for nps in lookup.list_nps_sizes()
    ]


def _pipe_construction_type_dropdown_options(
    standards_root: Path,
    task: Task,
) -> list[dict[str, str]]:
    pack_root = resolve_standard_pack(standards_root, "asme_b31.3")
    existing_inputs = dict(task.fact_store.active_facts())
    material = read_fact_value(existing_inputs, MATERIAL_GRADE_KEY)
    return list_pipe_construction_type_options(
        pack_root,
        material=str(material) if material else None,
    )


def _outside_diameter_dropdown_options(standards_root: Path) -> list[dict[str, str]]:
    lookup = PipeDimensionLookup(standards_root)
    by_mm: dict[float, str] = {}
    for nps in lookup.list_nps_sizes():
        try:
            result = lookup.lookup(nps)
        except ValueError:
            continue
        od_mm = round(float(result.outside_diameter_mm), 4)
        if od_mm not in by_mm:
            by_mm[od_mm] = (
                f"{result.outside_diameter_in:g} in ({result.outside_diameter_mm:g} mm)"
            )
    return [
        {"value": str(od_mm), "label": label}
        for od_mm, label in sorted(by_mm.items())
    ]


def _diameter_ui_payload(standards_root: Path) -> dict[str, Any]:
    return {
        "input_modes": list(_DIAMETER_INPUT_MODES),
        "related_options": {
            "nominal_pipe_size": _nps_dropdown_options(standards_root),
            "outside_diameter": _outside_diameter_dropdown_options(standards_root),
        },
    }


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
    if _DIAMETER_INPUT_PARAMETERS & set(requested_ids):
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
        )
        options = list(spec.get("options") or [])
        if parameter_id == "nominal_pipe_size" and reader is not None:
            options = _nps_dropdown_options(reader.standards_root)
        if parameter_id == "outside_diameter" and reader is not None:
            options = _outside_diameter_dropdown_options(reader.standards_root)
        if parameter_id == "pipe_construction_type" and reader is not None:
            options = _pipe_construction_type_dropdown_options(reader.standards_root, task)
        if options and spec.get("type") not in {"material", "checkbox"}:
            spec["type"] = "dropdown"
        existing = active_fact_for_key(task, parameter_id)
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
        if parameter_id in _DIAMETER_INPUT_PARAMETERS and reader is not None:
            payload["diameter_ui"] = _diameter_ui_payload(reader.standards_root)
        if reader is not None:
            provenance = parameter_input_provenance(reader, task, parameter_id)
            if provenance is None:
                param_node_id = param_index.get(parameter_id)
                if param_node_id:
                    guidance = payload.get("guidance")
                    source_field = "question" if guidance else "title"
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
        return default_workflow_parameter_prompt(parameter_id)
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
    return default_workflow_parameter_prompt(parameter_id)


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
    task = manager.get_task(task_id)
    planning = planning_projection(task)
    original_parameter = parameter
    parameter = _canonical_submit_parameter(parameter)
    submittable = submittable_parameter_ids(task, planning)
    allowed_ids = _expand_allowed_parameter_ids(set(submittable))
    # #region agent log
    from api.debug_trace import agent_debug_log

    agent_debug_log(
        "parameter_definitions.py:submit_task_input",
        "submit validation snapshot",
        {
            "task_id": task_id,
            "parameter": original_parameter,
            "canonical_parameter": parameter,
            "submittable": submittable,
            "allowed_ids": sorted(allowed_ids),
            "current_phase": planning.get("current_phase"),
            "phase_missing": planning.get("phase_missing"),
            "missing_inputs": planning.get("missing_inputs"),
            "has_t": task.outputs.get("t") is not None
            or task.outputs.get("required_thickness") is not None,
            "has_tm": task.outputs.get("minimum_required_thickness") is not None
            or task.outputs.get("t_m") is not None,
            "has_execution_trace": bool(task.outputs.get("_execution_trace")),
            "goal_keys": [g.key for g in task.goal_store.goals.values()],
        },
        hypothesis_id="A,B,D,E",
    )
    # #endregion
    if "pipe_construction_type" in allowed_ids:
        allowed_ids.add("joint_category")
    if (
        parameter in _DIAMETER_INPUT_PARAMETERS
        and _DIAMETER_INPUT_PARAMETERS & allowed_ids
    ):
        allowed_ids |= _DIAMETER_INPUT_PARAMETERS
    if original_parameter not in allowed_ids and parameter not in allowed_ids:
        raise ValueError(f"Parameter is not currently requested: {original_parameter}")

    definitions = {
        item["name"]: item
        for item in build_parameter_definitions(
            task,
            reader=StandardsReader(standards_root) if standards_root is not None else None,
        )
    }
    definition = _definition_for_parameter(definitions, parameter)
    if definition is None:
        raise ValueError(f"Parameter is not currently requested: {parameter}")
    coerced = _coerce_value(definition, value)
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
    if parameter == "outside_diameter":
        from engine.state.task_facts import deactivate_fact, store_system_categorical_fact

        store_system_categorical_fact(task, key="d_input_mode", label="direct_od")
        deactivate_fact(task, "inside_diameter")
        manager.replace_task(task_id, task)
        task = manager.get_task(task_id)

    if parameter == "inside_diameter":
        from engine.state.task_facts import deactivate_fact

        deactivate_fact(task, "outside_diameter")
        deactivate_fact(task, "nominal_pipe_size")
        manager.replace_task(task_id, task)
        task = manager.get_task(task_id)

    if parameter == "nominal_pipe_size":
        if standards_root is None:
            raise ValueError("Standards root is required to resolve nominal pipe size.")
        if workflow_id == MAWP_DESIGN:
            apply_nominal_pipe_size_for_mawp(task, standards_root)
        else:
            apply_nominal_pipe_size_lookup(task, standards_root)
        from engine.state.task_facts import deactivate_fact

        deactivate_fact(task, "inside_diameter")
        manager.replace_task(task_id, task)
        task = manager.get_task(task_id)

    if parameter == "pipe_schedule" and workflow_id == MAWP_DESIGN:
        if standards_root is None:
            raise ValueError("Standards root is required to resolve pipe schedule.")
        apply_pipe_schedule_lookup(task, standards_root)
        manager.replace_task(task_id, task)
        task = manager.get_task(task_id)

    if parameter == "geometry_input_mode" and workflow_id == MAWP_DESIGN:
        apply_direct_geometry_mode(task)
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
