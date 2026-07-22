"""Behavioral tests for InputAgent."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai.agents.input_agent import InputAgent
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.state.state_manager import TaskStateManager
from models.planning import NavigationPhase, NavigationPlan
from models.task import Task, new_task, TaskStatus


def _reader(project_root: Path):
    from engine.reference.standards_reader import StandardsReader

    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_input_agent_uses_navigation_plan_missing_inputs() -> None:
    agent = InputAgent(client=None)
    task = new_task("t1", status=TaskStatus.AWAITING_INPUT)
    navigation_plan = NavigationPlan(
        selected_root=PIPE_WALL_THICKNESS_DESIGN,
        current_phase=NavigationPhase.EXPANSION_ASSUMPTIONS,
        phase_missing={
            NavigationPhase.EXPANSION_ASSUMPTIONS.value: [
                "straight_pipe_section",
                "pressure_design_case",
            ],
        },
        questions=[
            "Is this a straight pipe section?",
            "Is the pipe internally or externally pressurized?",
        ],
    )

    result = agent.analyze(task, workflow=PIPE_WALL_THICKNESS_DESIGN, navigation_plan=navigation_plan)

    assert result.missing_inputs == ["straight_pipe_section", "pressure_design_case"]
    assert any(request.input_id == "pressure_design_case" for request in result.requests)


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[2].joinpath(
        "knowledge", "standards", "asme", "asme_b31.3"
    ).exists(),
    reason="ASME B31.3 pack required",
)
def test_input_agent_mawp_missing_inputs_from_graph(project_root: Path) -> None:
    agent = InputAgent(client=None)
    manager = TaskStateManager()
    task = manager.create_task("mawp-input-agent", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_DESIGN
    reader = _reader(project_root)

    result = agent.analyze(task, workflow=MAWP_DESIGN, reader=reader)

    assert result.missing_inputs
    assert "straight_pipe_section" in result.missing_inputs or "pressure_design_case" in result.missing_inputs


def test_enrich_with_llm_preserves_known_symbols() -> None:
    agent = InputAgent(client=None)
    task = new_task("t1", status=TaskStatus.AWAITING_INPUT)
    requests = [
        agent._build_request(task, "temperature_coefficient_Y", None, reader=None),
    ]

    def fake_complete_json(_prompt: str) -> dict:
        return {
            "requests": [
                {
                    "input_id": "temperature_coefficient_Y",
                    "symbol": "α",
                    "reason": "LLM reason",
                    "node_id": "B313-302.2",
                }
            ]
        }

    agent.complete_json = fake_complete_json  # type: ignore[method-assign]
    enriched = agent._enrich_with_llm(task, ["temperature_coefficient_Y"], requests, None, reader=None)

    assert enriched[0].symbol is None
    assert enriched[0].reason == "LLM reason"
