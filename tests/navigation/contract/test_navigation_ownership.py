"""Navigation ownership architecture-contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.graph_engine import GraphEngine, legacy_graph_traversal_enabled
from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.tools import GraphTools
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.input import InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.graph.conftest import PIPE_WALL_ROOT
from tests.helpers.facts import facts_from_inputs, legacy_input
from tests.navigation.fixtures.synthetic_nav_pack import (
    WORKFLOW_ROOT,
    build_synthetic_nav_pack,
    synthetic_gate_open_facts,
)
from tests.navigation.helpers.contracts import (
    api_current_ask_parameter,
    api_submittable_projection,
    assert_graph_planner_gatherable_parity,
    graph_active_direct_inputs,
    planner_active_direct_inputs,
    planner_next_field,
    planner_submittable_projection,
)


def _pipe_wall_gates_open_task(project_root: Path):
    from engine.reference.standards_reader import StandardsReader

    manager = TaskStateManager()
    task = manager.create_task("nav-contract-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id=PIPE_WALL_ROOT,
            ),
        )
    task = manager.get_task(task.task_id)
    facts = dict(task.fact_store.active_facts())
    return manager, task, reader, facts


def _synthetic_task(reader, facts):
    manager = TaskStateManager()
    task = manager.create_task("nav-contract-alpha", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = WORKFLOW_ROOT
    task.outputs["selected_root"] = WORKFLOW_ROOT
    for fact in facts.values():
        manager.store_fact(task.task_id, fact)
    task = manager.get_task(task.task_id)
    return manager, task


def test_graph_and_planner_agree_on_active_direct_inputs(project_root: Path) -> None:
    _, task, reader, facts = _pipe_wall_gates_open_task(project_root)
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None

    assert_graph_planner_gatherable_parity(
        reader,
        PIPE_WALL_ROOT,
        facts=facts,
        plan=plan,
        expansion_open=True,
    )


def test_api_current_ask_matches_planner_next_field(project_root: Path) -> None:
    from api.serializers import task_state
    from api.workflow_bootstrap import refresh_task_planning
    from engine.reference.standards_reader import StandardsReader

    manager = TaskStateManager()
    task = manager.create_task("nav-contract-api-ask", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    for inp in (
        straight_section_assumption(),
        internal_pressure_assumption(),
        legacy_input("internal_design_gage_pressure", 8.0, "bar"),
        legacy_input("outside_diameter__resolution_branch", "nps_lookup"),
    ):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id=PIPE_WALL_ROOT,
            ),
        )
    task = manager.get_task(task.task_id)
    facts = dict(task.fact_store.active_facts())
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None
    planner_next = planner_next_field(plan)
    assert planner_next is not None

    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)

    state = task_state(task, manager, reader=reader)
    api_ask = (state.get("current_ask") or {}).get("parameter_id")
    assert api_ask == planner_next


def test_api_submittable_matches_planner_submittable_projection(project_root: Path) -> None:
    manager, task, reader, facts = _pipe_wall_gates_open_task(project_root)
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None
    planner_submittable = planner_submittable_projection(plan)
    assert planner_submittable is not None

    from api.workflow_bootstrap import refresh_task_planning

    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)

    api_submittable = api_submittable_projection(task, manager, reader=reader)
    assert api_submittable == planner_submittable


def test_resolution_branch_switch_changes_only_active_prerequisites(tmp_path: Path) -> None:
    reader, root = build_synthetic_nav_pack(tmp_path)

    branch_x_facts = synthetic_gate_open_facts(task_id="alpha-branch-x")
    branch_x_facts.update(
        facts_from_inputs(
            {
                "alpha_resolution__resolution_branch": legacy_input(
                    "alpha_resolution__resolution_branch",
                    "branch_x",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            },
            task_id="alpha-branch-x",
        )
    )
    manager_x, task_x = _synthetic_task(reader, branch_x_facts)
    plan_x = build_engineering_plan(task_x, reader, existing_inputs=branch_x_facts)
    assert plan_x is not None
    graph_x = graph_active_direct_inputs(reader, root, facts=branch_x_facts)
    planner_x = planner_active_direct_inputs(plan_x)
    assert "alpha_input_x" in graph_x
    assert "alpha_input_y" not in graph_x
    assert "alpha_input_x" in planner_x
    assert "alpha_input_y" not in planner_x
    assert plan_x.input_strategy is not None
    assert plan_x.input_strategy.next_fields[0] in graph_x

    branch_y_facts = facts_from_inputs(
        {
            "alpha_gate": legacy_input(
                "alpha_gate",
                True,
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "alpha_path": legacy_input(
                "alpha_path",
                "path_y",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "alpha_resolution__resolution_branch": legacy_input(
                "alpha_resolution__resolution_branch",
                "branch_y",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id="alpha-branch-y",
    )
    manager_y, task_y = _synthetic_task(reader, branch_y_facts)
    plan_y = build_engineering_plan(task_y, reader, existing_inputs=branch_y_facts)
    assert plan_y is not None
    graph_y = graph_active_direct_inputs(reader, root, facts=branch_y_facts)
    assert "alpha_input_y" in graph_y
    assert "alpha_input_x" not in graph_y


def test_navigation_phase_order_does_not_activate_inactive_parameter(tmp_path: Path) -> None:
    order_a = ["alpha_resolution", "alpha_input_x", "alpha_input_y", "alpha_lookup_key"]
    order_b = ["alpha_lookup_key", "alpha_resolution", "alpha_input_x", "alpha_input_y"]

    reader_a, root = build_synthetic_nav_pack(tmp_path / "a", gathering_order=order_a)
    facts = synthetic_gate_open_facts(task_id="alpha-nav-order")
    manager, task = _synthetic_task(reader_a, facts)
    plan = build_engineering_plan(task, reader_a, existing_inputs=facts)
    assert plan is not None
    graph_fields = graph_active_direct_inputs(reader_a, root, facts=facts)
    assert "alpha_input_y" not in graph_fields

    reader_b, _root_b = build_synthetic_nav_pack(tmp_path / "b", gathering_order=order_b)
    manager_b, task_b = _synthetic_task(reader_b, facts)
    plan_b = build_engineering_plan(task_b, reader_b, existing_inputs=facts)
    assert plan_b is not None
    assert plan.input_strategy is not None
    assert plan_b.input_strategy is not None

    planner_fields = planner_active_direct_inputs(plan)
    assert "alpha_input_y" not in planner_fields
    graph_b = graph_active_direct_inputs(reader_b, root, facts=facts)
    assert "alpha_input_y" not in graph_b
    planner_b = planner_active_direct_inputs(plan_b)
    assert "alpha_input_y" not in planner_b


def test_missing_cache_uses_canonical_compile_not_legacy_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VER03_LEGACY_GRAPH_TRAVERSAL", raising=False)
    reader, root = build_synthetic_nav_pack(tmp_path)
    engine = GraphEngine()
    assert engine.uses_micro_graph(reader, root) is True
    assert legacy_graph_traversal_enabled(reader) is False

    facts = synthetic_gate_open_facts()
    preview = GraphTools(reader).preview_plan(task_id="alpha-canonical", root_id=root, inputs=facts)
    node_ids = set(preview.nodes)
    assert "ALPHA-ROOT" in node_ids
    assert "PARAM-alpha-gate" in node_ids or "ALPHA-PATH-X" in node_ids

    legacy_called = {"value": False}
    original = engine._collect_nodes

    def _guard(*args, **kwargs):
        legacy_called["value"] = True
        return original(*args, **kwargs)

    monkeypatch.setattr(engine, "_collect_nodes", _guard)
    engine.build_plan(task_id="alpha-canonical", root_id=root, inputs=facts, reader=reader)
    assert legacy_called["value"] is False
