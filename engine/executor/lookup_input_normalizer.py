"""Normalize lookup engine inputs to canonical binding keys."""

from __future__ import annotations

from typing import Any

from engine.reference.parameter_keys import (
    LEGACY_PARAMETER_KEY_ALIASES,
    MATERIAL_GRADE_KEY,
    canonical_parameter_key,
)
from models.fact import Fact, fact_scalar_value


def _scalar_value(raw: Any) -> Any:
    if isinstance(raw, Fact):
        return fact_scalar_value(raw)
    if hasattr(raw, "value"):
        return raw.value
    return raw


def _values_conflict(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return False
    return str(left).strip() != str(right).strip()


def normalize_lookup_inputs(
    inputs: dict[str, Any],
    *,
    bindings: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return lookup inputs keyed by canonical binding names only.

    Legacy aliases (e.g. ``material`` → ``material_grade``) are applied only when
    the canonical key is absent. Conflicting legacy and canonical values raise.
    """
    normalized: dict[str, Any] = dict(inputs)
    canonical_keys = set(bindings or ()) or {
        canonical_parameter_key(key) for key in inputs
    }

    for canonical_key in sorted(canonical_keys):
        legacy_keys = [
            legacy
            for legacy, target in LEGACY_PARAMETER_KEY_ALIASES.items()
            if target == canonical_key
        ]
        if not legacy_keys:
            continue

        canonical_present = canonical_key in normalized
        canonical_value = _scalar_value(normalized[canonical_key]) if canonical_present else None

        for legacy_key in legacy_keys:
            if legacy_key not in normalized:
                continue
            legacy_value = _scalar_value(normalized[legacy_key])
            if canonical_present:
                if _values_conflict(canonical_value, legacy_value):
                    raise ValueError(
                        f"Conflicting lookup inputs for {canonical_key!r}: "
                        f"{canonical_key}={canonical_value!r}, {legacy_key}={legacy_value!r}"
                    )
            else:
                normalized[canonical_key] = normalized[legacy_key]
            del normalized[legacy_key]

    # Explicit material_grade guard even when bindings omit it.
    if MATERIAL_GRADE_KEY in canonical_keys or "material" in inputs:
        material_present = MATERIAL_GRADE_KEY in normalized
        material_value = _scalar_value(normalized.get(MATERIAL_GRADE_KEY))
        if "material" in normalized:
            legacy_material = _scalar_value(normalized["material"])
            if material_present and _values_conflict(material_value, legacy_material):
                raise ValueError(
                    f"Conflicting lookup inputs for {MATERIAL_GRADE_KEY!r}: "
                    f"{MATERIAL_GRADE_KEY}={material_value!r}, material={legacy_material!r}"
                )
            if not material_present:
                normalized[MATERIAL_GRADE_KEY] = normalized["material"]
            del normalized["material"]

    return normalized
