"""MVP strategy §10–§11 — deterministic testing and graph regression."""

from __future__ import annotations

from engine.graph.graph_engine import GraphEngine
from engine.state.state_manager import TaskStateManager
from tests.acceptance.helpers import (
    MATERIAL_STRESS_NODE,
    PIPE_WALL_THICKNESS_ROOT,
    WALL_THICKNESS_NODE,
    normalize_execution_trace,
    run_completed_workflow,
    sample_inputs,
)


class TestDeterministicTesting:
    """§10 Deterministic Testing — same input produces same result and trace."""

    def test_repeated_runs_produce_identical_outputs(self, standards_reader) -> None:
        outputs = []
        for index in range(3):
            manager = TaskStateManager()
            run_completed_workflow(
                manager,
                standards_reader,
                f"pipe-wall-thickness-design-mvp-det-{index}",
            )
            task = manager.get_task(f"pipe-wall-thickness-design-mvp-det-{index}")
            outputs.append(
                {
                    "required_thickness": task.outputs["required_thickness"],
                    "allowable_stress": task.outputs["allowable_stress"],
                    "trace": normalize_execution_trace(task.outputs["_execution_trace"]),
                }
            )

        assert outputs[0] == outputs[1] == outputs[2]

    def test_graph_and_node_versions_recorded(self, standards_reader, state_manager) -> None:
        task_id = "pipe-wall-thickness-design-mvp-versions"
        run_completed_workflow(state_manager, standards_reader, task_id)
        task = state_manager.get_task(task_id)

        graph_version = task.outputs.get("graph_version", {})
        assert graph_version.get("nodes")
        trace = task.outputs.get("_execution_trace", [])
        assert any(entry.get("node_version") for entry in trace if isinstance(entry, dict))


class TestGraphRegression:
    """§11 Graph Regression — node dependencies drive affected workflows."""

    def test_material_stress_is_dependency_of_thickness_node(self, standards_reader) -> None:
        thickness = standards_reader.load(WALL_THICKNESS_NODE)
        depends_on = [
            item.get("node_id") if isinstance(item, dict) else str(item)
            for item in thickness.metadata.get("depends_on", [])
        ]
        assert MATERIAL_STRESS_NODE in depends_on

    def test_workflow_revalidates_dependent_node_order(self, standards_reader) -> None:
        plan = GraphEngine().build_plan(
            task_id="mvp-graph-regression",
            root_id=PIPE_WALL_THICKNESS_ROOT,
            inputs=sample_inputs(),
            reader=standards_reader,
        )
        assert MATERIAL_STRESS_NODE in plan.nodes
        assert WALL_THICKNESS_NODE in plan.nodes
        assert plan.execution_order.index(MATERIAL_STRESS_NODE) < plan.execution_order.index(
            WALL_THICKNESS_NODE
        )

    def test_changed_dependency_still_traverses_workflow(self, standards_reader, state_manager) -> None:
        """Simulate workflow revalidation after input change affecting material lookup."""
        task_id = "pipe-wall-thickness-design-mvp-graph-change"
        run_completed_workflow(state_manager, standards_reader, task_id)
        first_stress = state_manager.get_task(task_id).outputs["allowable_stress"]

        state_manager.store_input(task_id, sample_inputs(temperature=400)["design_temperature"])
        run_completed_workflow(state_manager, standards_reader, task_id)
        second_stress = state_manager.get_task(task_id).outputs["allowable_stress"]

        plan = GraphEngine().build_plan(
            task_id=task_id,
            root_id=PIPE_WALL_THICKNESS_ROOT,
            inputs=dict(state_manager.get_task(task_id).inputs),
            reader=standards_reader,
        )
        assert plan.execution_order.index(MATERIAL_STRESS_NODE) < plan.execution_order.index(
            WALL_THICKNESS_NODE
        )
        assert first_stress != second_stress
