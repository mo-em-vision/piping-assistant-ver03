"""Behavioral tests for InputAgent."""

from __future__ import annotations

from ai.agents.input_agent import InputAgent
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.task import Task, new_task, TaskStatus


def test_input_agent_identifies_missing_inputs() -> None:
    agent = InputAgent(client=None)
    task = new_task("t1", status=TaskStatus.AWAITING_INPUT)

    result = agent.analyze(task, workflow=PIPE_WALL_THICKNESS_DESIGN)

    assert "straight_pipe_section" in result.missing_inputs
    assert "pressure_design_case" in result.missing_inputs
    assert "design_pressure" in result.missing_inputs
    assert "outside_diameter" in result.missing_inputs
    assert "material" in result.missing_inputs
    assert "design_temperature" in result.missing_inputs
    assert "allowable_stress" not in result.missing_inputs
    assert any(request.input_id == "pressure_design_case" for request in result.requests)
    assert any(request.input_id == "design_pressure" for request in result.requests)
    assert any("304.1.1" in request.reason for request in result.requests)


def test_enrich_with_llm_preserves_known_symbols() -> None:
    agent = InputAgent(client=None)
    task = new_task("t1", status=TaskStatus.AWAITING_INPUT)
    requests = [
        agent._build_request("temperature_coefficient_Y", None),
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
    enriched = agent._enrich_with_llm(task, ["temperature_coefficient_Y"], requests, None)

    assert enriched[0].symbol == "Y"
