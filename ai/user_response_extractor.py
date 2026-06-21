"""Generic extraction of user responses against pending node interactions."""

from __future__ import annotations

import re
from typing import Mapping, Sequence

from engine.graph.node_interaction import (
    NodeInteractionSpec,
    extract_decision_responses,
    interaction_input_from_response,
    match_decision_in_message,
    resolve_interaction_value,
)
from models.input import EngineeringInput, InputSource, InputStatus

_CONFIRM_PATTERN = re.compile(
    r"^(?:confirm|yes|use\s+default|ok|accept)(?:\s+the\s+default)?\.?$",
    re.IGNORECASE,
)


def extract_interaction_responses(
    message: str,
    pending: Sequence[NodeInteractionSpec],
) -> dict[str, EngineeringInput]:
    """Parse user text for pending decision interactions and return canonical values."""
    extracted: dict[str, EngineeringInput] = {}
    if not message.strip() or not pending:
        return extracted

    for variable, raw_match in extract_decision_responses(message, pending).items():
        if variable in extracted:
            continue
        spec = _spec_for(pending, variable)
        if spec is None:
            continue
        canonical = resolve_interaction_value(spec, raw_match)
        if canonical is None:
            continue
        extracted[variable] = interaction_input_from_response(
            spec,
            canonical,
            original_value=message.strip(),
        )
    return extracted


def extract_confirmation_intent(message: str) -> bool:
    """Return True when the user affirms a proposed default."""
    return bool(_CONFIRM_PATTERN.match(message.strip()))


def extract_value_override(
    message: str,
    spec: NodeInteractionSpec,
) -> EngineeringInput | None:
    """Parse a labeled numeric override for a pending value requirement."""
    labels = [spec.variable, spec.variable.replace("_", " ")]
    if spec.symbol:
        labels.append(spec.symbol)
    for label in labels:
        if not label:
            continue
        pattern = re.compile(
            rf"\b{re.escape(label)}\b\s*[:=]?\s*(\d+(?:\.\d+)?)(?:\s*(\S+))?",
            re.IGNORECASE,
        )
        match = pattern.search(message)
        if not match:
            continue
        value: float | int = float(match.group(1))
        if value == int(value):
            value = int(value) if isinstance(value, float) else value
        unit = (match.group(2) or spec.unit).rstrip(".,;")
        return interaction_input_from_response(
            spec,
            value,
            original_value=message.strip(),
            status=InputStatus.USER_OVERRIDE,
            source=InputSource.USER,
        )
    return None


def confirm_proposed_input(
    spec: NodeInteractionSpec,
    existing: EngineeringInput,
) -> EngineeringInput:
    """Upgrade a proposed default to a confirmed user value."""
    return EngineeringInput(
        input_id=existing.input_id,
        value=existing.value,
        unit=existing.unit,
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
        default=existing.default,
        requires_confirmation=spec.confirmation_required,
        original_value=existing.original_value or existing.value,
    )


def resolve_pending_value_responses(
    message: str,
    pending: Sequence[NodeInteractionSpec],
    existing_inputs: Mapping[str, EngineeringInput],
) -> dict[str, EngineeringInput]:
    """Resolve confirm or override replies for pending value confirmations."""
    resolved: dict[str, EngineeringInput] = {}
    if not message.strip() or not pending:
        return resolved

    for spec in pending:
        override = extract_value_override(message, spec)
        if override is not None:
            resolved[spec.variable] = override

    if resolved:
        return resolved

    if not extract_confirmation_intent(message):
        return resolved

    for spec in pending:
        stored = existing_inputs.get(spec.variable)
        if not isinstance(stored, EngineeringInput):
            continue
        if stored.status != InputStatus.PROPOSED_DEFAULT:
            continue
        resolved[spec.variable] = confirm_proposed_input(spec, stored)
        break

    return resolved


def extract_explicit_interaction_value(
    message: str,
    spec: NodeInteractionSpec,
) -> str | None:
    """Resolve a single interaction when the executor already knows which variable is pending."""
    text = message.strip()
    if not text:
        return None
    if spec.mode.value == "decision":
        matched = match_decision_in_message(text, spec)
        if matched is not None:
            return matched
    return resolve_interaction_value(spec, text)


def _spec_for(
    pending: Sequence[NodeInteractionSpec],
    variable: str,
) -> NodeInteractionSpec | None:
    for spec in pending:
        if spec.variable == variable:
            return spec
    return None
