"""Tests for runtime Fact model validation per Fact Node template."""

from __future__ import annotations

from engine.validation.fact_validator import validate_fact, validate_fact_dict
from models.fact import (
    FactClass,
    FactProvenance,
    FactSource,
    FactValidation,
    NumericValue,
    SourceType,
    ValidationStatus,
    build_numeric_fact,
    new_fact_id,
)


def _sample_numeric_fact(**overrides) -> object:
    fact = build_numeric_fact(
        key="design_pressure",
        parameter="PARAM-internal-design-gage-pressure",
        amount=8,
        unit="UNIT-bar",
        fact_class=FactClass.USER_SUPPLIED,
        source=FactSource(
            source_type=SourceType.USER_INPUT,
            source_id="USER",
            description="Provided by user.",
        ),
        provenance=FactProvenance(
            task_id="TASK-test",
            workflow_id="WF-pipe-wall-thickness-design",
            created_by="user",
            timestamp="2026-07-02T10:30:00Z",
        ),
        canonical_amount=800_000,
        canonical_unit="UNIT-Pa",
        validation_status=ValidationStatus.CONFIRMED,
        dimension="DIM-pressure",
    )
    for key, value in overrides.items():
        setattr(fact, key, value)
    return fact


def test_valid_user_supplied_numeric_fact_passes() -> None:
    fact = _sample_numeric_fact()
    assert validate_fact(fact) == []


def test_fact_requires_param_reference() -> None:
    fact = _sample_numeric_fact(parameter="design_pressure")
    issues = validate_fact(fact)
    assert any("PARAM-*" in issue for issue in issues)


def test_fact_type_must_be_fact() -> None:
    fact = _sample_numeric_fact(type="parameter")
    assert "type must be 'fact'" in validate_fact(fact)


def test_confirmed_numeric_fact_requires_canonical_value() -> None:
    fact = _sample_numeric_fact(canonical_value=None)
    issues = validate_fact(fact)
    assert any("canonical_value" in issue for issue in issues)


def test_validate_fact_dict_round_trip() -> None:
    fact = _sample_numeric_fact()
    payload = {
        "id": fact.id,
        "type": "fact",
        "parameter": fact.parameter,
        "key": fact.key,
        "fact_class": fact.fact_class.value,
        "value": {"amount": 8, "unit": "UNIT-bar"},
        "canonical_value": {"amount": 800_000, "unit": "UNIT-Pa"},
        "source": {
            "source_type": SourceType.USER_INPUT.value,
            "source_id": "USER",
            "description": "Provided by user.",
        },
        "provenance": {
            "task_id": "TASK-test",
            "workflow_id": "WF-pipe-wall-thickness-design",
            "created_by": "user",
            "timestamp": "2026-07-02T10:30:00Z",
        },
        "validation": {
            "status": ValidationStatus.CONFIRMED.value,
            "unit_validated": True,
            "dimension": "DIM-pressure",
            "warnings": [],
            "errors": [],
        },
        "supersession": {
            "supersedes": None,
            "superseded_by": None,
            "active": True,
        },
        "metadata": {"version": 1},
    }
    assert validate_fact_dict(payload) == []


def test_forbidden_metadata_fields_rejected() -> None:
    fact = _sample_numeric_fact(metadata={"equation_formula": "t = PD / 2SE"})
    issues = validate_fact(fact)
    assert any("forbidden metadata field" in issue for issue in issues)


def test_pending_fact_may_have_no_value() -> None:
    fact = _sample_numeric_fact(
        value=None,
        validation=FactValidation(status=ValidationStatus.PENDING),
        fact_class=FactClass.SYSTEM_GENERATED,
    )
    assert validate_fact(fact) == []
