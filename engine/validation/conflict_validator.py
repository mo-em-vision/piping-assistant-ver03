"""Input conflict and parameter change detection."""

from __future__ import annotations

from models.task import InputConflict, Task
from models.validation import ComplianceStatus, LayerValidationResult, ValidationFinding, ValidationSeverity


class ConflictValidator:
    """Detect contradictory inputs and invalidated prior calculations."""

    def validate_task(self, task: Task) -> LayerValidationResult:
        warnings: list[ValidationFinding] = []

        for conflict in task.conflicts:
            if not isinstance(conflict, InputConflict):
                continue
            warnings.append(
                ValidationFinding(
                    rule="input_changed",
                    message=conflict.reason,
                    severity=ValidationSeverity.WARNING,
                    input_id=conflict.input_id,
                    source="task_state",
                )
            )
            if conflict.previous_calculation_invalid:
                warnings.append(
                    ValidationFinding(
                        rule="previous_calculation_invalid",
                        message=(
                            "The previous calculation may no longer be valid. "
                            "A new full execution is required."
                        ),
                        severity=ValidationSeverity.WARNING,
                        input_id=conflict.input_id,
                    )
                )

        status = ComplianceStatus.PASS_WITH_WARNING if warnings else ComplianceStatus.PASS
        return LayerValidationResult(
            status=status,
            warnings=warnings,
            affected_nodes=[],
            metadata={"conflict_count": len(task.conflicts)},
        )
