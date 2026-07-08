"""Default user-facing prompts for workflow parameter inputs.

Prompt resolution order for live tasks is implemented in
``parameter_input_prompt.build_parameter_input_prompt`` (interaction specs,
PARAM metadata, equation guidance, legacy phase_questions, then catalog defaults).
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
        "Enter the internal design gage pressure P, including units. "
        "This value is used in the pressure design thickness equation. "
        "Examples: 500 psi, 8 bar, 3.5 MPa."
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
        "Enter the corrosion allowance c, including units. "
        "This will be added to the calculated pressure design thickness to determine the minimum required thickness. "
        "Example: 1.5 mm or 0.0625 in."
    ),
    "material_grade": (
        "Enter the material specification and grade. "
        "This is used with design temperature to resolve allowable stress from the applicable material table. "
        "Example: ASTM A106 Grade B."
    ),
    "material": (
        "Enter the material specification and grade. "
        "This is used with design temperature to resolve allowable stress from the applicable material table. "
        "Example: ASTM A106 Grade B."
    ),
    "design_temperature": (
        "Enter the design temperature, including units. "
        "This is used with the selected material to resolve allowable stress from the applicable material table. "
        "Examples: 400 F, 200 C."
    ),
    "external_design_pressure": (
        "Please provide the external design pressure for external pressure "
        "wall thickness design per ASME B31.3 §304.1.3."
    ),
    "pipe_construction_type": (
        "Select the pipe construction or longitudinal joint type. "
        "This is used as a lookup key to resolve quality factor E from Tables A-2 and A-3 — "
        "do not enter E directly."
    ),
    "joint_category": (
        "Select the pipe construction or longitudinal joint type. "
        "This is used as a lookup key to resolve quality factor E from Tables A-2 and A-3 — "
        "do not enter E directly."
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

# Composer-only short asks (center panel). Long context belongs in guidance YAML scroll.
SHORT_WORKFLOW_PARAMETER_PROMPTS: dict[str, str] = {
    "straight_pipe_section": (
        "Is the pipe wall thickness you would like to calculate for a straight section of pipe?"
    ),
    "pressure_loading": "Is the pipe subjected to internal or external pressure?",
    "internal_design_gage_pressure": "Enter internal design gage pressure P.",
    "outside_diameter": "Enter outside diameter D.",
    "nominal_pipe_size": "Enter nominal pipe size (NPS).",
    "inside_diameter": "Enter inside diameter d.",
    "d_input_mode": "Provide outside diameter by NPS lookup or direct entry?",
    "corrosion_allowance": "Enter corrosion allowance c.",
    "material_grade": "Enter material specification and grade.",
    "material": "Enter material specification and grade.",
    "design_temperature": "Enter design temperature.",
    "external_design_pressure": "Enter external design pressure.",
    "pipe_construction_type": "Select pipe construction or longitudinal joint type.",
    "joint_category": "Select pipe construction or longitudinal joint type.",
    "geometry_input_mode": "Provide geometry by NPS and schedule or direct dimensions?",
    "pipe_schedule": "Enter pipe schedule.",
    "actual_wall_thickness": "Enter actual or ordered wall thickness.",
}


def short_workflow_parameter_prompt(parameter_id: str) -> str | None:
    """Return a short composer prompt for a workflow parameter, if catalogued."""
    from engine.reference.parameter_keys import canonical_parameter_key

    prompt = SHORT_WORKFLOW_PARAMETER_PROMPTS.get(canonical_parameter_key(parameter_id))
    if prompt is None:
        return None
    text = prompt.strip()
    return text or None


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
