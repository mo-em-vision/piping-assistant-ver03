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
from models.fact import (
    Fact,
    FactClass,
    ValidationStatus,
    fact_from_user_submission,
    fact_scalar_value,
    fact_unit,
)

_CONFIRM_PATTERN = re.compile(
    r"^(?:confirm|yes|use\s+default|ok|accept)(?:\s+the\s+default)?\.?$",
    re.IGNORECASE,
)


def extract_interaction_responses(
    message: str,
    pending: Sequence[NodeInteractionSpec],
    *,
    existing_inputs: Mapping[str, Fact] | None = None,
) -> dict[str, Fact]:
    """Parse user text for pending decision interactions and return canonical values."""
    extracted: dict[str, Fact] = {}
    if not message.strip() or not pending:
        return extracted

    if extract_confirmation_intent(message) and existing_inputs:
        for spec in pending:
            stored = existing_inputs.get(spec.variable)
            if not isinstance(stored, Fact):
                continue
            if (
                stored.fact_class != FactClass.DEFAULT_CONFIRMED
                or stored.validation.status != ValidationStatus.PENDING
            ):
                continue
            extracted[spec.variable] = confirm_proposed_input(spec, stored)
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
        task_id = ""
        if existing_inputs and existing_inputs.get(spec.variable) is not None:
            task_id = existing_inputs[spec.variable].provenance.task_id or ""
        extracted[variable] = interaction_input_from_response(
            spec,
            canonical,
            task_id=task_id,
            original_value=message.strip(),
        )
    return extracted


def extract_confirmation_intent(message: str) -> bool:
    """Return True when the user affirms a proposed default."""
    return bool(_CONFIRM_PATTERN.match(message.strip()))


def extract_value_override(
    message: str,
    spec: NodeInteractionSpec,
    *,
    task_id: str = "",
) -> Fact | None:
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
            task_id=task_id,
            original_value=message.strip(),
            validation_status=ValidationStatus.CONFIRMED,
        )
    return None


def confirm_proposed_input(
    spec: NodeInteractionSpec,
    existing: Fact,
) -> Fact:
    """Upgrade a proposed default to a confirmed user value."""
    return fact_from_user_submission(
        key=existing.key,
        value=fact_scalar_value(existing),
        unit=fact_unit(existing),
        task_id=existing.provenance.task_id or "",
        validation_status=ValidationStatus.CONFIRMED,
    )


def resolve_pending_value_responses(
    message: str,
    pending: Sequence[NodeInteractionSpec],
    existing_inputs: Mapping[str, Fact],
) -> dict[str, Fact]:
    """Resolve confirm or override replies for pending value confirmations."""
    resolved: dict[str, Fact] = {}
    if not message.strip() or not pending:
        return resolved

    task_id = ""
    for fact in existing_inputs.values():
        if fact.provenance.task_id:
            task_id = fact.provenance.task_id
            break

    for spec in pending:
        override = extract_value_override(message, spec, task_id=task_id)
        if override is not None:
            resolved[spec.variable] = override

    if resolved:
        return resolved

    if not extract_confirmation_intent(message):
        return resolved

    for spec in pending:
        stored = existing_inputs.get(spec.variable)
        if not isinstance(stored, Fact):
            continue
        if (
            stored.fact_class != FactClass.DEFAULT_CONFIRMED
            or stored.validation.status != ValidationStatus.PENDING
        ):
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
