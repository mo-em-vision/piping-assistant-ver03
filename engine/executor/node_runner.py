"""Single-node execution lifecycle."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from engine.executor.pipe_dimension_lookup import PipeDimensionLookup
from engine.graph.assumption_checker import field_value, evaluate_node_execution_assumptions
from engine.graph.node_interaction import evaluate_node_interactions
from engine.executor.functions import get_execution_function
from engine.executor.lookup_engine import LookupEngine
from engine.executor.unit_manager import prepare_engineering_input, prepare_symbol_map
from engine.reference.nomenclature_resolver import input_applies, load_nomenclature_for_node, resolve_input_spec
from engine.reference.standards_reader import NodeRecord, StandardsReader
from engine.rules.rule_engine import RuleEngine
from models.execution import NodeExecutionResult, NodeExecutionStatus
from models.input import EngineeringInput, InputSource, InputStatus, input_is_expansion_ready


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

        interaction_eval = evaluate_node_interactions(
            record,
            task_inputs,
            phase="execution",
            reader=self._reader,
        )
        if interaction_eval.missing_fields:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.AWAITING_INPUT,
                errors=[
                    f"Missing required interactions: {', '.join(interaction_eval.missing_fields)}"
                ],
                trace={
                    "missing_interactions": interaction_eval.missing_fields,
                    "interaction_questions": interaction_eval.field_questions,
                },
            )

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
        if node_type == "definition":
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.SKIPPED,
                trace={"reason": "definition node — reference only"},
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
        execution_eval = evaluate_node_execution_assumptions(
            record,
            existing_inputs=task_inputs,
        )
        if execution_eval.missing_fields:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.AWAITING_INPUT,
                errors=[
                    f"Missing execution assumptions: {', '.join(execution_eval.missing_fields)}"
                ],
                trace={"missing_assumptions": execution_eval.missing_fields},
            )

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

        equations = record.metadata.get("equations", []) or record.metadata.get("formulas", []) or []
        if not equations:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=["No equation configuration found"],
            )

        equation_meta = equations[0] if isinstance(equations[0], dict) else {}
        function_name = str(equation_meta.get("execution_function", ""))
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
        warnings: list[str] = []
        thin_wall_valid = True
        if calculation.final_result:
            eval_vars["t"] = calculation.final_result.value
            eval_vars["D"] = variables.get("D", eval_vars.get("D", 0.0))

            thickness = float(calculation.final_result.value)
            outside_d = float(variables.get("D", 0.0))
            if outside_d > 0 and thickness >= outside_d / 6.0:
                thin_wall_valid = False
                from engine.reference.coefficient_resolver import (
                    compute_thick_wall_y,
                    inside_diameter_from_od_and_thickness,
                )

                c_allowance = float(resolved.get("c", 0.0) or 0.0)
                if "c" not in resolved and "corrosion_allowance" in task_inputs:
                    c_prepared = prepare_engineering_input(task_inputs["corrosion_allowance"])
                    c_allowance = float(c_prepared.value)
                inside_d = inside_diameter_from_od_and_thickness(outside_d, thickness)
                thick_y = compute_thick_wall_y(
                    inside_diameter=inside_d,
                    outside_diameter=outside_d,
                    corrosion_allowance=c_allowance,
                )
                if abs(thick_y - float(variables.get("Y", 0.0))) > 1e-9:
                    variables["Y"] = thick_y
                    resolved["Y"] = thick_y
                    try:
                        calculation = fn(node_dir=record.path.parent, variables=variables)
                    except Exception as exc:  # noqa: BLE001
                        return NodeExecutionResult(
                            node_id=record.node_id,
                            status=NodeExecutionStatus.ERROR,
                            errors=[str(exc)],
                            inputs=resolved,
                        )
                    warnings.append(
                        "Thick-wall coefficient Y applied per §304.1.1(b): Y = (d + 2c) / (D + d + 2c)"
                    )
                    if calculation.final_result:
                        eval_vars["t"] = calculation.final_result.value
                        thickness = float(calculation.final_result.value)

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
            sets_field = str(condition.get("sets_field", ""))
            if sets_field:
                thin_wall_valid = cond_result.passed
            if not cond_result.passed:
                on_false = str(condition.get("on_false", ""))
                if on_false == "subsection_b":
                    subsections = record.metadata.get("subsections", []) or []
                    subsection_b = next(
                        (
                            item
                            for item in subsections
                            if isinstance(item, dict) and item.get("id") == "b"
                        ),
                        None,
                    )
                    if subsection_b and str(subsection_b.get("status", "")) == "not_implemented":
                        warnings.append(
                            "Thin-wall check failed (t >= D/6). "
                            "Subsection (b) thick-wall design is not yet implemented."
                        )
                elif cond_result.message:
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
            "thin_wall": thin_wall_valid,
        }

        tm_value = self._compute_minimum_required_thickness(
            record,
            task_inputs=task_inputs,
            thickness_t=final.value if final else None,
        )
        if tm_value is not None:
            outputs["minimum_required_thickness"] = tm_value
            outputs["t_m"] = tm_value

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

        nomenclature = load_nomenclature_for_node(self._reader, record.metadata)
        d_error = self._resolve_outside_diameter(
            record,
            task_inputs=task_inputs,
            resolved=resolved,
            missing=missing,
            nomenclature=nomenclature,
        )
        if d_error and d_error not in missing:
            missing.append(d_error)

        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            spec = resolve_input_spec(spec, nomenclature) if nomenclature else spec
            if not input_applies(spec, task_inputs):
                continue
            input_id = str(spec.get("id", ""))
            symbol = str(spec.get("name", input_id))
            if symbol == "D" or input_id == "outside_diameter":
                if "D" in resolved:
                    continue
            if input_id == "nominal_pipe_size":
                continue
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
                stored = task_inputs[input_id]
                if bool(spec.get("requires_confirmation", False)) and not input_is_expansion_ready(
                    stored
                ):
                    missing.append(input_id)
                    continue
                prepared = prepare_engineering_input(stored)
                resolved[symbol] = prepared.value
                resolved[f"{symbol}_unit"] = prepared.unit
                continue
            elif source == "resolved":
                if input_id in task_inputs:
                    stored = task_inputs[input_id]
                    if bool(spec.get("requires_confirmation", False)) and not input_is_expansion_ready(
                        stored
                    ):
                        missing.append(input_id)
                        continue
                    prepared = prepare_engineering_input(stored)
                    resolved[symbol] = prepared.value
                    resolved[f"{symbol}_unit"] = prepared.unit
                    continue
                if required:
                    missing.append(input_id)
                continue
            elif source == "default" and spec.get("default") is not None:
                if bool(spec.get("requires_confirmation", False)):
                    if input_id not in task_inputs:
                        if required:
                            missing.append(input_id)
                        continue
                    stored = task_inputs[input_id]
                    if not input_is_expansion_ready(stored):
                        if required:
                            missing.append(input_id)
                        continue
                    prepared = prepare_engineering_input(stored)
                    resolved[symbol] = prepared.value
                    resolved[f"{symbol}_unit"] = prepared.unit
                    continue
                value = spec.get("default")
            elif input_id in dependency_outputs:
                value = dependency_outputs[input_id]

            if value is None:
                if required:
                    missing.append(input_id)
                continue

            resolved[symbol] = value

        return resolved, missing

    def _resolve_outside_diameter(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, EngineeringInput],
        resolved: dict[str, Any],
        missing: list[str],
        nomenclature: dict,
    ) -> str | None:
        del record, nomenclature
        mode = field_value("d_input_mode", task_inputs)
        if mode is None:
            if "outside_diameter" in task_inputs:
                mode = "direct_od"
            else:
                mode = "nps_lookup"

        if mode == "nps_lookup":
            nps = field_value("nominal_pipe_size", task_inputs)
            if nps is None:
                return "nominal_pipe_size"
            try:
                lookup = PipeDimensionLookup(self._reader.standards_root)
                result = lookup.lookup(str(nps))
                resolved["D"] = result.outside_diameter_mm
                resolved["D_unit"] = "mm"
                resolved["D_source"] = "asme_b36.10"
                return None
            except (ValueError, FileNotFoundError):
                return "nominal_pipe_size"

        if "outside_diameter" not in task_inputs:
            return "outside_diameter"
        stored = task_inputs["outside_diameter"]
        prepared = prepare_engineering_input(stored)
        resolved["D"] = prepared.value
        resolved["D_unit"] = prepared.unit
        return None

    @staticmethod
    def _missing_inputs(
        record: NodeRecord,
        task_inputs: dict[str, EngineeringInput],
    ) -> list[str]:
        missing: list[str] = []
        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            if not input_applies(spec, task_inputs):
                continue
            input_id = str(spec.get("id", ""))
            if bool(spec.get("required", True)) and input_id not in task_inputs:
                if input_id == "outside_diameter" and field_value("d_input_mode", task_inputs) == "nps_lookup":
                    if "nominal_pipe_size" not in task_inputs:
                        missing.append("nominal_pipe_size")
                    continue
                if input_id == "nominal_pipe_size" and field_value("d_input_mode", task_inputs) == "direct_od":
                    continue
                missing.append(input_id)
        if field_value("d_input_mode", task_inputs) is None and "d_input_mode" not in task_inputs:
            if "outside_diameter" not in task_inputs and "nominal_pipe_size" not in task_inputs:
                missing.append("nominal_pipe_size")
        return missing

    @staticmethod
    def _compute_minimum_required_thickness(
        record: NodeRecord,
        *,
        task_inputs: dict[str, EngineeringInput],
        thickness_t: float | None,
    ) -> float | None:
        if thickness_t is None:
            return None
        if "corrosion_allowance" not in task_inputs:
            return None
        stored = task_inputs["corrosion_allowance"]
        if stored.requires_confirmation and not input_is_expansion_ready(stored):
            return None
        c_prepared = prepare_engineering_input(stored)
        c_value = float(c_prepared.value)
        if record.node_id != "B313-304.1.2":
            return thickness_t + c_value
        from engine.executor.functions import get_execution_function

        fn = get_execution_function("calculate_minimum_required_thickness")
        if fn is None:
            return thickness_t + c_value
        definition_path = record.path.parent.parent / "B313-304.1.1"
        try:
            calculation = fn(
                node_dir=definition_path,
                variables={"t": float(thickness_t), "c": c_value},
            )
            if calculation.final_result:
                return float(calculation.final_result.value)
        except Exception:  # noqa: BLE001
            return thickness_t + c_value
        return thickness_t + c_value

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
