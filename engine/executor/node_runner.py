"""Single-node execution lifecycle."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from engine.equation.equation_display_trace_builder import build_equation_display_trace
from engine.equation.equation_renderer import EquationRenderSteps
from engine.equation.sympy_evaluator import evaluate_equation
from models.calculation import CalculationResult, QuantityResult
from engine.graph.assumption_checker import field_value, evaluate_node_execution_assumptions
from engine.graph.param_priority import normalize_require_ids
from engine.graph.relationship_resolver import resolve_require_bindings
from engine.reference.node_types import (
    is_designation_node,
    is_lookup_node,
    is_quantity_node,
    is_section_node,
    is_table_node,
    is_ui_parameter,
)
from engine.graph.node_interaction import evaluate_node_interactions
from engine.executor.functions import get_execution_function
from engine.executor.lookup_engine import LookupEngine
from engine.executor.unit_manager import prepare_fact, prepare_symbol_map
from engine.executor.validation_rule_runner import execute_validation_rule
from engine.reference.nomenclature_resolver import (
    enrich_input_spec,
    input_applies,
    load_nomenclature_for_node,
    spec_symbol,
)
from engine.reference.parameter_keys import fact_for_task_input, read_fact_value
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.embedded_nodes import find_embedded_body
from engine.reference.standards_reader import NodeRecord, StandardsReader
from engine.rules.rule_engine import RuleEngine
from models.execution import NodeExecutionResult, NodeExecutionStatus
from models.fact import Fact, ValidationStatus, fact_is_expansion_ready, fact_scalar_value, fact_unit
from models.task import Task


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
        task_inputs: dict[str, Fact],
        dependency_outputs: dict[str, Any],
        task: Task | None = None,
    ) -> NodeExecutionResult:
        record = self._reader.load(node_id)
        node_type = str(record.metadata.get("type", ""))
        metadata = record.metadata

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

        if node_type == "equation" and is_lookup_node(metadata, node_type):
            if metadata.get("output_param"):
                return self._run_micro_lookup(record, task_inputs=task_inputs)
            return self._run_lookup(record, task_inputs=task_inputs)
        if node_type == "equation" and (
            metadata.get("executor") or metadata.get("execution_function")
        ):
            return self._run_executor_equation(
                record,
                task_inputs=task_inputs,
                dependency_outputs=dependency_outputs,
            )
        if node_type == "equation":
            return self._run_equation_node(
                record,
                task_inputs=task_inputs,
                dependency_outputs=dependency_outputs,
            )
        if (
            node_type in {"workflow", "text", "parameter", "quantity", "designation"}
            or is_section_node(metadata, node_type)
            or is_table_node(metadata, node_type)
            or is_ui_parameter(metadata, node_type)
            or is_quantity_node(metadata, node_type)
            or is_designation_node(metadata, node_type)
        ):
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.SKIPPED,
                trace={"reason": f"{node_type} node — graph reference only"},
            )
        if node_type == "lookup" and metadata.get("output_param"):
            return self._run_micro_lookup(record, task_inputs=task_inputs)
        if node_type == "lookup":
            return self._run_lookup(record, task_inputs=task_inputs)
        if node_type == "validation_rule":
            return self._run_validation_rule(
                record,
                task_inputs=task_inputs,
                dependency_outputs=dependency_outputs,
                task=task,
            )
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

    def _run_validation_rule(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, Fact],
        dependency_outputs: dict[str, Any],
        task: Task | None = None,
    ) -> NodeExecutionResult:
        return execute_validation_rule(
            record,
            reader=self._reader,
            rule_engine=self._rule_engine,
            task_inputs=task_inputs,
            dependency_outputs=dependency_outputs,
            resolve_value=self._resolve_parameter_value,
            param_fact_key=self._param_fact_key,
            output_alias_keys=self._output_alias_keys,
            task=task,
        )

    @staticmethod
    def _param_fact_key(param_meta: dict[str, Any]) -> str:
        return str(param_meta.get("input_id") or param_meta.get("key") or "").strip()

    def _lookup_returns_fact_key(self, record: NodeRecord) -> str | None:
        for item in record.metadata.get("returns") or []:
            if not isinstance(item, dict):
                continue
            param_id = str(item.get("parameter") or "").strip()
            if not param_id:
                continue
            try:
                param = self._reader.load(param_id)
            except FileNotFoundError:
                continue
            fact_key = self._param_fact_key(param.metadata)
            if fact_key:
                return fact_key
        return None

    def _lookup_output_already_satisfied(
        self,
        record: NodeRecord,
        task_inputs: dict[str, Fact],
    ) -> bool:
        fact_key = self._lookup_returns_fact_key(record)
        if not fact_key or fact_key not in task_inputs:
            return False
        stored = task_inputs[fact_key]
        if fact_scalar_value(stored) is None:
            return False
        if stored.requires_confirmation and not fact_is_expansion_ready(stored):
            return False
        return True

    def _run_lookup(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, Fact],
    ) -> NodeExecutionResult:
        if self._lookup_output_already_satisfied(record, task_inputs):
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.SKIPPED,
                trace={"reason": "lookup output already confirmed in task facts"},
            )

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
            fact_key = str(spec.get("task_input_id") or input_id).strip()
            source_fact = None
            if fact_key in task_inputs:
                source_fact = task_inputs[fact_key]
            elif input_id in task_inputs:
                source_fact = task_inputs[input_id]
            elif fact_key == "material_grade" and "material" in task_inputs:
                source_fact = task_inputs["material"]
            elif fact_key == "material" and "material_grade" in task_inputs:
                source_fact = task_inputs["material_grade"]
            if source_fact is not None:
                target_unit = None
                if fact_key == "design_temperature":
                    target_unit = "f"
                prepared = prepare_fact(
                    source_fact,
                    target_unit=target_unit,
                )
                raw_inputs[input_id or fact_key] = fact_scalar_value(prepared)
                if fact_key == "design_temperature":
                    raw_inputs["design_temperature"] = fact_scalar_value(prepared)
                    raw_inputs["design_temperature_unit"] = fact_unit(prepared)
                raw_inputs[f"{input_id}_unit"] = fact_unit(prepared)

        lookups = record.metadata.get("lookups", []) or []
        lookup_block = record.metadata.get("lookup")
        if isinstance(lookup_block, dict):
            lookup_config = dict(lookup_block)
        elif lookups and isinstance(lookups[0], dict):
            lookup_config = dict(lookups[0])
        else:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=["No lookup configuration found"],
            )

        from engine.executor.lookup_rule_schema import lookup_bindings
        from engine.graph.lookup_parameter_resolution import _resolve_lookup_key

        bindings = lookup_bindings(record.metadata)
        if bindings:
            engine_inputs: dict[str, Any] = {}
            store = self._reader.graph_store
            for logical_key, param_ref in bindings.items():
                fact_key = _resolve_lookup_key(store, param_ref)
                source_fact = task_inputs.get(fact_key)
                if source_fact is None and fact_key == "material_grade" and "material" in task_inputs:
                    source_fact = task_inputs["material"]
                if source_fact is None:
                    continue
                target_unit = "f" if logical_key == "design_temperature" else None
                prepared = prepare_fact(source_fact, target_unit=target_unit)
                engine_inputs[logical_key] = fact_scalar_value(prepared)
                if logical_key == "design_temperature":
                    engine_inputs["design_temperature_unit"] = fact_unit(prepared)
                if logical_key == "nominal_pipe_size":
                    from engine.reference.nps_normalization import nps_entry_unit

                    engine_inputs["nominal_pipe_size_unit"] = nps_entry_unit(source_fact)
        else:
            engine_inputs = dict(raw_inputs)
            if "material_grade" in engine_inputs and "material" not in engine_inputs:
                engine_inputs["material"] = engine_inputs["material_grade"]
            if "material" in engine_inputs and "material_grade" not in engine_inputs:
                engine_inputs["material_grade"] = engine_inputs["material"]
            if "temperature" in engine_inputs and "design_temperature" not in engine_inputs:
                engine_inputs["design_temperature"] = engine_inputs["temperature"]

        table_ref = str(
            lookup_config.get("table_id")
            or lookup_config.get("table")
            or ""
        ).strip()
        source = record.metadata.get("source")
        if isinstance(source, dict):
            db_table_id = str(source.get("table_id") or "").strip()
            if db_table_id:
                table_ref = self._lookup_engine._resolve_table_ref(db_table_id)
        try:
            lookup_rule = str(
                lookup_config.get("rule") or lookup_config.get("lookup_rule") or ""
            ).strip()
            if not lookup_rule:
                return NodeExecutionResult(
                    node_id=record.node_id,
                    status=NodeExecutionStatus.ERROR,
                    errors=["lookup.rule is required"],
                    inputs=engine_inputs,
                )
            rule_result = self._lookup_engine.execute_rule_lookup(
                table_ref=table_ref,
                rule=lookup_rule,
                inputs=engine_inputs,
                returns=list(record.metadata.get("returns") or []),
            )
            outputs = dict(rule_result.outputs)
            trace_payload = {
                "table_id": table_ref or rule_result.meta.get("table_ref") or "",
                "rule": lookup_rule,
                "outputs": dict(outputs),
                "meta": dict(rule_result.meta),
            }
        except (ValueError, FileNotFoundError) as exc:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[str(exc)],
                inputs=engine_inputs,
            )

        for item in record.metadata.get("returns") or []:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol") or "").strip()
            param_id = str(item.get("parameter") or "").strip()
            value = outputs.get(symbol) or outputs.get("value")
            if value is None:
                continue
            if symbol and symbol not in outputs:
                outputs[symbol] = value
            if param_id:
                try:
                    param = self._reader.load(param_id)
                    fact_key = self._param_fact_key(param.metadata)
                    if fact_key:
                        outputs[fact_key] = value
                except FileNotFoundError:
                    pass

        return self._finalize_result(
            record,
            status=NodeExecutionStatus.COMPLETED,
            inputs=engine_inputs,
            outputs=outputs,
            trace=trace_payload,
        )

    def _run_calculation(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, Fact],
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
            symbol = spec_symbol(spec)
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

        equation_meta = self._primary_equation_meta(record, self._reader)
        if not equation_meta:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=["No equation configuration found"],
            )

        function_name = str(
            equation_meta.get("execution_function") or equation_meta.get("executor", "")
        ).strip()
        fn = get_execution_function(function_name)
        if fn is None:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[f"Unapproved execution function: {function_name}"],
            )

        try:
            calculation = fn(
                node_dir=record.path.parent,
                variables=variables,
                reader=self._reader,
                record=record,
                equation_meta=equation_meta,
            )
        except Exception as exc:  # noqa: BLE001 — surface execution errors to task state
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[str(exc)],
                inputs=resolved,
            )

        symbol_map = {"P": "P", "D": "D", "S": "S", "E_j": "E_j", "W": "W", "Y": "Y", "t": "t"}
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
                    c_prepared = prepare_fact(task_inputs["corrosion_allowance"])
                    c_allowance = float(fact_scalar_value(c_prepared))
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
                        calculation = fn(
                            node_dir=record.path.parent,
                            variables=variables,
                            reader=self._reader,
                            record=record,
                            equation_meta=equation_meta,
                        )
                    except Exception as exc:  # noqa: BLE001
                        return NodeExecutionResult(
                            node_id=record.node_id,
                            status=NodeExecutionStatus.ERROR,
                            errors=[str(exc)],
                            inputs=resolved,
                        )
                    warnings.append(
                        "Thick-wall coefficient Y applied per §304.1.1-b: Y = (d + 2c) / (D + d + 2c)"
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
        output_symbol = "t"
        for spec in record.metadata.get("outputs", []) or []:
            if isinstance(spec, dict) and spec.get("id"):
                output_id = str(spec["id"])
                output_symbol = spec_symbol(spec, fallback=output_id)
                break

        final = calculation.final_result
        outputs: dict[str, Any] = {
            output_id: final.value if final else None,
        }
        if output_symbol:
            outputs[output_symbol] = final.value if final else None
        if output_symbol == "t":
            outputs["required_thickness"] = final.value if final else None
            outputs["pressure_design_thickness"] = final.value if final else None
        if output_symbol == "MAWP":
            outputs["mawp"] = final.value if final else None
        outputs["thin_wall"] = thin_wall_valid
        for symbol, value in resolved.items():
            if str(symbol).endswith("_unit"):
                continue
            if not isinstance(value, (int, float)):
                continue
            outputs[str(symbol)] = float(value)
            for alias in self._OUTPUT_ALIASES.get(str(symbol), ()):
                outputs[alias] = float(value)

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

        trace_payload = {
            "calculation": asdict(calculation),
            "intermediates": intermediates,
            "variables_si": variables,
        }
        trace_payload = self._attach_equation_display_trace(
            trace_payload,
            record=record,
            symbol_values={
                key: float(value)
                for key, value in variables.items()
                if isinstance(value, (int, float))
            },
            dependency_outputs=dependency_outputs,
            task_inputs=task_inputs,
            calculation=calculation,
        )

        return self._finalize_result(
            record,
            status=NodeExecutionStatus.COMPLETED,
            inputs=resolved,
            outputs=outputs,
            warnings=warnings,
            trace=trace_payload,
        )

    def _resolve_calculation_inputs(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, Fact],
        dependency_outputs: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        legacy_inputs = record.metadata.get("inputs", []) or []
        requires = record.metadata.get("requires")
        if requires and not legacy_inputs:
            resolved: dict[str, Any] = {}
            missing: list[str] = []
            bindings = resolve_require_bindings(self._reader.graph_store, requires)
            for binding in bindings:
                value = self._resolve_parameter_value(
                    binding.param_id,
                    task_inputs=task_inputs,
                    dependency_outputs=dependency_outputs,
                    sympy_symbol=binding.sympy_symbol,
                )
                if value is None:
                    try:
                        param = self._reader.load(binding.param_id)
                        missing.append(
                            str(param.metadata.get("input_id") or binding.sympy_symbol)
                        )
                    except FileNotFoundError:
                        missing.append(binding.sympy_symbol)
                else:
                    resolved[binding.sympy_symbol] = value
            d_error = self._resolve_outside_diameter(
                record,
                task_inputs=task_inputs,
                resolved=resolved,
                missing=missing,
                nomenclature={},
            )
            if d_error and d_error not in missing:
                missing.append(d_error)
            return resolved, missing

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
            spec = enrich_input_spec(spec, nomenclature if nomenclature else None)
            if not input_applies(spec, task_inputs):
                continue
            input_id = str(spec.get("id", ""))
            symbol = spec_symbol(spec, fallback=input_id)
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
                if bool(spec.get("requires_confirmation", False)) and not fact_is_expansion_ready(
                    stored
                ):
                    missing.append(input_id)
                    continue
                prepared = prepare_fact(stored)
                resolved[symbol] = fact_scalar_value(prepared)
                resolved[f"{symbol}_unit"] = fact_unit(prepared)
                continue
            elif source == "resolved":
                if input_id in task_inputs:
                    stored = task_inputs[input_id]
                    if bool(spec.get("requires_confirmation", False)) and not fact_is_expansion_ready(
                        stored
                    ):
                        missing.append(input_id)
                        continue
                    prepared = prepare_fact(stored)
                    resolved[symbol] = fact_scalar_value(prepared)
                    resolved[f"{symbol}_unit"] = fact_unit(prepared)
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
                    if not fact_is_expansion_ready(stored):
                        if required:
                            missing.append(input_id)
                        continue
                    prepared = prepare_fact(stored)
                    resolved[symbol] = fact_scalar_value(prepared)
                    resolved[f"{symbol}_unit"] = fact_unit(prepared)
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

    @staticmethod
    def _primary_equation_meta(
        record: NodeRecord,
        reader: StandardsReader | None = None,
    ) -> dict[str, Any] | None:
        metadata = record.metadata
        if metadata.get("executor") or metadata.get("execution_function"):
            return metadata
        for child_id in record.metadata.get("contains", []) or []:
            child = str(child_id).strip()
            if "eq" not in child.lower():
                continue
            body = find_embedded_body(record.metadata, child)
            if body is None:
                slug = (
                    child.split("B313-eq-", 1)[-1].replace("-", "_")
                    if "B313-eq-" in child
                    else child
                )
                body = find_embedded_body(record.metadata, f"equations/{slug}.md")
            if body is None:
                continue
            metadata, _ = split_frontmatter(body)
            if metadata.get("executor") or metadata.get("execution_function"):
                return metadata

        equations = record.metadata.get("equations", []) or record.metadata.get("formulas", []) or []
        for equation in equations:
            if not isinstance(equation, dict):
                continue
            if equation.get("execution_function") or equation.get("executor"):
                merged = dict(equation)
                if reader is not None and equation.get("file"):
                    text = reader.read_asset_text(record, str(equation["file"]))
                    if text:
                        file_meta, _ = split_frontmatter(text)
                        if isinstance(file_meta, dict):
                            merged.update({k: v for k, v in file_meta.items() if k not in merged or not merged[k]})
                    eq_id = str(equation.get("id") or merged.get("id") or "").strip()
                    if eq_id:
                        try:
                            eq_record = reader.load(eq_id)
                            for key in (
                                "executor",
                                "execution_function",
                                "variables",
                                "steps",
                                "outputs",
                                "calculation_module",
                            ):
                                if eq_record.metadata.get(key) and not merged.get(key):
                                    merged[key] = eq_record.metadata[key]
                        except FileNotFoundError:
                            pass
                return merged
            if equation.get("source"):
                parsed_meta, _ = split_frontmatter(str(equation["source"]))
                if isinstance(parsed_meta, dict) and (
                    parsed_meta.get("executor") or parsed_meta.get("execution_function")
                ):
                    merged = dict(equation)
                    merged.update(parsed_meta)
                    return merged
        return None

    def _resolve_outside_diameter(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, Fact],
        resolved: dict[str, Any],
        missing: list[str],
        nomenclature: dict,
    ) -> str | None:
        del record, nomenclature, missing
        from engine.graph.resolution_branches import active_resolution_branch_id
        from engine.graph.lookup_resolution_service import OUTSIDE_DIAMETER_LOOKUP_NODE, lookup_node_metadata
        from engine.reference.nps_normalization import nps_entry_unit, to_nps_lookup_key

        mode = active_resolution_branch_id("outside_diameter", task_inputs)
        if mode is None:
            mode = "nps_lookup"

        if mode == "direct_od":
            if "outside_diameter" not in task_inputs:
                return "outside_diameter"
            stored = task_inputs["outside_diameter"]
            prepared = prepare_fact(stored)
            resolved["D"] = fact_scalar_value(prepared)
            resolved["D_unit"] = fact_unit(prepared)
            return None

        if "outside_diameter" in task_inputs:
            stored = task_inputs["outside_diameter"]
            if fact_scalar_value(stored) is not None:
                prepared = prepare_fact(stored)
                resolved["D"] = fact_scalar_value(prepared)
                resolved["D_unit"] = fact_unit(prepared)
                resolved["D_source"] = stored.source.source_id if stored.source else None
                return None

        if mode == "nps_lookup":
            nps = field_value("nominal_pipe_size", task_inputs)
            if nps is None:
                return "nominal_pipe_size"
            nps_fact = task_inputs.get("nominal_pipe_size")
            try:
                table_ref, rule, _keys = lookup_node_metadata(self._reader, OUTSIDE_DIAMETER_LOOKUP_NODE)
                if not table_ref or not rule:
                    return "nominal_pipe_size"
                lookup_inputs: dict[str, Any] = {"nominal_pipe_size": str(nps)}
                if nps_fact is not None:
                    entry_unit = nps_entry_unit(nps_fact)
                    lookup_inputs["nominal_pipe_size"] = to_nps_lookup_key(str(nps), entry_unit)
                    lookup_inputs["nominal_pipe_size_unit"] = entry_unit
                rule_result = self._lookup_engine.execute_rule_lookup(
                    table_ref=table_ref,
                    rule=rule,
                    inputs=lookup_inputs,
                )
                outside_diameter = rule_result.outputs.get("outside_diameter")
                if outside_diameter is None:
                    return "nominal_pipe_size"
                resolved["D"] = outside_diameter
                resolved["D_unit"] = "mm"
                resolved["D_source"] = table_ref
                return None
            except (ValueError, FileNotFoundError):
                return "nominal_pipe_size"

        if "outside_diameter" not in task_inputs:
            return "outside_diameter"
        stored = task_inputs["outside_diameter"]
        prepared = prepare_fact(stored)
        resolved["D"] = fact_scalar_value(prepared)
        resolved["D_unit"] = fact_unit(prepared)
        return None

    @staticmethod
    def _missing_inputs(
        record: NodeRecord,
        task_inputs: dict[str, Fact],
    ) -> list[str]:
        missing: list[str] = []
        node_type = str(record.metadata.get("type", ""))
        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            if not input_applies(spec, task_inputs):
                continue
            input_id = str(spec.get("id", ""))
            fact_key = input_id
            if node_type == "lookup":
                fact_key = str(spec.get("task_input_id") or input_id).strip()
            if bool(spec.get("required", True)) and fact_key not in task_inputs:
                if fact_key == "material_grade" and "material" in task_inputs:
                    continue
                if fact_key == "material" and "material_grade" in task_inputs:
                    continue
                from engine.graph.resolution_branches import active_resolution_branch_id

                od_branch = active_resolution_branch_id("outside_diameter", task_inputs)
                if input_id == "outside_diameter" and od_branch == "nps_lookup":
                    if "nominal_pipe_size" not in task_inputs:
                        missing.append("nominal_pipe_size")
                    continue
                if input_id == "nominal_pipe_size" and od_branch == "direct_od":
                    continue
                missing.append(input_id)
        from engine.graph.resolution_branches import (
            active_resolution_branch_id,
            resolution_branch_fact_key,
        )

        branch_key = resolution_branch_fact_key("outside_diameter")
        if (
            active_resolution_branch_id("outside_diameter", task_inputs) is None
            and branch_key not in task_inputs
        ):
            if "outside_diameter" not in task_inputs and "nominal_pipe_size" not in task_inputs:
                missing.append("nominal_pipe_size")
        return missing

    def _compute_minimum_required_thickness(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, Fact],
        thickness_t: float | None,
    ) -> float | None:
        if thickness_t is None:
            return None
        if "corrosion_allowance" not in task_inputs:
            return None
        stored = task_inputs["corrosion_allowance"]
        if stored.requires_confirmation and not fact_is_expansion_ready(stored):
            return None
        c_prepared = prepare_fact(stored)
        c_value = float(fact_scalar_value(c_prepared))
        if record.node_id not in {"304.1.2-a", "304.1.2"}:
            return thickness_t + c_value
        from engine.executor.functions import get_execution_function

        fn = get_execution_function("calculate_minimum_required_thickness")
        if fn is None:
            return thickness_t + c_value
        eq_record: NodeRecord | None = None
        try:
            eq_record = self._reader.load("asme-b313-304-1-1-eq-2")
            definition_path = eq_record.path.parent
        except FileNotFoundError:
            definition_path = record.path.parent
        try:
            calculation = fn(
                node_dir=definition_path,
                variables={"t": float(thickness_t), "c": c_value},
                reader=self._reader,
                record=eq_record or record,
                equation_meta={"file": "../equation/asme-b313-304-1-1-eq-2.yaml"},
            )
            if calculation.final_result:
                return float(calculation.final_result.value)
        except Exception:  # noqa: BLE001
            return thickness_t + c_value
        return thickness_t + c_value

    _OUTPUT_ALIASES: dict[str, tuple[str, ...]] = {
        "t": ("t", "required_thickness", "thickness"),
        "t_m": ("t_m", "minimum_required_thickness"),
        "S": ("S", "allowable_stress"),
    }

    def _resolve_parameter_value(
        self,
        param_node_id: str,
        *,
        task_inputs: dict[str, Fact],
        dependency_outputs: dict[str, Any],
        sympy_symbol: str = "",
    ) -> float | None:
        try:
            param = self._reader.load(param_node_id)
        except FileNotFoundError:
            return None
        symbol = str(
            sympy_symbol
            or param.metadata.get("canonical_symbol")
            or param.metadata.get("symbol")
            or ""
        ).strip()
        fact_key = self._param_fact_key(param.metadata)
        for key in self._output_alias_keys(symbol, fact_key):
            if key in dependency_outputs:
                value = dependency_outputs[key]
                if value is not None:
                    return float(value)
        stored = fact_for_task_input(task_inputs, fact_key) if fact_key else None
        if stored is not None:
            prepared = prepare_fact(stored)
            scalar = fact_scalar_value(prepared)
            if scalar is not None:
                try:
                    return float(scalar)
                except (TypeError, ValueError):
                    return None
        if fact_key:
            value = read_fact_value(task_inputs, fact_key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
        if fact_key:
            value = field_value(fact_key, task_inputs)
            if value is not None:
                return float(value)
        resolution = param.metadata.get("resolution") or {}
        if isinstance(resolution, dict) and resolution.get("method") == "table_lookup":
            return self._resolve_table_lookup_parameter(param, resolution, task_inputs)
        return None

    def _output_alias_keys(self, symbol: str, fact_key: str) -> list[str]:
        keys: list[str] = []
        if symbol:
            keys.extend(self._OUTPUT_ALIASES.get(symbol, (symbol,)))
        if fact_key and fact_key not in keys:
            keys.append(fact_key)
        return keys

    def _resolve_table_lookup_parameter(
        self,
        param: NodeRecord,
        resolution: dict[str, Any],
        task_inputs: dict[str, Fact],
    ) -> float | None:
        table_id = str(resolution.get("table_id", "")).strip()
        if not table_id:
            return None
        keys = [str(key) for key in (resolution.get("keys") or [])]
        lookup_inputs: dict[str, Any] = {}
        for key in keys:
            if key in task_inputs:
                lookup_inputs[key] = task_inputs[key]
            elif field_value(key, task_inputs) is not None:
                lookup_inputs[key] = field_value(key, task_inputs)
            else:
                return None
        try:
            lookup_result = self._lookup_engine.lookup(table_id, lookup_inputs)
        except Exception:  # noqa: BLE001
            return None
        return float(lookup_result.value) if lookup_result.value is not None else None

    def _run_equation_node(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, Fact],
        dependency_outputs: dict[str, Any],
    ) -> NodeExecutionResult:
        sympy_expr = str(record.metadata.get("sympy") or "").strip()
        executor_name = str(
            record.metadata.get("executor") or record.metadata.get("execution_function") or ""
        ).strip()
        if not sympy_expr and executor_name:
            return self._run_executor_equation(
                record,
                task_inputs=task_inputs,
                dependency_outputs=dependency_outputs,
            )
        if not sympy_expr:
            store = self._reader.graph_store
            for edge in store.incoming(record.node_id, edge_types={"contains"}):
                parent = store.get_node(edge.from_id)
                if parent is not None and parent.node_type == "calculation":
                    return NodeExecutionResult(
                        node_id=record.node_id,
                        status=NodeExecutionStatus.SKIPPED,
                        trace={"reason": f"executed via parent calculation node {edge.from_id}"},
                    )
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[f"No equation execution configuration for {record.node_id}"],
            )
        display = str(record.metadata.get("display_latex") or sympy_expr)
        requires = record.metadata.get("requires")
        calculates = record.metadata.get("calculates") or []
        store = self._reader.graph_store
        bindings = resolve_require_bindings(store, requires)

        symbol_values: dict[str, float] = {}
        missing: list[str] = []
        for binding in bindings:
            param = self._reader.load(binding.param_id)
            value = self._resolve_parameter_value(
                binding.param_id,
                task_inputs=task_inputs,
                dependency_outputs=dependency_outputs,
                sympy_symbol=binding.sympy_symbol,
            )
            if value is None:
                missing.append(str(param.metadata.get("input_id") or binding.sympy_symbol))
            else:
                symbol_values[binding.sympy_symbol] = value

        if missing:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.AWAITING_INPUT,
                errors=[f"Missing required inputs: {', '.join(missing)}"],
                trace={"missing_inputs": missing},
            )

        try:
            result = evaluate_equation(
                sympy_expr=sympy_expr,
                display_latex=display,
                symbol_values=symbol_values,
            )
        except Exception as exc:  # noqa: BLE001
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[str(exc)],
            )

        outputs: dict[str, Any] = dict(result.outputs)
        for symbol, value in symbol_values.items():
            outputs[symbol] = value
            for alias in self._OUTPUT_ALIASES.get(symbol, ()):
                outputs[alias] = value
        for ref in calculates:
            param = self._reader.load(str(ref))
            input_id = str(param.metadata.get("input_id", ""))
            symbol = str(param.metadata.get("symbol", ""))
            if symbol in result.outputs:
                value = result.outputs[symbol]
                if input_id:
                    outputs[input_id] = value
                outputs[symbol] = value
                for alias in self._OUTPUT_ALIASES.get(symbol, ()):
                    outputs[alias] = value

        trace_payload = {
            "substitution": result.substitution,
            "result_text": result.result_text,
            "equation": display,
            "render_steps": asdict(result.render_steps),
        }
        sympy_calculation = self._calculation_from_sympy_result(record, result.outputs)
        trace_payload = self._attach_equation_display_trace(
            trace_payload,
            record=record,
            symbol_values=symbol_values,
            dependency_outputs=dependency_outputs,
            task_inputs=task_inputs,
            calculation=sympy_calculation,
            render_steps=result.render_steps,
        )

        return self._finalize_result(
            record,
            status=NodeExecutionStatus.COMPLETED,
            inputs=symbol_values,
            outputs=outputs,
            trace=trace_payload,
        )

    def _run_micro_lookup(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, Fact],
    ) -> NodeExecutionResult:
        table_id = str(record.metadata.get("table_id", ""))
        keys = [str(key) for key in (record.metadata.get("keys") or [])]
        output_param_id = str(record.metadata.get("output_param", ""))
        missing = [key for key in keys if field_value(key, task_inputs) is None]
        if missing:
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.AWAITING_INPUT,
                errors=[f"Missing required inputs: {', '.join(missing)}"],
                trace={"missing_inputs": missing},
            )

        lookup_inputs: dict[str, Any] = {}
        for key in keys:
            target_unit = "f" if key == "design_temperature" else None
            prepared = prepare_fact(task_inputs[key], target_unit=target_unit)
            lookup_inputs[key] = fact_scalar_value(prepared)
            if key == "design_temperature":
                lookup_inputs["design_temperature_unit"] = fact_unit(prepared)

        try:
            lookup_result = self._lookup_engine.lookup(table_id, lookup_inputs)
        except Exception as exc:  # noqa: BLE001
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[str(exc)],
            )

        outputs: dict[str, Any] = {"value": lookup_result.value}
        if output_param_id:
            try:
                param = self._reader.load(output_param_id)
                input_id = str(param.metadata.get("input_id", ""))
                symbol = str(param.metadata.get("symbol", ""))
                if input_id:
                    outputs[input_id] = lookup_result.value
                if symbol:
                    outputs[symbol] = lookup_result.value
            except FileNotFoundError:
                pass

        return self._finalize_result(
            record,
            status=NodeExecutionStatus.COMPLETED,
            inputs=lookup_inputs,
            outputs=outputs,
            trace={"table_id": table_id},
        )

    _CRITICAL_EQUATION_OUTPUT_KEYS = frozenset(
        {
            "t",
            "t_m",
            "required_thickness",
            "minimum_required_thickness",
            "required_wall_thickness",
            "pressure_design_thickness",
        }
    )

    def _equation_produces_critical_output(self, record: NodeRecord) -> bool:
        for spec in record.metadata.get("outputs", []) or []:
            if not isinstance(spec, dict):
                continue
            for key in ("name", "symbol", "id"):
                value = str(spec.get(key) or "").strip()
                if value in self._CRITICAL_EQUATION_OUTPUT_KEYS:
                    return True
        for ref in record.metadata.get("calculates") or []:
            param_id = str(ref.get("parameter") if isinstance(ref, dict) else ref).strip()
            if not param_id:
                continue
            try:
                param = self._reader.load(param_id)
            except FileNotFoundError:
                continue
            fact_key = self._param_fact_key(param.metadata)
            symbol = str(param.metadata.get("symbol", "")).strip()
            if fact_key in self._CRITICAL_EQUATION_OUTPUT_KEYS or symbol in self._CRITICAL_EQUATION_OUTPUT_KEYS:
                return True
        return False

    def _run_executor_equation(
        self,
        record: NodeRecord,
        *,
        task_inputs: dict[str, Fact],
        dependency_outputs: dict[str, Any],
    ) -> NodeExecutionResult:
        requires = record.metadata.get("requires")
        store = self._reader.graph_store
        bindings = resolve_require_bindings(store, requires)
        resolved: dict[str, Any] = {}
        missing: list[str] = []
        for binding in bindings:
            param = self._reader.load(binding.param_id)
            value = self._resolve_parameter_value(
                binding.param_id,
                task_inputs=task_inputs,
                dependency_outputs=dependency_outputs,
                sympy_symbol=binding.sympy_symbol,
            )
            if value is None:
                missing.append(
                    str(param.metadata.get("input_id") or param.metadata.get("key") or binding.sympy_symbol)
                )
            else:
                resolved[binding.sympy_symbol] = value

        if missing:
            if not self._equation_produces_critical_output(record):
                return NodeExecutionResult(
                    node_id=record.node_id,
                    status=NodeExecutionStatus.SKIPPED,
                    trace={
                        "reason": (
                            "optional branch equation skipped; "
                            f"missing inputs: {', '.join(missing)}"
                        ),
                    },
                )
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.AWAITING_INPUT,
                errors=[f"Missing required inputs: {', '.join(missing)}"],
                trace={"missing_inputs": missing},
            )

        unit_map = self._symbol_unit_map(record)
        variables = prepare_symbol_map(resolved, unit_map)
        function_name = str(
            record.metadata.get("executor") or record.metadata.get("execution_function") or ""
        ).strip()
        fn = get_execution_function(function_name)
        if fn is None:
            if not self._equation_produces_critical_output(record):
                return NodeExecutionResult(
                    node_id=record.node_id,
                    status=NodeExecutionStatus.SKIPPED,
                    trace={"reason": f"optional branch equation skipped: unknown function {function_name}"},
                )
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[f"Unapproved execution function: {function_name}"],
            )

        equation_meta = dict(record.metadata)
        try:
            calculation = fn(
                node_dir=record.path.parent,
                variables=variables,
                reader=self._reader,
                record=record,
                equation_meta=equation_meta,
            )
        except Exception as exc:  # noqa: BLE001
            if not self._equation_produces_critical_output(record):
                return NodeExecutionResult(
                    node_id=record.node_id,
                    status=NodeExecutionStatus.SKIPPED,
                    trace={"reason": f"optional branch equation skipped: {exc}"},
                )
            return NodeExecutionResult(
                node_id=record.node_id,
                status=NodeExecutionStatus.ERROR,
                errors=[str(exc)],
                inputs=resolved,
            )

        outputs: dict[str, Any] = {}
        final = calculation.final_result
        if final and final.value is not None:
            symbol = str(final.symbol or "").strip()
            if symbol:
                outputs[symbol] = final.value
                for alias in self._OUTPUT_ALIASES.get(symbol, ()):
                    outputs[alias] = final.value

        for spec in record.metadata.get("outputs", []) or []:
            if not isinstance(spec, dict):
                continue
            symbol = spec_symbol(spec, fallback=str(spec.get("symbol", "")))
            name = str(spec.get("name", symbol)).strip()
            value = outputs.get(symbol)
            if value is None and final:
                value = final.value
            if value is not None:
                if name:
                    outputs[name] = value
                if symbol:
                    outputs[symbol] = value
                    for alias in self._OUTPUT_ALIASES.get(symbol, ()):
                        outputs[alias] = value

        calculates = record.metadata.get("calculates") or []
        for ref in calculates:
            if isinstance(ref, dict):
                param_id = str(ref.get("parameter") or ref.get("target") or "")
            else:
                param_id = str(ref)
            if not param_id:
                continue
            try:
                param = self._reader.load(param_id)
            except FileNotFoundError:
                continue
            fact_key = str(param.metadata.get("input_id") or param.metadata.get("key") or "").strip()
            symbol = str(param.metadata.get("symbol", "")).strip()
            value = outputs.get(symbol)
            if value is None and final:
                value = final.value
            if value is None:
                continue
            if fact_key:
                outputs[fact_key] = value
            if symbol:
                outputs[symbol] = value
                for alias in self._OUTPUT_ALIASES.get(symbol, ()):
                    outputs[alias] = value

        trace_payload = {"calculation": asdict(calculation)}
        trace_payload = self._attach_equation_display_trace(
            trace_payload,
            record=record,
            symbol_values={
                key: float(value)
                for key, value in resolved.items()
                if isinstance(value, (int, float))
            },
            dependency_outputs=dependency_outputs,
            task_inputs=task_inputs,
            calculation=calculation,
        )
        trace_payload["variables_si"] = prepare_symbol_map(
            resolved,
            self._symbol_unit_map(record),
        )

        return self._finalize_result(
            record,
            status=NodeExecutionStatus.COMPLETED,
            inputs=resolved,
            outputs=outputs,
            trace=trace_payload,
        )

    def _calculation_from_sympy_result(
        self,
        record: NodeRecord,
        outputs: dict[str, float],
    ) -> CalculationResult | None:
        if not outputs:
            return None
        symbol = next(iter(outputs))
        value = float(outputs[symbol])
        unit = ""
        for spec in record.metadata.get("outputs", []) or []:
            if isinstance(spec, dict) and str(spec.get("symbol", "")) == symbol:
                unit = str(spec.get("unit") or "")
                break
        return CalculationResult(
            calculation_id=record.node_id,
            final_result=QuantityResult(symbol=symbol, value=value, unit=unit),
        )

    def _attach_equation_display_trace(
        self,
        trace: dict[str, Any],
        *,
        record: NodeRecord,
        symbol_values: dict[str, float],
        dependency_outputs: dict[str, Any],
        task_inputs: dict[str, Fact],
        calculation: CalculationResult | None = None,
        render_steps: EquationRenderSteps | None = None,
        source_node_id: str = "",
        status: str | None = None,
    ) -> dict[str, Any]:
        node_type = str(record.metadata.get("type", ""))
        if node_type != "equation" and not record.metadata.get("requires"):
            return trace

        display_trace = build_equation_display_trace(
            reader=self._reader,
            equation_id=record.node_id,
            equation_metadata=record.metadata,
            symbol_values=symbol_values,
            source_node_id=source_node_id or record.node_id,
            dependency_outputs=dependency_outputs,
            task_inputs=task_inputs,
            calculation=calculation,
            render_steps=render_steps,
            status=status,  # type: ignore[arg-type]
        )
        updated = dict(trace)
        updated["equation_display_trace"] = display_trace.to_dict()
        return updated

    @staticmethod
    def _symbol_unit_map(record: NodeRecord) -> dict[str, str]:
        unit_map: dict[str, str] = {}
        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            symbol = spec_symbol(spec)
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
