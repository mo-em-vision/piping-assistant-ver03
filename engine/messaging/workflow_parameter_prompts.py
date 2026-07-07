"""Default user-facing prompts for workflow parameter inputs.

Prompt resolution order for live tasks is implemented in
``parameter_input_prompt.build_parameter_input_prompt`` (interaction specs,
graph questions, equation guidance, then these defaults). The planner and
goal layers must not own prompt copy.
"""

from __future__ import annotations

DEFAULT_WORKFLOW_PARAMETER_PROMPTS: dict[str, str] = {
    "straight_pipe_section": (
        "Is the pipe wall thickness you would like to calculate for a straight section of pipe? "
        "Non-straight sections (fittings, bends) are not yet supported."
    ),
    "pressure_loading": (
        "Is the pipe subjected to internal or external pressure? "
        "Internal pressure design uses §304.1.2; external pressure design uses §304.1.3."
    ),
    "internal_design_gage_pressure": (
        "To continue the calculation, I need the internal design gage pressure because "
        "wall thickness is governed by internal pressure per ASME B31.3 §304.1.2."
    ),
    "outside_diameter": (
        "Please provide the outside diameter of the pipe (mm or in) so the required "
        "wall thickness can be calculated."
    ),
    "nominal_pipe_size": (
        "Please provide the nominal pipe size (NPS) so outside diameter D can be "
        "looked up per ASME B36.10."
    ),
    "inside_diameter": (
        "Please provide the inside diameter d of the pipe (mm or in) so the required "
        "wall thickness can be calculated using eq. (3b)."
    ),
    "d_input_mode": (
        "Provide outside diameter D by nominal pipe size (NPS, looked up per ASME B36.10) "
        "or enter the outside diameter directly (mm or in)?"
    ),
    "corrosion_allowance": (
        "For c (mechanical allowances): the default is 0.5 mm when machined surfaces "
        "or grooves where tolerance is not specified. Confirm or enter another value."
    ),
    "material_grade": (
        "Select the pipe material. (start typing to see the available options)"
    ),
    "design_temperature": (
        "Please provide the design temperature because allowable stress "
        "depends on metal temperature."
    ),
    "external_design_pressure": (
        "Please provide the external design pressure for external pressure "
        "wall thickness design per ASME B31.3 §304.1.3."
    ),
    "pipe_construction_type": (
        "Select the pipe construction or longitudinal joint type to resolve quality "
        "factor E from Tables A-2 and A-3."
    ),
    "joint_category": (
        "Select the pipe construction or longitudinal joint type to resolve quality "
        "factor E from Tables A-2 and A-3."
    ),
    "geometry_input_mode": (
        "Provide geometry by nominal pipe size and schedule (looked up per ASME B36.10) "
        "or enter the outside diameter and actual wall thickness directly?"
    ),
    "pipe_schedule": (
        "Enter the pipe schedule so outside diameter and wall thickness can be "
        "looked up per ASME B36.10."
    ),
    "actual_wall_thickness": (
        "Enter the actual or ordered wall thickness of the pipe."
    ),
}


def default_workflow_parameter_prompt(parameter_id: str) -> str | None:
    """Return the catalog default prompt for a workflow parameter, if any."""
    from engine.reference.parameter_keys import canonical_parameter_key

    prompt = DEFAULT_WORKFLOW_PARAMETER_PROMPTS.get(canonical_parameter_key(parameter_id))
    if prompt is None:
        return None
    text = prompt.strip()
    return text or None


def resolve_workflow_parameter_prompt(
    parameter_id: str,
    *,
    field_question: str | None = None,
    fallback_prefix: str = "Provide",
) -> str:
    """Resolve a prompt from graph field text, defaults, or a generic fallback."""
    if field_question and field_question.strip():
        return field_question.strip()
    default = default_workflow_parameter_prompt(parameter_id)
    if default:
        return default
    return f"{fallback_prefix} {parameter_id.replace('_', ' ')}"
