"""Tests for pressure design case path decision and branch applicability."""

from __future__ import annotations

from pathlib import Path

from engine.graph.assumption_checker import AssumptionEvaluation, applicability_expansion_status
from engine.graph.graph_engine import GraphEngine
from engine.graph.lazy_expander import expand_workflow
from engine.graph.path_decision import pending_path_branch_nodes, resolve_path_decision
from engine.graph.workflow_navigation import load_workflow_navigation
from engine.planner.graph_navigation import build_graph_navigation_from_plan
from engine.reference.parameter_keys import canonical_parameter_key
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from engine.state.task_facts import active_facts, store_user_fact
from models.input import InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.helpers.facts import facts_from_inputs, legacy_input


def _store(project_root: Path):
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    assert micro is not None
    resolved = engine._resolve_micro_root("pipe_wall_thickness_design", reader)
    return micro.store, reader, resolved


def test_unresolved_pressure_design_case_leaves_both_branches_pending(project_root: Path) -> None:
    store, reader, root = _store(project_root)
    inputs = facts_from_inputs(
        {"straight_pipe_section": straight_section_assumption()},
        task_id="pending-branches",
    )
    expansion = expand_workflow(store, root, inputs, lazy=False)
    assert "304.1.2-a" not in expansion.active_nodes
    assert "304.1.3" not in expansion.active_nodes
    for node_id in ("304.1.2-a", "304.1.3"):
        node = store.get_node(node_id)
        assert node is not None
        assert applicability_expansion_status(node.metadata, inputs) == "pending"
    pending = pending_path_branch_nodes(store, expansion.active_nodes + ["304.1.2-a", "304.1.3"], inputs)
    pending_ids = {item["node_id"] for item in pending}
    assert pending_ids == {"304.1.2-a", "304.1.3"}
    assert resolve_path_decision(store, list(expansion.active_nodes), inputs) is None


def test_internal_pressure_activates_304_1_2_excludes_304_1_3(project_root: Path) -> None:
    store, reader, root = _store(project_root)
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_design_case": internal_pressure_assumption(),
        },
        task_id="internal-branch",
    )
    expansion = expand_workflow(store, root, inputs, lazy=False)
    assert "304.1.2-a" in expansion.active_nodes
    assert "304.1.3" not in expansion.active_nodes
    decision = resolve_path_decision(store, list(expansion.active_nodes), inputs)
    assert decision is not None
    assert decision["field"] == "pressure_design_case"
    assert decision["selected_node"] == "304.1.2-a"


def test_external_pressure_activates_304_1_3_and_external_pressure_input(project_root: Path) -> None:
    store, reader, root = _store(project_root)
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_design_case": legacy_input(
                "pressure_design_case",
                "external_pressure",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id="external-branch",
    )
    expansion = expand_workflow(store, root, inputs, lazy=False)
    assert "304.1.3" in expansion.active_nodes
    assert "304.1.2-a" not in expansion.active_nodes
    assert "PARAM-external-design-pressure" in expansion.active_nodes


def test_straight_pipe_false_does_not_ask_pressure_design_case(project_root: Path) -> None:
    from engine.graph.assumption_checker import AssumptionEvaluation
    from engine.graph.navigation_phases import build_workflow_phased_navigation
    from engine.graph.workflow_navigation import load_workflow_navigation
    from engine.planner.tools import GraphTools

    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("straight-pipe-block", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    store_user_fact(
        task,
        "straight_pipe_section",
        False,
        unit="dimensionless",
        workflow_id="pipe_wall_thickness_design",
    )
    graph = GraphTools(reader)
    inputs = dict(active_facts(task))
    preview = graph.preview_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs=inputs,
    )
    assumption_eval = graph.evaluate_assumptions(
        "pipe_wall_thickness_design",
        existing_inputs=inputs,
        plan=preview,
    )
    expansion_eval = graph.evaluate_expansion_interactions(
        "pipe_wall_thickness_design",
        existing_inputs=inputs,
        plan=preview,
    )
    assert assumption_eval.is_blocked
    phased = build_workflow_phased_navigation(
        config=load_workflow_navigation(reader, "pipe_wall_thickness_design"),
        assumption_eval=assumption_eval,
        expansion_eval=expansion_eval,
        user_inputs=[],
        execution_eval=AssumptionEvaluation(),
        question_map={},
        existing_inputs=inputs,
    )
    assert phased.current_phase.value == "expansion_assumptions"
    assert "pressure_design_case" not in phased.all_missing


def test_legacy_pressure_loading_alias_resolves_to_pressure_design_case(project_root: Path) -> None:
    assert canonical_parameter_key("pressure_loading") == "pressure_design_case"
    store, reader, root = _store(project_root)
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": legacy_input(
                "pressure_loading",
                "internal_pressure",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id="legacy-alias",
    )
    expansion = expand_workflow(store, root, inputs, lazy=False)
    decision = resolve_path_decision(store, list(expansion.active_nodes), inputs)
    assert decision is not None
    assert decision["field"] == "pressure_design_case"


def test_pressure_design_case_facts_do_not_leak_between_workflows(project_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("scope-test", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "mawp_design"
    store_user_fact(
        task,
        "pressure_design_case",
        "external_pressure",
        unit="dimensionless",
        workflow_id="pipe_wall_thickness_design",
    )
    scoped = active_facts(task)
    assert "pressure_design_case" not in scoped
