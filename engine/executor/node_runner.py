"""Single-node execution lifecycle."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from engine.executor.functions import get_execution_function
from engine.executor.lookup_engine import LookupEngine
from engine.executor.unit_manager import prepare_engineering_input, prepare_symbol_map
from engine.reference.standards_reader import NodeRecord, StandardsReader
from engine.rules.rule_engine import RuleEngine
from models.execution import NodeExecutionResult, NodeExecutionStatus
from models.input import EngineeringInput, InputSource


class NodeRunner:
    """Execute one standards node deterministically."""

    def __init__(
        self,
        reader: StandardsReader,
        *,
        lookup_engine: LookupEngine | None = None,
        rule_engine: RuleEngine | None = None,
    ) -> None:
        self._reader = reader
        self._lookup_engine = lookup_engine or LookupEngine(reader.pack_root)
        self._rule_engine = rule_engine or RuleEngine()

    def run(
        self,
        node_id: str,
        *,
        task_inputs: dict[str, EngineeringInput],
        dependency_outputs: dict[str, Any],
    ) -> NodeExecutionResult:
        record = self._reader.load(node_id)
        node_type = str(record.metadata.get("type", ""))

        if node_type == "lookup":
            return self._run_lookup(record, task_inputs=task_inputs)
        if node_type == "calculation":
            return self._run_calculation(
                record,
                task_inputs=task_inputs,
                dependency_outputs=dependency_outputs,
            )
        if node_type == "root":
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.SKIPPED,
                trace={"reason": "root node — no execution"},
            )

        return NodeExecutionResult(
            node_id=record.node_id,
            status=NodeExecutionStatus.ERROR,
            errors=[f"Unsupported node type: {node_type}"],
        )

    def _run_lookup(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, EngineeringInput],
    ) -> NodeExecutionResult:
        missing = self._missing_inputs(record, task_inputs)
        if missing:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.AWAITING_INPUT,
                errors=[f"Missing required inputs: {', '.join(missing)}"],
                trace={"missing_inputs": missing},
            )

        raw_inputs: dict[str, Any] = {}
        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            input_id = str(spec.get("id", ""))
            if input_id in task_inputs:
                target_unit = None
                if input_id == "design_temperature":
                    target_unit = "f"
                prepared = prepare_engineering_input(
                    task_inputs[input_id],
                    target_unit=target_unit,
                )
                raw_inputs[input_id] = prepared.value
                raw_inputs[f"{input_id}_unit"] = prepared.unit

        lookups = record.metadata.get("lookups", []) or []
        if not lookups:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=["No lookup configuration found"],
            )

        lookup_config = lookups[0] if isinstance(lookups[0], dict) else {}
        try:
            lookup_result = self._lookup_engine.execute_lookup(
                node_id=record.node_id,
                lookup_config=lookup_config,
                inputs=raw_inputs,
            )
        except (ValueError, FileNotFoundError) as exc:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[str(exc)],
                inputs=raw_inputs,
            )

        output_id = "allowable_stress"
        for spec in record.metadata.get("outputs", []) or []:
            if isinstance(spec, dict) and spec.get("id"):
                output_id = str(spec["id"])
                break

        outputs = {
            output_id: lookup_result.calculation.final_result.value
            if lookup_result.calculation.final_result
            else None,
            "S": lookup_result.calculation.final_result.value
            if lookup_result.calculation.final_result
            else None,
        }

        return self._finalize_result(
            record,
            status=NodeExecutionStatus.COMPLETED,
            inputs=raw_inputs,
            outputs=outputs,
            trace={
                "lookup": asdict(lookup_result.trace),
                "calculation": asdict(lookup_result.calculation),
            },
        )

    def _run_calculation(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, EngineeringInput],
        dependency_outputs: dict[str, Any],
    ) -> NodeExecutionResult:
        resolved, missing = self._resolve_calculation_inputs(
            record,
            task_inputs=task_inputs,
            dependency_outputs=dependency_outputs,
        )
        if missing:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.AWAITING_INPUT,
                errors=[f"Missing required inputs: {', '.join(missing)}"],
                trace={"missing_inputs": missing},
            )

        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            symbol = str(spec.get("name", spec.get("id", "")))
            validation = str(spec.get("validation", ""))
            if validation == "positive" and symbol in resolved:
                error = self._rule_engine.validate_positive(symbol, resolved[symbol])
                if error:
                    return NodeExecutionResult(
                        node_id=record.node_id,
                        status=NodeExecutionStatus.ERROR,
                        errors=[error],
                        inputs=resolved,
                    )

        unit_map = self._symbol_unit_map(record)
        variables = prepare_symbol_map(resolved, unit_map)

        formulas = record.metadata.get("formulas", []) or []
        if not formulas:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=["No formula configuration found"],
            )

        formula_meta = formulas[0] if isinstance(formulas[0], dict) else {}
        function_name = str(formula_meta.get("execution_function", ""))
        fn = get_execution_function(function_name)
        if fn is None:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[f"Unapproved execution function: {function_name}"],
            )

        try:
            calculation = fn(node_dir=record.path.parent, variables=variables)
        except Exception as exc:  # noqa: BLE001 — surface execution errors to task state
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[str(exc)],
                inputs=resolved,
            )

        symbol_map = {"P": "P", "D": "D", "S": "S", "E": "E", "W": "W", "Y": "Y", "t": "t"}
        eval_vars = {symbol_map.get(k, k): v for k, v in variables.items()}
        if calculation.final_result:
            eval_vars["t"] = calculation.final_result.value
            eval_vars["D"] = variables.get("D", eval_vars.get("D", 0.0))

        warnings: list[str] = []
        for condition in record.metadata.get("conditions", []) or []:
            if not isinstance(condition, dict):
                continue
            cond_id = str(condition.get("id", "condition"))
            expression = str(condition.get("expression", ""))
            if not expression:
                continue
            cond_result = self._rule_engine.evaluate_condition(
                condition_id=cond_id,
                expression=expression,
                variables=eval_vars,
            )
            if not cond_result.passed and cond_result.message:
                warnings.append(cond_result.message)

        output_id = "required_thickness"
        for spec in record.metadata.get("outputs", []) or []:
            if isinstance(spec, dict) and spec.get("id"):
                output_id = str(spec["id"])
                break

        final = calculation.final_result
        outputs = {
            output_id: final.value if final else None,
            "t": final.value if final else None,
        }

        intermediates: dict[str, float] = {}
        for step in calculation.steps:
            if isinstance(step.result, dict):
                for key, value in step.result.items():
                    if isinstance(value, (int, float)):
                        intermediates[key] = float(value)

        return self._finalize_result(
            record,
            status=NodeExecutionStatus.COMPLETED,
            inputs=resolved,
            outputs=outputs,
            warnings=warnings,
            trace={
                "calculation": asdict(calculation),
                "intermediates": intermediates,
                "variables_si": variables,
            },
        )

    def _resolve_calculation_inputs(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, EngineeringInput],
        dependency_outputs: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        resolved: dict[str, Any] = {}
        missing: list[str] = []

        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            input_id = str(spec.get("id", ""))
            symbol = str(spec.get("name", input_id))
            required = bool(spec.get("required", True))
            source = str(spec.get("source", "user_input"))

            value: Any = None
            if source == "node_output":
                value = dependency_outputs.get(input_id)
                if value is None:
                    value = dependency_outputs.get(symbol)
                if value is None:
                    value = dependency_outputs.get("S")
            elif input_id in task_inputs:
                prepared = prepare_engineering_input(task_inputs[input_id])
                resolved[symbol] = prepared.value
                resolved[f"{symbol}_unit"] = prepared.unit
                continue
            elif source == "default" and spec.get("default") is not None:
                value = spec.get("default")
            elif input_id in dependency_outputs:
                value = dependency_outputs[input_id]

            if value is None:
                if required:
                    missing.append(input_id)
                continue

            resolved[symbol] = value

        return resolved, missing

    @staticmethod
    def _missing_inputs(
        record: NodeRecord,
        task_inputs: dict[str, EngineeringInput],
    ) -> list[str]:
        missing: list[str] = []
        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            input_id = str(spec.get("id", ""))
            if bool(spec.get("required", True)) and input_id not in task_inputs:
                missing.append(input_id)
        return missing

    @staticmethod
    def _symbol_unit_map(record: NodeRecord) -> dict[str, str]:
        unit_map: dict[str, str] = {}
        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            symbol = str(spec.get("name", spec.get("id", "")))
            unit_map[symbol] = str(spec.get("unit", "dimensionless"))
        return unit_map

    @staticmethod
    def _finalize_result(
        record: NodeRecord,
        *,
        status: NodeExecutionStatus,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
        trace: dict[str, Any] | None = None,
    ) -> NodeExecutionResult:
        payload = json.dumps({"inputs": inputs, "outputs": outputs}, sort_keys=True, default=str)
        input_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]
        result_hash = hashlib.sha256(json.dumps(outputs, sort_keys=True, default=str).encode()).hexdigest()[:16]

        return NodeExecutionResult(
            node_id=record.node_id,
            status=status,
            inputs=inputs,
            outputs=outputs,
            warnings=warnings or [],
            errors=errors or [],
            trace=trace or {},
            execution_id=str(uuid.uuid4()),
            node_version=str(record.metadata.get("version", "1.0")),
            input_hash=input_hash,
            result_hash=result_hash,
        )
