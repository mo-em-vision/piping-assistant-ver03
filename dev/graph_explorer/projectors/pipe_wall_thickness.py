"""Pipe wall thickness workflow expansion projector."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.conditions import when_clause_matches
from engine.graph.graph_engine import normalize_root_id, resolve_workflow_node_id
from engine.graph.graph_store import GraphStore
from engine.graph.lazy_expander import (
    _collect_expansion_assumptions,
    expand_workflow,
    expansion_gate_ready,
)
from engine.reference.graph_db import GraphEdgeRecord
from engine.reference.graph_edge_schema import workflow_anchor_target
from engine.reference.node_types import is_ui_parameter, parameter_input_id
from engine.state.task_facts import active_facts
from models.fact import Fact
from models.planning import NavigationPhase
from models.task import Task

from engine.graph.expansion_policy import expansion_projection_hint
from dev.graph_explorer.expansion_types import (
    DEPENDENCY_EDGE_TYPES,
    EXTERNAL_PRESSURE_BRANCH,
    INTERNAL_PRESSURE_BRANCH,
    PIPE_WALL_PHASE_FIELDS,
    PIPE_WALL_TIMELINE_PHASES,
    REFERENCE_EDGE_TYPES,
    WORKFLOW_ROOT,
)
from dev.graph_explorer.projectors.base import (
    ExpansionProjector,
    execution_status_map,
    extract_execution_trace,
    extract_planning_summary,
    extract_task_inputs,
    infer_current_phase,
    infer_phase_missing,
    node_graph_type,
    node_label,
    resolve_workflow_id,
    task_status_label,
    trace_by_node_id,
)


class PipeWallThicknessExpansionProjector(ExpansionProjector):
    """Runtime expansion projection for pipe_wall_thickness_design."""

    def project(self, task: Task, *, requested_task_id: str | None = None) -> dict[str, Any]:
        warnings: list[str] = []
        workflow = resolve_workflow_id(task) or "pipe_wall_thickness_design"
        inputs = active_facts(task)
        planning = extract_planning_summary(task, inputs)
        execution_trace, skipped_trace = extract_execution_trace(task)
        trace_map = trace_by_node_id(execution_trace)
        exec_status = execution_status_map(execution_trace)

        store, root_id, root_record = self._resolve_workflow_store(workflow)
        if store is None or root_record is None:
            warnings.append("Workflow root not found in compiled graph databases.")
            return self._empty_view(task, workflow, planning, warnings, has_graph=False)

        resolved_root = store.resolve_node_id(root_id) or root_id
        anchor = workflow_anchor_target(root_record.metadata)
        anchor_id = store.resolve_node_id(anchor) if isinstance(anchor, str) else ""

        lazy_state = expand_workflow(store, resolved_root, inputs, lazy=True)
        full_state = expand_workflow(store, resolved_root, inputs, lazy=False)

        pressure_value = field_value("pressure_loading", inputs)
        straight_value = field_value("straight_pipe_section", inputs)
        current_phase = str(planning.get("current_phase") or infer_current_phase(inputs))
        phase_missing = planning.get("phase_missing") or infer_phase_missing(inputs, current_phase)

        visible = self._build_visible_set(
            task=task,
            store=store,
            resolved_root=resolved_root,
            anchor_id=anchor_id,
            lazy_nodes=lazy_state.active_nodes,
            full_nodes=full_state.active_nodes,
            skipped_nodes=full_state.skipped_nodes,
            execution_trace=execution_trace,
            inputs=inputs,
            pressure_value=pressure_value,
            straight_value=straight_value,
        )

        full_graph_ids = set(full_state.active_nodes)
        skipped_ids = self._skipped_node_ids(
            full_state.skipped_nodes,
            pressure_value,
            planning.get("path_decision"),
        )
        pending_skipped = {
            str(item.get("node_id")): bool(item.get("pending"))
            for item in full_state.skipped_nodes
            if item.get("node_id")
        }

        nodes: list[dict[str, Any]] = []
        for node_id in sorted(visible | full_graph_ids):
            record, node_store = self.find_node(node_id)
            if record is None and node_id not in visible:
                continue
            is_visible_default = node_id in visible
            classified = self._classify_node(
                node_id=node_id,
                record=record,
                task=task,
                inputs=inputs,
                current_phase=current_phase,
                phase_missing=phase_missing,
                straight_value=straight_value,
                pressure_value=pressure_value,
                skipped_ids=skipped_ids,
                pending_skipped=pending_skipped,
                exec_status=exec_status,
                trace_map=trace_map,
                lazy_nodes=set(lazy_state.active_nodes),
                full_nodes=set(full_state.active_nodes),
                is_visible_default=is_visible_default,
                store=node_store or store,
            )
            if classified["status"] == "hidden" and not is_visible_default:
                classified["visible"] = False
            nodes.append(classified)

        edges = self._build_edges(
            store=store,
            node_ids=set(n["id"] for n in nodes if n.get("visible", True)),
            all_node_ids=set(n["id"] for n in nodes),
            inputs=inputs,
            exec_status=exec_status,
            skipped_ids=skipped_ids,
            pressure_value=pressure_value,
        )

        timeline = build_phase_timeline(task, inputs, current_phase, phase_missing, pressure_value)
        expansion_state = {
            "straight_pipe_section": straight_value,
            "pressure_loading": pressure_value,
            "expansion_gate_ready": expansion_gate_ready(store, resolved_root, inputs),
            "selected_pressure_branch": self._selected_branch(pressure_value),
        }

        return {
            "task_id": task.task_id,
            "workflow": workflow,
            "task_status": task_status_label(task),
            "current_phase": current_phase,
            "phase_missing": phase_missing,
            "inputs": extract_task_inputs(task),
            "expansion_state": expansion_state,
            "nodes": nodes,
            "edges": edges,
            "timeline": timeline,
            "warnings": warnings,
            "debug": {
                "has_task": True,
                "has_compiled_graph": True,
                "has_planning_summary": bool(
                    task.goal_store.goals or task.outputs.get("planning_summary")
                ),
                "has_execution_trace": bool(execution_trace),
                "projector": "pipe_wall_thickness",
                "workflow_root": resolved_root,
                "anchor_id": anchor_id,
                "lazy_node_count": len(lazy_state.active_nodes),
                "full_node_count": len(full_state.active_nodes),
                "skipped_trace_count": len(skipped_trace),
                "requested_task_id": requested_task_id,
            },
        }

    def _resolve_workflow_store(
        self,
        workflow: str,
    ) -> tuple[GraphStore | None, str, Any]:
        slug = normalize_root_id(workflow)
        resolved = resolve_workflow_node_id(slug)
        for candidate in (resolved, WORKFLOW_ROOT, "B313-WF-PIPE-WALL-THICKNESS", slug):
            record, store = self.find_node(candidate)
            if record is not None and store is not None:
                return store, candidate, record
        for store in self.adapter._stores.values():  # noqa: SLF001
            for candidate in (resolved, WORKFLOW_ROOT):
                if store.get_node(candidate) is not None:
                    return store, candidate, store.get_node(candidate)
        return None, resolved, None

    def _build_visible_set(
        self,
        *,
        task: Task,
        store: GraphStore,
        resolved_root: str,
        anchor_id: str,
        lazy_nodes: list[str],
        full_nodes: list[str],
        skipped_nodes: list[dict[str, Any]],
        execution_trace: list[dict[str, Any]],
        inputs: dict[str, Fact],
        pressure_value: Any,
        straight_value: Any,
    ) -> set[str]:
        visible: set[str] = set()
        visible.add(resolved_root)
        if anchor_id:
            visible.add(anchor_id)
        visible.update(task.active_nodes)
        visible.update(lazy_nodes)

        for item in execution_trace:
            node_id = str(item.get("node_id", ""))
            if node_id:
                visible.add(node_id)

        for skip in skipped_nodes:
            node_id = str(skip.get("node_id", ""))
            if node_id:
                visible.add(node_id)

        for field_name in _collect_expansion_assumptions(store, resolved_root):
            for node_id in self._nodes_for_input_field(store, field_name):
                visible.add(node_id)

        gate_open = expansion_gate_ready(store, resolved_root, inputs)
        if pressure_value is None:
            visible.add(INTERNAL_PRESSURE_BRANCH)
            visible.add(EXTERNAL_PRESSURE_BRANCH)
        elif pressure_value == "internal_pressure":
            visible.add(INTERNAL_PRESSURE_BRANCH)
            visible.add(EXTERNAL_PRESSURE_BRANCH)
        elif pressure_value == "external_pressure":
            visible.add(INTERNAL_PRESSURE_BRANCH)
            visible.add(EXTERNAL_PRESSURE_BRANCH)

        seed_nodes = set(task.active_nodes) | set(full_nodes if gate_open else lazy_nodes)
        for node_id in list(seed_nodes):
            record = store.get_node(node_id)
            if record is None:
                continue
            node_type = record.node_type or ""
            if node_type not in {"calculation", "lookup", "equation", "paragraph", "definition"}:
                continue
            for edge in store.incoming(node_id, edge_types=DEPENDENCY_EDGE_TYPES):
                visible.add(edge.from_id)
            for edge in store.outgoing(node_id, edge_types=DEPENDENCY_EDGE_TYPES):
                visible.add(edge.to_id)

        return {self.resolve_id(store, node_id) for node_id in visible if node_id}

    def _nodes_for_input_field(self, store: GraphStore, field_name: str) -> list[str]:
        matches: list[str] = []
        for node in store.list_nodes(node_type="parameter"):
            if parameter_input_id(node.metadata) == field_name:
                matches.append(node.node_id)
            elif is_ui_parameter(node.metadata, node.node_type) and node.metadata.get("input_id") == field_name:
                matches.append(node.node_id)
        return matches

    def _skipped_node_ids(
        self,
        skipped_nodes: list[dict[str, Any]],
        pressure_value: Any,
        path_decision: Any,
    ) -> dict[str, str]:
        reasons: dict[str, str] = {}
        for item in skipped_nodes:
            node_id = str(item.get("node_id", ""))
            if node_id:
                reasons[node_id] = str(item.get("reason") or "conditional dependency not active")

        if pressure_value == "internal_pressure":
            reasons.setdefault(EXTERNAL_PRESSURE_BRANCH, "pressure_loading != external_pressure")
        elif pressure_value == "external_pressure":
            reasons.setdefault(INTERNAL_PRESSURE_BRANCH, "pressure_loading != internal_pressure")

        if isinstance(path_decision, dict):
            selected = path_decision.get("selected_node")
            if isinstance(selected, str):
                if pressure_value == "internal_pressure" and selected == INTERNAL_PRESSURE_BRANCH:
                    reasons.setdefault(EXTERNAL_PRESSURE_BRANCH, "path_decision selected internal branch")
                if pressure_value == "external_pressure" and selected == EXTERNAL_PRESSURE_BRANCH:
                    reasons.setdefault(INTERNAL_PRESSURE_BRANCH, "path_decision selected external branch")

        return reasons

    def _classify_node(
        self,
        *,
        node_id: str,
        record: Any,
        task: Task,
        inputs: dict[str, Fact],
        current_phase: str,
        phase_missing: dict[str, list[str]],
        straight_value: Any,
        pressure_value: Any,
        skipped_ids: dict[str, str],
        pending_skipped: dict[str, bool],
        exec_status: dict[str, str],
        trace_map: dict[str, dict[str, Any]],
        lazy_nodes: set[str],
        full_nodes: set[str],
        is_visible_default: bool,
        store: GraphStore,
    ) -> dict[str, Any]:
        node_type = node_graph_type(record, node_id)
        label = node_label(record, node_id)
        missing_inputs = find_missing_inputs_for_node(
            node_id,
            task,
            store,
            phase_missing,
            current_phase,
            inputs,
        )

        status = "unknown"
        reason = "Visible in workflow expansion projection"
        source = "compiled_graph"
        phase = current_phase
        expansion_hint = (
            expansion_projection_hint(store, node_id, inputs) if record is not None else None
        )

        if node_id in exec_status:
            status = exec_status[node_id]
            reason = f"Execution trace status: {exec_status[node_id]}"
            source = "execution_trace"
        elif expansion_hint:
            status = str(expansion_hint["status"])
            reason = str(expansion_hint["reason"])
            field_name = str(expansion_hint.get("field") or "")
            if field_name in (phase_missing.get(NavigationPhase.EXPANSION_ASSUMPTIONS.value) or []):
                phase = NavigationPhase.EXPANSION_ASSUMPTIONS.value
            elif expansion_hint.get("status") == "blocked":
                phase = NavigationPhase.EXPANSION_ASSUMPTIONS.value
            source = "compiled_graph"
        elif node_id in skipped_ids:
            if pending_skipped.get(node_id):
                status = "pending_condition"
            else:
                status = "skipped"
            reason = skipped_ids[node_id]
            source = "compiled_graph"
        elif node_id in {INTERNAL_PRESSURE_BRANCH, EXTERNAL_PRESSURE_BRANCH}:
            if pressure_value is None:
                status = "pending_condition"
                reason = "Branch visibility preview until pressure_loading is selected"
                phase = NavigationPhase.PATH_DECISIONS.value
            elif node_id in skipped_ids:
                status = "skipped"
                reason = skipped_ids[node_id]
            elif node_id == INTERNAL_PRESSURE_BRANCH and pressure_value == "internal_pressure":
                status = "awaiting_input" if missing_inputs else "active"
                reason = "Internal pressure calculation branch selected"
                phase = NavigationPhase.PARAMETER_GATHERING.value
            elif node_id == EXTERNAL_PRESSURE_BRANCH and pressure_value == "external_pressure":
                status = "awaiting_input" if missing_inputs else "active"
                reason = "External pressure calculation branch selected"
                phase = NavigationPhase.PARAMETER_GATHERING.value
        elif node_id in task.active_nodes:
            if missing_inputs:
                status = "awaiting_input" if current_phase in {
                    NavigationPhase.PARAMETER_GATHERING.value,
                    NavigationPhase.COEFFICIENT_RESOLUTION.value,
                    NavigationPhase.EXECUTION_ASSUMPTIONS.value,
                } else "blocked"
                reason = f"Missing inputs: {', '.join(missing_inputs)}"
            else:
                status = "active"
                reason = "Node is in task.active_nodes"
            source = "task_state"
        elif node_id in lazy_nodes and node_id not in full_nodes:
            status = "preview"
            reason = "Preview node before expansion gate opens"
        elif not is_visible_default:
            status = "hidden"
            reason = "Full compiled graph node (hidden by default)"
        else:
            status = "preview"
            reason = "Supporting dependency on active path"

        trace_item = trace_map.get(node_id)
        provided_outputs: list[str] = []
        if trace_item and isinstance(trace_item.get("outputs"), dict):
            provided_outputs = sorted(str(k) for k in trace_item["outputs"])

        details: dict[str, Any] = {"source": source}
        if record is not None:
            paragraph = record.metadata.get("paragraph") or record.metadata.get("paragraph_number")
            if paragraph:
                details["paragraph"] = str(paragraph)
            title = record.metadata.get("title") or record.metadata.get("display_heading")
            if title:
                details["title"] = str(title)
        if trace_item:
            details["execution"] = {
                "inputs": trace_item.get("inputs"),
                "outputs": trace_item.get("outputs"),
                "warnings": trace_item.get("warnings") or [],
                "errors": trace_item.get("errors") or [],
                "trace_summary": trace_item.get("trace"),
            }

        return {
            "id": node_id,
            "label": label,
            "type": node_type,
            "status": status,
            "visible": is_visible_default and status != "hidden",
            "active": node_id in task.active_nodes,
            "blocked": status in {"blocked", "awaiting_input"} and bool(missing_inputs),
            "skipped": status == "skipped",
            "reason": reason,
            "missing_inputs": missing_inputs,
            "provided_outputs": provided_outputs,
            "required_inputs": missing_inputs,
            "phase": phase,
            "details": details,
        }

    def _build_edges(
        self,
        *,
        store: GraphStore,
        node_ids: set[str],
        all_node_ids: set[str],
        inputs: dict[str, Fact],
        exec_status: dict[str, str],
        skipped_ids: dict[str, str],
        pressure_value: Any,
    ) -> list[dict[str, Any]]:
        edges: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for node_id in all_node_ids:
            resolved = self.resolve_id(store, node_id)
            for edge in list(store.outgoing(resolved)) + list(store.incoming(resolved)):
                if edge.from_id not in all_node_ids or edge.to_id not in all_node_ids:
                    continue
                key = (edge.from_id, edge.to_id, edge.edge_type)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    classify_workflow_edge(
                        edge,
                        inputs=inputs,
                        exec_status=exec_status,
                        skipped_ids=skipped_ids,
                        visible_node_ids=node_ids,
                        pressure_value=pressure_value,
                    )
                )
        return edges

    @staticmethod
    def _selected_branch(pressure_value: Any) -> str | None:
        if pressure_value == "internal_pressure":
            return "internal_pressure"
        if pressure_value == "external_pressure":
            return "external_pressure"
        return None

    def _empty_view(
        self,
        task: Task,
        workflow: str,
        planning: dict[str, Any],
        warnings: list[str],
        *,
        has_graph: bool,
    ) -> dict[str, Any]:
        inputs = active_facts(task)
        execution_trace, _ = extract_execution_trace(task)
        return {
            "task_id": task.task_id,
            "workflow": workflow,
            "task_status": task_status_label(task),
            "current_phase": str(planning.get("current_phase") or infer_current_phase(inputs)),
            "phase_missing": planning.get("phase_missing") or {},
            "inputs": extract_task_inputs(task),
            "expansion_state": {},
            "nodes": [],
            "edges": [],
            "timeline": build_phase_timeline(
                task,
                inputs,
                str(planning.get("current_phase") or infer_current_phase(inputs)),
                planning.get("phase_missing") or {},
                field_value("pressure_loading", inputs),
            ),
            "warnings": warnings,
            "debug": {
                "has_task": True,
                "has_compiled_graph": has_graph,
                "has_planning_summary": bool(
                    task.goal_store.goals or task.outputs.get("planning_summary")
                ),
                "has_execution_trace": bool(execution_trace),
                "projector": "pipe_wall_thickness",
            },
        }


def find_missing_inputs_for_node(
    node_id: str,
    task: Task,
    store: GraphStore,
    phase_missing: dict[str, list[str]],
    current_phase: str,
    inputs: dict[str, Fact],
) -> list[str]:
    """Return current-phase missing inputs relevant to this node."""
    current_missing = list(phase_missing.get(current_phase) or [])
    if not current_missing:
        return []

    node_missing: list[str] = []
    record = store.get_node(node_id)
    if record is None:
        return current_missing if node_id in task.active_nodes else []

    for edge in store.incoming(node_id, edge_types={"requires", "requires_parameter", "uses"}):
        producer = store.get_node(edge.from_id)
        if producer and producer.node_type == "parameter":
            field_name = parameter_input_id(producer.metadata)
            if field_name in current_missing:
                node_missing.append(field_name)

    if node_id in task.active_nodes and not node_missing:
        return current_missing

    return sorted(set(node_missing))


def classify_workflow_edge(
    edge: GraphEdgeRecord,
    *,
    inputs: dict[str, Fact],
    exec_status: dict[str, str],
    skipped_ids: dict[str, str],
    visible_node_ids: set[str],
    pressure_value: Any,
) -> dict[str, Any]:
    when = edge.metadata.get("when") if edge.metadata else None
    condition = ""
    edge_type = "dependency"
    skipped = False
    active = exec_status.get(edge.from_id) == "executed"

    reason = edge.edge_type
    if edge.edge_type in REFERENCE_EDGE_TYPES:
        edge_type = "reference"
        reason = edge.edge_type
    elif when and isinstance(when, dict):
        edge_type = "conditional"
        field_name = when.get("field", "")
        allowed = when.get("in") or []
        condition = f"{field_name} == {allowed[0]}" if len(allowed) == 1 else f"{field_name} in {allowed}"
        matches = when_clause_matches(when, inputs)
        if not matches:
            skipped = True
            edge_type = "skipped"
            if edge.to_id in skipped_ids:
                reason = skipped_ids[edge.to_id]
            elif field_name == "pressure_loading" and pressure_value is None:
                reason = "pressure_loading not selected"
            else:
                reason = f"Condition not satisfied: {condition}"
        else:
            reason = condition
            active = True
    elif edge.to_id in skipped_ids:
        edge_type = "skipped"
        skipped = True
        reason = skipped_ids[edge.to_id]
    elif active:
        edge_type = "active"
        reason = "Source node executed"
    else:
        reason = edge.edge_type

    visible = edge.from_id in visible_node_ids and edge.to_id in visible_node_ids
    if not visible and edge_type == "reference":
        edge_type = "reference"

    return {
        "id": f"{edge.from_id}->{edge.to_id}",
        "source": edge.from_id,
        "target": edge.to_id,
        "type": edge_type,
        "active": active and not skipped,
        "skipped": skipped,
        "reason": reason,
        "condition": condition,
    }


def build_phase_timeline(
    task: Task,
    inputs: dict[str, Fact],
    current_phase: str,
    phase_missing: dict[str, list[str]],
    pressure_value: Any,
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    phase_index = PIPE_WALL_TIMELINE_PHASES.index(current_phase) if current_phase in PIPE_WALL_TIMELINE_PHASES else -1

    for index, phase in enumerate(PIPE_WALL_TIMELINE_PHASES):
        fields = PIPE_WALL_PHASE_FIELDS.get(phase, ())
        items: list[dict[str, Any]] = []
        phase_status = "completed"
        for field_name in fields:
            value = field_value(field_name, inputs)
            item_status = _timeline_item_status(
                field_name=field_name,
                value=value,
                phase=phase,
                current_phase=current_phase,
                phase_index=phase_index,
                index=index,
                phase_missing=phase_missing,
                pressure_value=pressure_value,
            )
            if item_status in {"missing", "current"}:
                phase_status = "current" if item_status == "current" else phase_status
            if item_status == "missing" and phase_status == "completed":
                phase_status = "current"
            items.append(
                {
                    "id": field_name,
                    "status": item_status,
                    "value": value,
                }
            )
        if phase == current_phase:
            phase_status = "current"
        elif index < phase_index:
            phase_status = "completed"
        elif index > phase_index and phase_index >= 0:
            phase_status = "not_reached"

        timeline.append({"phase": phase, "status": phase_status, "items": items})

    corrosion_fields = PIPE_WALL_PHASE_FIELDS.get(NavigationPhase.DEFINITION_EQUATION_COMPLETION.value, ())
    if corrosion_fields:
        items = []
        for field_name in corrosion_fields:
            value = field_value(field_name, inputs)
            item_status = _timeline_item_status(
                field_name=field_name,
                value=value,
                phase=NavigationPhase.DEFINITION_EQUATION_COMPLETION.value,
                current_phase=current_phase,
                phase_index=phase_index,
                index=len(PIPE_WALL_TIMELINE_PHASES),
                phase_missing=phase_missing,
                pressure_value=pressure_value,
            )
            items.append({"id": field_name, "status": item_status, "value": value})
        timeline.append(
            {
                "phase": NavigationPhase.EXECUTION_ASSUMPTIONS.value,
                "status": "current" if current_phase == NavigationPhase.EXECUTION_ASSUMPTIONS.value else "not_reached",
                "items": items,
            }
        )

    return timeline


def _timeline_item_status(
    *,
    field_name: str,
    value: Any,
    phase: str,
    current_phase: str,
    phase_index: int,
    index: int,
    phase_missing: dict[str, list[str]],
    pressure_value: Any,
) -> str:
    if field_name == "straight_pipe_section" and value is False:
        return "blocked"
    if value is not None:
        return "confirmed"
    if phase == current_phase or field_name in (phase_missing.get(current_phase) or []):
        return "current" if field_name in (phase_missing.get(current_phase) or []) else "missing"
    if index > phase_index and phase_index >= 0:
        return "not_reached"
    if field_name == "pressure_loading" and pressure_value is None and phase == NavigationPhase.PATH_DECISIONS.value:
        return "missing"
    return "missing"
