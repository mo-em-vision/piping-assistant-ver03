"""Acceptance criteria §18 and §19 — reproducibility and performance."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from tests.acceptance.helpers import (
    measure_graph_plan_time,
    normalize_execution_trace,
    run_completed_workflow,
)


class TestReproducibilityAcceptance:
    """§18 Reproducibility — same input produces same result and trace."""

    def test_same_inputs_produce_same_results(self, standards_reader) -> None:
        first_manager = TaskStateManager()
        second_manager = TaskStateManager()
        run_completed_workflow(
            first_manager,
            standards_reader,
            "pipe-wall-thickness-design-acceptance-repro-a",
        )
        run_completed_workflow(
            second_manager,
            standards_reader,
            "pipe-wall-thickness-design-acceptance-repro-b",
        )

        first_outputs = first_manager.get_task("pipe-wall-thickness-design-acceptance-repro-a").outputs
        second_outputs = second_manager.get_task("pipe-wall-thickness-design-acceptance-repro-b").outputs
        assert first_outputs["required_thickness"] == second_outputs["required_thickness"]
        assert first_outputs["allowable_stress"] == second_outputs["allowable_stress"]

    def test_same_inputs_produce_equivalent_execution_trace(self, standards_reader) -> None:
        first_manager = TaskStateManager()
        second_manager = TaskStateManager()
        run_completed_workflow(first_manager, standards_reader, "pipe-wall-thickness-design-acceptance-trace-a")
        run_completed_workflow(second_manager, standards_reader, "pipe-wall-thickness-design-acceptance-trace-b")

        first_trace = normalize_execution_trace(
            first_manager.get_task("pipe-wall-thickness-design-acceptance-trace-a").outputs["_execution_trace"]
        )
        second_trace = normalize_execution_trace(
            second_manager.get_task("pipe-wall-thickness-design-acceptance-trace-b").outputs["_execution_trace"]
        )
        assert first_trace == second_trace

    def test_graph_version_is_recorded_for_replay(self, standards_reader, state_manager) -> None:
        task_id = "pipe-wall-thickness-design-acceptance-graph-version"
        run_completed_workflow(state_manager, standards_reader, task_id)
        graph_version = state_manager.get_task(task_id).outputs["graph_version"]

        assert graph_version
        assert graph_version.get("graph_id") in {
            "pipe_wall_thickness_design",
            "B313-PIPE-WALL-THICKNESS-DESIGN",
            "B313-WF-PIPE-WALL-THICKNESS",
            "WF-PIPE-WALL-THICKNESS",
        }
        assert "304.1.1-a" in graph_version.get("nodes", [])
        assert "304.1.2-a" in graph_version.get("nodes", [])

    def test_replay_frames_are_deterministic(self, standards_reader) -> None:
        import os

        os.environ["DEV_INSPECTION_ENABLED"] = "1"
        try:
            first_manager = TaskStateManager()
            second_manager = TaskStateManager()
            run_completed_workflow(first_manager, standards_reader, "pipe-wall-replay-a")
            run_completed_workflow(second_manager, standards_reader, "pipe-wall-replay-b")

            first_snapshot = first_manager.get_task("pipe-wall-replay-a").outputs.get("_replay_snapshot")
            second_snapshot = second_manager.get_task("pipe-wall-replay-b").outputs.get("_replay_snapshot")
            assert isinstance(first_snapshot, dict)
            assert isinstance(second_snapshot, dict)
            assert first_snapshot.get("frame_count") == second_snapshot.get("frame_count")
            if first_snapshot.get("frame_count", 0) > 0:
                first_frame = first_snapshot["frames"][0]
                second_frame = second_snapshot["frames"][0]
                assert first_frame.get("outputs") == second_frame.get("outputs")
        finally:
            os.environ.pop("DEV_INSPECTION_ENABLED", None)


class TestPerformanceAcceptance:
    """§19 Performance — reasonable response time."""

    def test_graph_plan_builds_within_reasonable_time(self, standards_reader) -> None:
        average_seconds = measure_graph_plan_time(standards_reader, iterations=10)
        assert average_seconds < 10.0, f"Graph plan averaged {average_seconds:.2f}s"
