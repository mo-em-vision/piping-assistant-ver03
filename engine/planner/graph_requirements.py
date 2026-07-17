"""Graph-driven engineering plan requirements from execution preview and PARAM nodes."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.graph_engine import GraphEngine
from engine.graph.graph_store import GraphStore
from engine.graph.lookup_parameter_resolution import (
    catalog_resolution_for_parameter,
    lookup_resolution_for_parameter,
    parameter_resolution_for_parameter,
)
from engine.graph.navigation_phases import PhasedNavigation
from engine.graph.workflow_navigation import WorkflowNavigationConfig, load_workflow_navigation
from models.planning import NavigationPhase
from engine.planner.question_spec_builder import build_question_spec
from engine.planner.workflow_goal_metadata import lookup_fields_for_workflow, selection_fields_for_workflow
from engine.reference.parameter_keys import (
    canonical_parameter_key,
    load_parameter_node_metadata,
    param_node_id_for_input,
)
from engine.reference.standards_reader import StandardsReader
from engine.reference.workflow_sidecar import _param_to_field
from models.engineering_plan import ActivationCondition, PlanRequirement, RequirementAlternative

_LOOKUP_SUFFIX = "_lookup"
_EQ_SUFFIX = "_eq"
_DIAMETER_RESOLUTION_ID = "REQ-diameter_resolution"
_OUTSIDE_DIAMETER_LOOKUP_ID = "REQ-outside_diameter_lookup"
_ALT_DIRECT_OD = "ALT-direct-outside-diameter"
_ALT_NPS_LOOKUP = "ALT-nps-lookup"
_GATE_PHASES = frozenset({"expansion_assumptions", "path_decisions"})
_COEFFICIENT_PHASE = "coefficient_resolution"
_EQUATION_PHASE = "equation_execution"
_REPORT_PHASE = "reporting"
_LATE_INPUT_PHASE = "definition_equation_completion"


def requirement_id(field: str) -> str:
    return f"REQ-{field}"


def lookup_requirement_id(field: str) -> str:
    return f"REQ-{field}{_LOOKUP_SUFFIX}"


def equation_requirement_id(
    field: str,
    existing: dict[str, PlanRequirement],
    *,
    target_field: str | None = None,
) -> str:
    canonical = canonical_parameter_key(field)
    if target_field and canonical == canonical_parameter_key(target_field):
        return f"REQ-{canonical}{_EQ_SUFFIX}"
    candidate = requirement_id(canonical)
    if candidate not in existing:
        return candidate
    return f"REQ-{canonical}{_EQ_SUFFIX}"


def _graph_store(reader: StandardsReader) -> GraphStore | None:
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    return micro.store if micro is not None else None


def _param_field(store: GraphStore, param_node_id: str) -> str:
    node = store.get_node(param_node_id)
    if node is None:
        return _param_to_field(param_node_id)
    key = str(node.metadata.get("key") or "").strip()
    if key:
        return canonical_parameter_key(key)
    return _param_to_field(param_node_id)


def _collect_planning_fields(
    *,
    nav_config: WorkflowNavigationConfig,
    phased: PhasedNavigation | None,
    missing_inputs: list[str] | None,
) -> list[tuple[str, str]]:
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()

    if phased is not None:
        for field in phased.all_missing:
            if field not in seen:
                phase = _phase_for_field(field, phased, nav_config)
                ordered.append((field, phase))
                seen.add(field)
        for phase_name, fields in phased.phase_missing.items():
            for field in fields:
                if field not in seen:
                    ordered.append((field, phase_name))
                    seen.add(field)
    else:
        for phase, fields in nav_config.phase_order:
            if phase not in {
                NavigationPhase.EXPANSION_ASSUMPTIONS,
                NavigationPhase.PATH_DECISIONS,
            }:
                continue
            for field in fields:
                if field not in seen:
                    ordered.append((field, phase.value))
                    seen.add(field)
        for field in missing_inputs or []:
            if field not in seen:
                phase = _phase_for_field(field, None, nav_config)
                ordered.append((field, phase))
                seen.add(field)
    return ordered


def _phase_for_field(
    field: str,
    phased: PhasedNavigation | None,
    nav_config: WorkflowNavigationConfig,
) -> str:
    if phased is not None:
        for phase_name, fields in phased.phase_missing.items():
            if field in fields:
                return phase_name
        for phase_name, fields in phased.phase_questions.items():
            if field in fields:
                return phase_name
    for phase, fields in nav_config.phase_order:
        if field in fields:
            return phase.value
    return "parameter_gathering"


def _requirement_class_for_field(
    field: str,
    *,
    selection_fields: frozenset[str],
    lookup_fields: frozenset[str],
) -> str:
    if field in selection_fields:
        return "branch_decision"
    if field in lookup_fields:
        return "table_lookup"
    return "user_input"


def _dependency_requirement_id(
    field: str,
    requirements: dict[str, PlanRequirement],
    *,
    lookup_fields: frozenset[str],
) -> str:
    canonical = canonical_parameter_key(field)
    lookup_id = lookup_requirement_id(canonical)
    if lookup_id in requirements:
        return lookup_id
    if canonical == "outside_diameter" and _DIAMETER_RESOLUTION_ID in requirements:
        return _DIAMETER_RESOLUTION_ID
    user_id = requirement_id(canonical)
    if user_id in requirements:
        return user_id
    if canonical in lookup_fields:
        return lookup_id
    return user_id


def _lookup_keys_for_node(store: GraphStore, lookup_node_id: str) -> list[str]:
    keys: list[str] = []
    for edge in store.outgoing(lookup_node_id):
        if edge.edge_type != "requires_parameter":
            continue
        field = _param_field(store, edge.to_id)
        if field and field not in keys:
            keys.append(field)
    return keys


def _returns_parameters(store: GraphStore, lookup_node_id: str) -> list[str]:
    fields: list[str] = []
    for edge in store.outgoing(lookup_node_id):
        if edge.edge_type != "returns_parameter":
            continue
        field = _param_field(store, edge.to_id)
        if field and field not in fields:
            fields.append(field)
    return fields


def _equation_output_fields(store: GraphStore, equation_node_id: str) -> list[str]:
    fields: list[str] = []
    for edge in store.outgoing(equation_node_id):
        if edge.edge_type != "calculates_parameter":
            continue
        field = _param_field(store, edge.to_id)
        if field and field not in fields:
            fields.append(field)
    return fields


def _equation_input_fields(store: GraphStore, equation_node_id: str) -> list[str]:
    fields: list[str] = []
    for edge in store.outgoing(equation_node_id):
        if edge.edge_type != "requires_parameter":
            continue
        field = _param_field(store, edge.to_id)
        if field and field not in fields:
            fields.append(field)
    return fields


def _equation_nodes_for_param(store: GraphStore, param_node_id: str) -> list[str]:
    nodes: list[str] = []
    for edge in store.incoming(param_node_id):
        if edge.edge_type != "calculates_parameter":
            continue
        equation_id = edge.from_id
        node = store.get_node(equation_id)
        if node is not None and node.node_type == "equation" and equation_id not in nodes:
            nodes.append(equation_id)
    return nodes


def _select_equation_for_parameter(
    store: GraphStore,
    param_node_id: str,
    inputs: dict[str, Any],
    *,
    execution_order: frozenset[str],
) -> str | None:
    from engine.graph.assumption_checker import applicability_expansion_satisfied

    candidates: list[str] = []
    for edge in store.incoming(param_node_id):
        if edge.edge_type != "calculates_parameter":
            continue
        equation_id = edge.from_id
        node = store.get_node(equation_id)
        if node is None or node.node_type != "equation":
            continue
        metadata = node.metadata if isinstance(node.metadata, dict) else {}
        if not applicability_expansion_satisfied(metadata, inputs):
            continue
        candidates.append(equation_id)
    if not candidates:
        return None

    in_order = [eq_id for eq_id in candidates if eq_id in execution_order]
    if in_order:
        candidates = in_order

    with_applicability = [
        eq_id
        for eq_id in candidates
        if (store.get_node(eq_id).metadata or {}).get("applicability", {}).get("applies_when")
    ]
    if with_applicability:
        return sorted(with_applicability)[0]
    return sorted(candidates)[0]


def _equations_on_target_path(
    store: GraphStore,
    target_field: str,
    inputs: dict[str, Any],
    *,
    execution_order: list[str],
) -> list[str]:
    """Backward walk from workflow target parameter to required equation nodes."""
    target_param = param_node_id_for_input(target_field)
    order_set = frozenset(execution_order)
    needed_equations: list[str] = []
    seen_equations: set[str] = set()
    queue = [target_param]
    visited_params: set[str] = set()

    while queue:
        param_id = queue.pop(0)
        if param_id in visited_params:
            continue
        visited_params.add(param_id)

        equation_id = _select_equation_for_parameter(
            store,
            param_id,
            inputs,
            execution_order=order_set,
        )
        if equation_id is None or equation_id in seen_equations:
            continue
        seen_equations.add(equation_id)
        needed_equations.append(equation_id)

        for edge in store.outgoing(equation_id):
            if edge.edge_type != "requires_parameter":
                continue
            if edge.to_id not in visited_params:
                queue.append(edge.to_id)

    return needed_equations


def _table_targets_for_parameter(
    store: GraphStore,
    param_node_id: str,
) -> list[str]:
    tables: list[str] = []
    for edge in store.outgoing(param_node_id):
        if edge.edge_type not in {"used_by", "introduced_by"}:
            continue
        target = store.get_node(edge.to_id)
        if target is not None and target.node_type == "table":
            tables.append(edge.to_id)

    meta = load_parameter_node_metadata(param_node_id)
    if isinstance(meta, dict):
        for edge in meta.get("edges") or []:
            if not isinstance(edge, dict):
                continue
            if str(edge.get("type") or "") != "used_by":
                continue
            target_id = str(edge.get("target") or "").strip()
            if not target_id:
                continue
            target = store.get_node(target_id)
            if target is not None and target.node_type == "table":
                tables.append(target_id)
            elif target_id not in tables:
                tables.append(target_id)
    return tables


def _shared_dimension_table(
    store: GraphStore,
    *param_node_ids: str,
) -> str | None:
    tables: list[str] = []
    for param_id in param_node_ids:
        tables.extend(_table_targets_for_parameter(store, param_id))
    if not tables:
        return None
    first = tables[0]
    if all(table == first for table in tables):
        return first
    return first


def _activation_from_parameter_node(
    store: GraphStore,
    param_node_id: str | None,
) -> ActivationCondition | None:
    """Resolve authored parameter applicability as a requirement activation condition."""
    if not param_node_id:
        return None
    return _branch_activation_from_node(store, param_node_id, selection_fields=None)


def _branch_activation_from_node(
    store: GraphStore,
    node_id: str,
    selection_fields: frozenset[str] | None,
) -> ActivationCondition | None:
    node = store.get_node(node_id)
    if node is None:
        return None
    applicability = node.metadata.get("applicability") or {}
    if not isinstance(applicability, dict):
        return None
    for item in applicability.get("applies_when") or []:
        if not isinstance(item, dict):
            continue
        field = _param_to_field(str(item.get("parameter") or ""))
        if selection_fields is not None and field not in selection_fields:
            continue
        operator = str(item.get("operator") or "equals")
        if operator not in {"equals", "not_equals", "in"}:
            continue
        value = item.get("value")
        if value is None:
            continue
        return ActivationCondition(field=field, operator=operator, value=value)
    return None


def _collect_path_activation(
    store: GraphStore,
    execution_order: list[str],
    selection_fields: frozenset[str],
) -> ActivationCondition | None:
    for node_id in execution_order:
        condition = _branch_activation_from_node(store, node_id, selection_fields)
        if condition is not None:
            return condition
    return None


def _emit_user_requirement(
    requirements: dict[str, PlanRequirement],
    *,
    field: str,
    phase: str,
    root_goal_id: str,
    selection_fields: frozenset[str],
    lookup_fields: frozenset[str],
    required_by: list[str] | None = None,
) -> None:
    req_id = requirement_id(field)
    if req_id in requirements:
        return
    req_class = _requirement_class_for_field(
        field,
        selection_fields=selection_fields,
        lookup_fields=lookup_fields,
    )
    if req_class == "table_lookup":
        return
    requirements[req_id] = PlanRequirement(
        id=req_id,
        field=field,
        parameter_node_id=param_node_id_for_input(field),
        requirement_class=req_class,
        status="missing",
        phase=phase,
        required_by=list(required_by or [root_goal_id]),
        depends_on=[],
        question_spec=build_question_spec(
            field,
            priority_override=0 if phase in _GATE_PHASES else None,
            ask_policy="ask_later" if phase == _LATE_INPUT_PHASE else "ask_now",
        ),
        resolution={"method": "user_input", "output_field": field},
    )


def _emit_lookup_requirement(
    requirements: dict[str, PlanRequirement],
    *,
    field: str,
    lookup_node_id: str,
    depends_on: list[str],
    root_goal_id: str,
    resolution: dict[str, Any],
) -> str:
    req_id = lookup_requirement_id(field)
    if req_id in requirements:
        return req_id
    requirements[req_id] = PlanRequirement(
        id=req_id,
        field=field,
        parameter_node_id=param_node_id_for_input(field),
        requirement_class="table_lookup",
        status="blocked",
        phase=_COEFFICIENT_PHASE,
        required_by=[root_goal_id],
        depends_on=depends_on,
        resolution=resolution,
    )
    return req_id


def _emit_equation_requirement(
    requirements: dict[str, PlanRequirement],
    *,
    field: str,
    equation_node_id: str,
    depends_on: list[str],
    root_goal_id: str,
    target_field: str | None = None,
) -> str:
    req_id = equation_requirement_id(field, requirements, target_field=target_field)
    if req_id in requirements:
        return req_id
    requirements[req_id] = PlanRequirement(
        id=req_id,
        field=field,
        parameter_node_id=param_node_id_for_input(field),
        requirement_class="equation_result",
        status="blocked",
        phase=_EQUATION_PHASE,
        required_by=[root_goal_id],
        depends_on=depends_on,
        resolution={
            "method": "equation",
            "source_node_id": equation_node_id,
            "output_field": field,
        },
    )
    return req_id


def _emit_report_requirement(
    requirements: dict[str, PlanRequirement],
    *,
    root_goal_id: str,
    depends_on: list[str],
) -> None:
    if "REQ-calculation_report" in requirements:
        return
    requirements["REQ-calculation_report"] = PlanRequirement(
        id="REQ-calculation_report",
        field="calculation_report",
        parameter_node_id=None,
        requirement_class="report_output",
        status="blocked",
        phase=_REPORT_PHASE,
        required_by=[root_goal_id],
        depends_on=depends_on,
        resolution={"method": "report", "output_field": "calculation_report"},
        title="Calculation Report",
    )


def _maybe_emit_diameter_resolution(
    requirements: dict[str, PlanRequirement],
    *,
    store: GraphStore,
    root_goal_id: str,
    planning_fields: set[str],
) -> None:
    od_field = "outside_diameter"
    nps_field = "nominal_pipe_size"
    if od_field not in planning_fields and nps_field not in planning_fields:
        return

    od_param = param_node_id_for_input(od_field)
    nps_param = param_node_id_for_input(nps_field)
    table_id = _shared_dimension_table(store, od_param, nps_param)
    if table_id is None:
        return

    if _DIAMETER_RESOLUTION_ID in requirements:
        return

    requirements.pop(requirement_id(od_field), None)
    requirements[_DIAMETER_RESOLUTION_ID] = PlanRequirement(
        id=_DIAMETER_RESOLUTION_ID,
        field=od_field,
        parameter_node_id=od_param,
        requirement_class="user_input",
        status="missing",
        phase="parameter_gathering",
        required_by=[root_goal_id],
        depends_on=[],
        alternatives=[
            RequirementAlternative(
                id=_ALT_DIRECT_OD,
                label="Provide outside diameter directly",
                fields=[od_field],
                resolves=od_field,
                method="direct_input",
            ),
            RequirementAlternative(
                id=_ALT_NPS_LOOKUP,
                label="Provide NPS and look up outside diameter",
                fields=[nps_field],
                resolves=od_field,
                method="lookup",
            ),
        ],
        question_spec=build_question_spec(
            "diameter_input_mode",
            label_override="Pipe diameter",
            expected_value_class_override="pipe_size",
            priority_override=2,
        ),
    )

    if nps_field in planning_fields:
        _emit_user_requirement(
            requirements,
            field=nps_field,
            phase="parameter_gathering",
            root_goal_id=_DIAMETER_RESOLUTION_ID,
            selection_fields=frozenset(),
            lookup_fields=frozenset(),
            required_by=[_DIAMETER_RESOLUTION_ID],
        )
        nps_req = requirements.get(requirement_id(nps_field))
        if nps_req is not None:
            nps_req.question_spec = build_question_spec(nps_field, ask_policy="ask_if_needed")
            nps_req.resolution = {
                "method": "user_input",
                "output_field": nps_field,
                "role": "lookup_key",
            }

    if _OUTSIDE_DIAMETER_LOOKUP_ID not in requirements:
        nps_dep = requirement_id(nps_field) if requirement_id(nps_field) in requirements else []
        requirements[_OUTSIDE_DIAMETER_LOOKUP_ID] = PlanRequirement(
            id=_OUTSIDE_DIAMETER_LOOKUP_ID,
            field=od_field,
            parameter_node_id=od_param,
            requirement_class="table_lookup",
            status="blocked",
            phase="parameter_gathering",
            required_by=[_DIAMETER_RESOLUTION_ID],
            depends_on=[requirement_id(nps_field)] if requirement_id(nps_field) in requirements else [],
            resolution={
                "method": "lookup",
                "source_node_id": table_id,
                "output_field": od_field,
                "role": "lookup_output",
            },
        )


def _workflow_has_report(reader: StandardsReader, workflow_id: str) -> bool:
    from engine.planner.workflow_goal_metadata import _workflow_node_metadata

    metadata = _workflow_node_metadata(reader, workflow_id)
    report = metadata.get("report")
    return isinstance(report, dict) and bool(report.get("report_type"))


def _make_planning_fact(field: str, value: Any, *, task_id: str = "planning") -> Any:
    from engine.state.fact_migration import fact_from_engineering_input
    from models.input import EngineeringInput, InputSource, InputStatus

    return fact_from_engineering_input(
        EngineeringInput(
            input_id=field,
            value=value,
            unit="dimensionless",
            source=InputSource.SYSTEM,
            status=InputStatus.CONFIRMED,
        ),
        task_id=task_id,
    )


def synthesize_planning_facts(
    reader: StandardsReader,
    workflow_id: str,
    existing_inputs: dict[str, Any],
    *,
    task_id: str = "planning",
) -> dict[str, Any]:
    """Provisional gate/path values for discovering the full active-path requirement graph."""
    from engine.graph.expansion_policy import collect_workflow_expansion_fields, workflow_expansion_gate_ready
    from engine.graph.graph_engine import normalize_root_id
    from engine.graph.node_interaction import collect_root_interactions
    from engine.planner.planner_traversal import _default_branch_value

    slug = normalize_root_id(workflow_id)
    store = _graph_store(reader)
    if store is None:
        return dict(existing_inputs)

    augmented = dict(existing_inputs)
    if not workflow_expansion_gate_ready(store, slug, augmented):
        for field in collect_workflow_expansion_fields(store, slug):
            if field_value(field, augmented) is not None:
                continue
            default = _default_branch_value(field)
            if default is not None:
                augmented[field] = _make_planning_fact(field, default, task_id=task_id)

    for spec in collect_root_interactions(reader, slug):
        variable = str(spec.variable or "").strip()
        if not variable or field_value(variable, augmented) is not None:
            continue
        if spec.mode == "decision" and spec.options:
            augmented[variable] = _make_planning_fact(variable, spec.options[0], task_id=task_id)
            continue
        default = spec.default
        if default is not None:
            augmented[variable] = _make_planning_fact(variable, default, task_id=task_id)

    return augmented


def _preview_too_shallow(preview: Any | None) -> bool:
    order = list(getattr(preview, "execution_order", ()) or [])
    return len(order) < 5


def _required_outputs(
    requirements: dict[str, PlanRequirement],
    *,
    target_field: str,
    has_report: bool,
) -> list[str]:
    outputs: list[str] = []
    for req in requirements.values():
        if req.requirement_class == "equation_result" and req.field:
            outputs.append(req.field)
    if target_field and target_field not in outputs:
        outputs.append(target_field)
    if has_report and "calculation_report" not in outputs:
        outputs.append("calculation_report")
    return outputs


def build_graph_requirements(
    *,
    reader: StandardsReader,
    workflow_id: str,
    root_goal_id: str,
    preview: Any | None,
    phased: PhasedNavigation | None = None,
    missing_inputs: list[str] | None = None,
    target_field: str | None = None,
    planning_inputs: dict[str, Any] | None = None,
) -> dict[str, PlanRequirement]:
    store = _graph_store(reader)
    if store is None:
        return {}

    nav_config = load_workflow_navigation(reader, workflow_id)
    selection_fields = selection_fields_for_workflow(reader, workflow_id)
    lookup_fields = lookup_fields_for_workflow(reader, workflow_id)
    execution_order = list(getattr(preview, "execution_order", ()) or [])
    applicability_inputs = dict(planning_inputs or {})
    planning_pairs = _collect_planning_fields(
        nav_config=nav_config,
        phased=phased,
        missing_inputs=missing_inputs,
    )
    planning_fields = {field for field, _ in planning_pairs}

    requirements: dict[str, PlanRequirement] = {}
    for field, phase in planning_pairs:
        _emit_user_requirement(
            requirements,
            field=field,
            phase=phase,
            root_goal_id=root_goal_id,
            selection_fields=selection_fields,
            lookup_fields=lookup_fields,
        )

    for node_id in execution_order:
        node = store.get_node(node_id)
        if node is None:
            continue
        if node.node_type == "lookup":
            for field in _returns_parameters(store, node_id):
                deps = [
                    _dependency_requirement_id(
                        key_field,
                        requirements,
                        lookup_fields=lookup_fields,
                    )
                    for key_field in _lookup_keys_for_node(store, node_id)
                ]
                resolution = lookup_resolution_for_parameter(store, param_node_id_for_input(field))
                if resolution is None:
                    resolution = {
                        "method": "lookup",
                        "source_node_id": node_id,
                        "output_field": field,
                    }
                elif resolution.get("method") == "table_lookup":
                    resolution = {
                        "method": "lookup",
                        "source_node_id": node_id,
                        "output_field": field,
                        **{k: v for k, v in resolution.items() if k not in {"method"}},
                    }
                _emit_lookup_requirement(
                    requirements,
                    field=field,
                    lookup_node_id=node_id,
                    depends_on=deps,
                    root_goal_id=root_goal_id,
                    resolution=resolution,
                )
                requirements.pop(requirement_id(field), None)

    for node_id in execution_order:
        node = store.get_node(node_id)
        if node is None or node.node_type != "parameter":
            continue
        field = _param_field(store, node_id)
        if not field:
            continue
        resolution = parameter_resolution_for_parameter(store, node_id)
        if isinstance(resolution, dict):
            method = str(resolution.get("method") or "")
            if method == "material_catalog":
                keys = [
                    canonical_parameter_key(str(key))
                    for key in (resolution.get("keys") or [])
                    if str(key).strip()
                ]
                deps = [
                    _dependency_requirement_id(key, requirements, lookup_fields=lookup_fields)
                    for key in keys
                ]
                _emit_lookup_requirement(
                    requirements,
                    field=field,
                    lookup_node_id="MAT-catalog",
                    depends_on=deps,
                    root_goal_id=root_goal_id,
                    resolution={
                        "method": "material_catalog",
                        "output_field": field,
                        "keys": keys,
                    },
                )
                requirements.pop(requirement_id(field), None)
            elif method == "table_lookup" and lookup_requirement_id(field) not in requirements:
                keys = [
                    canonical_parameter_key(str(key))
                    for key in (resolution.get("keys") or [])
                    if str(key).strip()
                ]
                deps = [
                    _dependency_requirement_id(key, requirements, lookup_fields=lookup_fields)
                    for key in keys
                ]
                table_id = str(resolution.get("table_id") or "")
                _emit_lookup_requirement(
                    requirements,
                    field=field,
                    lookup_node_id=table_id or node_id,
                    depends_on=deps,
                    root_goal_id=root_goal_id,
                    resolution={
                        "method": "lookup",
                        "source_node_id": table_id or node_id,
                        "output_field": field,
                        "keys": keys,
                    },
                )
                requirements.pop(requirement_id(field), None)

    equation_node_ids: list[str] = []
    if target_field:
        equation_node_ids = _equations_on_target_path(
            store,
            target_field,
            applicability_inputs,
            execution_order=execution_order,
        )

    for equation_id in equation_node_ids:
        for field in _equation_output_fields(store, equation_id):
            input_fields = _equation_input_fields(store, equation_id)
            deps = [
                _dependency_requirement_id(input_field, requirements, lookup_fields=lookup_fields)
                for input_field in input_fields
            ]
            _emit_equation_requirement(
                requirements,
                field=field,
                equation_node_id=equation_id,
                depends_on=deps,
                root_goal_id=root_goal_id,
                target_field=target_field,
            )

    _maybe_emit_diameter_resolution(
        requirements,
        store=store,
        root_goal_id=root_goal_id,
        planning_fields=planning_fields,
    )

    path_activation = _collect_path_activation(store, execution_order, selection_fields)
    for req in requirements.values():
        if req.phase in _GATE_PHASES:
            continue
        param_activation = _activation_from_parameter_node(store, req.parameter_node_id)
        if param_activation is not None:
            req.activation_condition = param_activation
        elif path_activation is not None:
            req.activation_condition = path_activation

    if _workflow_has_report(reader, workflow_id):
        equation_req_ids = [
            req.id
            for req in requirements.values()
            if req.requirement_class == "equation_result"
        ]
        report_dep = equation_req_ids[-1:] if equation_req_ids else []
        _emit_report_requirement(
            requirements,
            root_goal_id=root_goal_id,
            depends_on=report_dep,
        )

    return requirements


def _diameter_mode(existing_inputs: dict) -> str | None:
    from engine.graph.resolution_branches import active_resolution_branch_id

    branch = active_resolution_branch_id("outside_diameter", existing_inputs)
    if branch in {"direct_od", "nps_lookup"}:
        return str(branch)
    for mode_field in ("d_input_mode", "diameter_input_mode"):
        mode = field_value(mode_field, existing_inputs)
        if mode in {"direct_od", "nps_lookup", "direct_id"}:
            return str(mode)
    from engine.reference.parameter_keys import parameter_is_ready

    if parameter_is_ready(existing_inputs, "outside_diameter"):
        return "direct_od"
    if parameter_is_ready(existing_inputs, "nominal_pipe_size"):
        return "nps_lookup"
    if parameter_is_ready(existing_inputs, "inside_diameter"):
        return "direct_id"
    return None


def apply_alternative_resolution_statuses(
    requirements: dict[str, PlanRequirement],
    *,
    existing_inputs: dict,
) -> None:
    from engine.reference.parameter_keys import parameter_is_ready

    diameter_mode = _diameter_mode(existing_inputs)
    diameter = requirements.get(_DIAMETER_RESOLUTION_ID)
    if diameter is None:
        return

    od_lookup = requirements.get(_OUTSIDE_DIAMETER_LOOKUP_ID)
    nps_req = requirements.get(requirement_id("nominal_pipe_size"))

    if diameter_mode == "direct_od" and parameter_is_ready(existing_inputs, "outside_diameter"):
        diameter.status = "resolved"
    elif diameter_mode == "direct_id" and parameter_is_ready(existing_inputs, "inside_diameter"):
        diameter.status = "resolved"
    elif diameter_mode == "nps_lookup":
        if parameter_is_ready(existing_inputs, "outside_diameter"):
            diameter.status = "resolved"
        else:
            # Branch choice is complete; outside diameter will be lookup-derived.
            diameter.status = "resolved"
    elif diameter.status == "missing":
        pass

    if od_lookup is not None:
        if diameter_mode != "nps_lookup":
            od_lookup.status = "not_applicable"
        elif parameter_is_ready(existing_inputs, "outside_diameter"):
            od_lookup.status = "resolved"
        elif not parameter_is_ready(existing_inputs, "nominal_pipe_size"):
            od_lookup.status = "blocked"
        else:
            od_lookup.status = "ready"

    if nps_req is not None:
        if diameter_mode == "direct_od":
            nps_req.status = "not_applicable"
        elif parameter_is_ready(existing_inputs, "nominal_pipe_size"):
            nps_req.status = "resolved"
        elif diameter_mode == "nps_lookup":
            nps_req.status = "missing"
        else:
            nps_req.status = "not_applicable"


def required_outputs_for_plan(
    requirements: dict[str, PlanRequirement],
    *,
    target_field: str,
    has_report: bool,
) -> list[str]:
    return _required_outputs(requirements, target_field=target_field, has_report=has_report)
