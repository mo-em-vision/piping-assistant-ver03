"""MVP strategy §21 — performance testing."""

from __future__ import annotations

import time

from engine.executor.executor import execute_workflow
from engine.graph.graph_engine import GraphEngine
from tests.acceptance.helpers import (
    PIPE_WALL_THICKNESS_ROOT,
    measure_graph_plan_time,
    run_completed_workflow,
    sample_inputs,
)


class TestPerformanceTesting:
    """§21 Performance — graph traversal and execution preparation under 10 seconds."""

    def test_graph_traversal_under_target(self, standards_reader) -> None:
        average = measure_graph_plan_time(standards_reader, iterations=10)
        assert average < 10.0, f"Graph plan averaged {average:.3f}s (target < 10s)"

    def test_dependency_resolution_under_target(self, standards_reader) -> None:
        engine = GraphEngine()
        start = time.perf_counter()
        for index in range(20):
            engine.build_plan(
                task_id=f"mvp-perf-deps-{index}",
                root_id=PIPE_WALL_THICKNESS_ROOT,
                inputs=sample_inputs(),
                reader=standards_reader,
            )
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"20 graph plans took {elapsed:.3f}s"

    def test_full_workflow_execution_under_target(self, standards_reader, state_manager) -> None:
        task_id = "pipe-wall-thickness-design-mvp-perf-exec"
        start = time.perf_counter()
        run_completed_workflow(state_manager, standards_reader, task_id)
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"Workflow execution took {elapsed:.3f}s"

    def test_execution_preparation_is_consistent(self, standards_reader) -> None:
        samples = [measure_graph_plan_time(standards_reader, iterations=3) for _ in range(3)]
        assert max(samples) < 10.0
        assert max(samples) - min(samples) < 5.0
