"""Rule engine tests."""

from __future__ import annotations

from engine.rules.rule_engine import RuleEngine


def test_evaluate_thin_wall_condition() -> None:
    engine = RuleEngine()
    result = engine.evaluate_condition(
        condition_id="thin_wall_check",
        expression="t < D/6",
        variables={"t": 1.0, "D": 10.0},
    )

    assert result.passed is True


def test_validate_positive_rejects_zero() -> None:
    engine = RuleEngine()
    assert engine.validate_positive("P", 0) is not None
    assert engine.validate_positive("P", 100) is None
