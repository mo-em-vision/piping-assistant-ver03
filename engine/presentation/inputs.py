"""Reconstruct engineering inputs from workflow parameters only."""

from __future__ import annotations

from models.input import EngineeringInput, InputSource, InputStatus, ResolutionMethod
from models.workflow_state import WorkflowParameter

_SOURCE_TO_INPUT: dict[str, InputSource] = {
    "user_input": InputSource.USER,
    "lookup": InputSource.TABLE,
    "default": InputSource.DEFAULT,
    "equation": InputSource.NODE,
    "derived": InputSource.SYSTEM,
}

_RESOLUTION_BY_SOURCE: dict[str, ResolutionMethod] = {
    "user_input": ResolutionMethod.USER_INPUT,
    "lookup": ResolutionMethod.TABLE_LOOKUP,
    "default": ResolutionMethod.DEFAULT_CONFIRMED,
    "equation": ResolutionMethod.EQUATION,
    "derived": ResolutionMethod.NODE_OUTPUT,
}


def _parse_status(status: str) -> InputStatus:
    try:
        return InputStatus(status)
    except ValueError:
        if status == "confirmed":
            return InputStatus.CONFIRMED
        return InputStatus.PENDING


def engineering_inputs_from_parameters(
    parameters: dict[str, WorkflowParameter],
) -> dict[str, EngineeringInput]:
    """Build ``EngineeringInput`` map for graph display emitters."""
    inputs: dict[str, EngineeringInput] = {}
    for name, param in parameters.items():
        source = _SOURCE_TO_INPUT.get(param.source, InputSource.SYSTEM)
        status = _parse_status(param.status)
        requires_confirmation = status == InputStatus.PROPOSED_DEFAULT
        inputs[name] = EngineeringInput(
            input_id=name,
            value=param.value,
            unit=param.unit,
            source=source,
            status=status,
            symbol=param.symbol,
            requires_confirmation=requires_confirmation,
            resolution_method=_RESOLUTION_BY_SOURCE.get(param.source),
        )
    return inputs
