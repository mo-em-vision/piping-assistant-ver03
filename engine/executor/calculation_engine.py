"""Formula step execution from standards node formula files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.executor.expression_evaluator import evaluate_expression
from engine.reference.standards_markdown import split_frontmatter
from models.calculation import CalculationResult, CalculationStatus, CalculationStep, QuantityResult


def load_formula_text(text: str) -> dict[str, Any]:
    if not text.strip():
        return {}
    metadata, _ = split_frontmatter(text)
    return metadata if isinstance(metadata, dict) else {}


def load_formula_file(path: Path) -> dict[str, Any]:
    return load_formula_text(path.read_text(encoding="utf-8"))


class CalculationEngine:
    """Execute approved formula step definitions."""

    def execute_formula_steps(
        self,
        *,
        calculation_id: str,
        formula_data: dict[str, Any],
        variables: dict[str, float],
    ) -> CalculationResult:
        steps: list[CalculationStep] = []
        env = dict(variables)
        intermediates: dict[str, float] = {}

        for step_def in formula_data.get("steps", []) or []:
            step_name = str(step_def.get("name", "step"))
            step_inputs = dict(env)

            for expr_def in step_def.get("expressions", []) or []:
                expression = str(expr_def.get("expression", ""))
                assign = str(expr_def.get("assign", ""))
                if not expression or not assign:
                    continue
                value = evaluate_expression(expression, env)
                env[assign] = value
                intermediates[assign] = value

            steps.append(
                CalculationStep(
                    name=step_name,
                    inputs=step_inputs,
                    result={k: env[k] for k in env if k not in step_inputs or env[k] != step_inputs[k]},
                )
            )

        output_def = None
        outputs = formula_data.get("outputs", []) or []
        if outputs:
            output_def = outputs[0]

        symbol = str(output_def.get("symbol", "t")) if output_def else "t"
        unit = str(output_def.get("unit", "mm")) if output_def else "mm"
        final_value = env.get(symbol)
        if final_value is None:
            raise ValueError(f"Formula did not produce output symbol: {symbol}")

        return CalculationResult(
            calculation_id=calculation_id,
            inputs=variables,
            formula={"display": formula_data.get("display"), "steps": formula_data.get("steps")},
            steps=steps,
            final_result=QuantityResult(symbol=symbol, value=float(final_value), unit=unit),
            status=CalculationStatus.PASS,
        )

    def execute_from_file(
        self,
        *,
        calculation_id: str,
        formula_path: Path,
        variables: dict[str, float],
    ) -> CalculationResult:
        formula_data = load_formula_file(formula_path)
        return self.execute_from_text(
            calculation_id=calculation_id,
            formula_text=formula_path.read_text(encoding="utf-8"),
            variables=variables,
        )

    def execute_from_text(
        self,
        *,
        calculation_id: str,
        formula_text: str,
        variables: dict[str, float],
    ) -> CalculationResult:
        formula_data = load_formula_text(formula_text)
        return self.execute_formula_steps(
            calculation_id=calculation_id,
            formula_data=formula_data,
            variables=variables,
        )
