"""Graph-to-Planner gatherable direct-input parity contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.router import MAWP_DESIGN
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.input import InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.graph.conftest import PIPE_WALL_ROOT
from tests.helpers.facts import facts_from_inputs, legacy_input
from tests.navigation.fixtures.synthetic_nav_pack import (
    build_synthetic_nav_pack,
    synthetic_gate_open_facts,
)
from tests.navigation.helpers.contracts import (
    assert_graph_planner_gatherable_parity,
    graph_active_direct_inputs,
    is_planner_direct_input_requirement,
    planner_active_direct_inputs,
)


def _pipe_wall_gates_open(project_root: Path):
    from engine.reference.standards_reader import StandardsReader

    manager = TaskStateManager()
    task = manager.create_task("parity-pwt-gates", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(inp, task_id=task.task_id, workflow_id=PIPE_WALL_ROOT),
        )
    task = manager.get_task(task.task_id)
    facts = dict(task.fact_store.active_facts())
    return manager, task, reader, facts


def _synthetic_task(reader, root: str, facts):
    manager = TaskStateManager()
    task = manager.create_task("parity-alpha", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = root
    task.outputs["selected_root"] = root
    for fact in facts.values():
        manager.store_fact(task.task_id, fact)
    return manager, manager.get_task(task.task_id)


def _gatherable_fields(plan) -> list[str]:
    fields: list[str] = []
    for req in plan.requirements.values():
        field = is_planner_direct_input_requirement(req)
        if field:
            fields.append(field)
    return sorted(fields)


def _assert_unique_gatherable(plan) -> None:
    fields = _gatherable_fields(plan)
    assert len(fields) == len(set(fields))


def test_pipe_wall_gates_open_parity(project_root: Path) -> None:
    """Test 1 — pipe-wall internal-pressure gates-open parity."""
    _, task, reader, facts = _pipe_wall_gates_open(project_root)
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None

    assert_graph_planner_gatherable_parity(
        reader,
        PIPE_WALL_ROOT,
        facts=facts,
        plan=plan,
        expansion_open=True,
    )

    planner_fields = planner_active_direct_inputs(plan)
    assert "internal_design_gage_pressure" in planner_fields
    assert "design_temperature" in planner_fields
    assert "material_grade" in planner_fields
    assert "pipe_construction_type" in planner_fields
    assert "outside_diameter" in planner_fields
    assert "corrosion_allowance" not in planner_fields
    _assert_unique_gatherable(plan)


def test_pipe_wall_nps_branch_parity(project_root: Path) -> None:
    """Test 2 — NPS branch parity."""
    manager, task, reader, facts = _pipe_wall_gates_open(project_root)
    for inp in (
        legacy_input("internal_design_gage_pressure", 8.0, "bar"),
        legacy_input("outside_diameter__resolution_branch", "nps_lookup"),
    ):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(inp, task_id=task.task_id, workflow_id=PIPE_WALL_ROOT),
        )
    task = manager.get_task(task.task_id)
    facts = dict(task.fact_store.active_facts())
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None

    assert_graph_planner_gatherable_parity(
        reader,
        PIPE_WALL_ROOT,
        facts=facts,
        plan=plan,
        expansion_open=True,
    )

    planner_fields = planner_active_direct_inputs(plan)
    assert "nominal_pipe_size" in planner_fields
    assert "outside_diameter" not in planner_fields
    _assert_unique_gatherable(plan)


def test_pipe_wall_direct_od_branch_parity(project_root: Path) -> None:
    """Test 3 — direct-OD branch parity."""
    manager = TaskStateManager()
    task = manager.create_task("parity-pwt-direct", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = __import__(
        "engine.reference.standards_reader", fromlist=["StandardsReader"]
    ).StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    for inp in (
        straight_section_assumption(),
        internal_pressure_assumption(),
        legacy_input("internal_design_gage_pressure", 8.0, "bar"),
        legacy_input("outside_diameter__resolution_branch", "direct_od"),
    ):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(inp, task_id=task.task_id, workflow_id=PIPE_WALL_ROOT),
        )
    task = manager.get_task(task.task_id)
    facts = dict(task.fact_store.active_facts())
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None

    assert_graph_planner_gatherable_parity(
        reader,
        PIPE_WALL_ROOT,
        facts=facts,
        plan=plan,
        expansion_open=True,
    )

    planner_fields = planner_active_direct_inputs(plan)
    assert "outside_diameter" in planner_fields
    assert "nominal_pipe_size" not in planner_fields
    _assert_unique_gatherable(plan)


def test_synthetic_branch_x_parity(tmp_path: Path) -> None:
    """Test 4 — synthetic branch X parity."""
    reader, root = build_synthetic_nav_pack(tmp_path / "branch-x")
    facts = synthetic_gate_open_facts(task_id="parity-alpha-x")
    _, task = _synthetic_task(reader, root, facts)
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None

    assert_graph_planner_gatherable_parity(
        reader,
        root,
        facts=facts,
        plan=plan,
        expansion_open=True,
    )

    planner_fields = planner_active_direct_inputs(plan)
    assert "alpha_input_x" in planner_fields
    assert "alpha_input_y" not in planner_fields
    assert "alpha_lookup_key" in planner_fields
    assert "alpha_lookup_output" not in planner_fields
    assert "alpha_derived_output" not in planner_fields
    _assert_unique_gatherable(plan)


def test_synthetic_branch_y_parity(tmp_path: Path) -> None:
    """Test 5 — synthetic branch Y parity."""
    reader, root = build_synthetic_nav_pack(tmp_path / "branch-y")
    facts = facts_from_inputs(
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
        task_id="parity-alpha-y",
    )
    _, task = _synthetic_task(reader, root, facts)
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None

    assert_graph_planner_gatherable_parity(
        reader,
        root,
        facts=facts,
        plan=plan,
        expansion_open=True,
    )

    planner_fields = planner_active_direct_inputs(plan)
    assert "alpha_input_y" in planner_fields
    assert "alpha_input_x" not in planner_fields
    assert plan.input_strategy is not None
    assert plan.input_strategy.next_fields[0] == "alpha_input_y"
    _assert_unique_gatherable(plan)


def test_navigation_phase_order_does_not_activate_inactive_field(tmp_path: Path) -> None:
    """Test 6 — phase order must not activate inapplicable fields."""
    order_a = ["alpha_resolution", "alpha_input_x", "alpha_input_y", "alpha_lookup_key"]
    order_b = ["alpha_lookup_key", "alpha_resolution", "alpha_input_x", "alpha_input_y"]

    reader_a, root = build_synthetic_nav_pack(tmp_path / "order-a", gathering_order=order_a)
    facts = synthetic_gate_open_facts(task_id="parity-nav-order")
    _, task_a = _synthetic_task(reader_a, root, facts)
    plan_a = build_engineering_plan(task_a, reader_a, existing_inputs=facts)
    assert plan_a is not None

    graph_a = graph_active_direct_inputs(reader_a, root, facts=facts)
    planner_a = planner_active_direct_inputs(plan_a)
    assert "alpha_input_y" not in graph_a
    assert "alpha_input_y" not in planner_a

    reader_b, _ = build_synthetic_nav_pack(tmp_path / "order-b", gathering_order=order_b)
    _, task_b = _synthetic_task(reader_b, root, facts)
    plan_b = build_engineering_plan(task_b, reader_b, existing_inputs=facts)
    assert plan_b is not None
    graph_b = graph_active_direct_inputs(reader_b, root, facts=facts)
    planner_b = planner_active_direct_inputs(plan_b)
    assert "alpha_input_y" not in graph_b
    assert "alpha_input_y" not in planner_b


def test_late_phase_field_not_over_emitted_before_graph_requires(project_root: Path) -> None:
    """Test 7 — corrosion_allowance not gatherable before Graph requires it."""
    _, task, reader, facts = _pipe_wall_gates_open(project_root)
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None

    graph_fields = graph_active_direct_inputs(reader, PIPE_WALL_ROOT, facts=facts)
    planner_fields = planner_active_direct_inputs(plan)
    assert "corrosion_allowance" not in graph_fields
    assert "corrosion_allowance" not in planner_fields


def test_gatherable_requirement_uniqueness_across_fixtures(
    project_root: Path,
    tmp_path: Path,
) -> None:
    """Test 8 — each comparable field appears at most once per fixture."""
    _, task, reader, facts = _pipe_wall_gates_open(project_root)
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None
    _assert_unique_gatherable(plan)

    reader_syn, root = build_synthetic_nav_pack(tmp_path / "unique")
    syn_facts = synthetic_gate_open_facts(task_id="parity-unique")
    _, syn_task = _synthetic_task(reader_syn, root, syn_facts)
    syn_plan = build_engineering_plan(syn_task, reader_syn, existing_inputs=syn_facts)
    assert syn_plan is not None
    _assert_unique_gatherable(syn_plan)


def test_pre_expansion_gate_fields_allowed_when_graph_empty(project_root: Path) -> None:
    """Approved parity exception — fresh workflow before expansion opens."""
    from engine.reference.standards_reader import StandardsReader

    manager = TaskStateManager()
    task = manager.create_task("parity-pwt-fresh", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    facts: dict = {}
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None

    assert_graph_planner_gatherable_parity(
        reader,
        PIPE_WALL_ROOT,
        facts=facts,
        plan=plan,
        expansion_open=False,
    )


def test_mawp_pre_expansion_gate_parity(project_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("parity-mawp-fresh", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_DESIGN
    task.outputs["selected_root"] = MAWP_DESIGN
    from engine.reference.standards_reader import StandardsReader

    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    facts: dict = {}
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None
    assert_graph_planner_gatherable_parity(
        reader,
        MAWP_DESIGN,
        facts=facts,
        plan=plan,
        expansion_open=False,
    )
