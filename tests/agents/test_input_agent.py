"""Behavioral tests for InputAgent."""

from __future__ import annotations

from ai.agents.input_agent import InputAgent
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.task import Task, TaskStatus


def test_input_agent_identifies_missing_inputs() -> None:
    agent = InputAgent(client=None)
    task = Task(task_id="t1", status=TaskStatus.AWAITING_INPUT)

    result = agent.analyze(task, workflow=PIPE_WALL_THICKNESS_DESIGN)

    assert "design_pressure" in result.missing_inputs
    assert "outside_diameter" in result.missing_inputs
    assert any(request.input_id == "design_pressure" for request in result.requests)
    assert any("304.1.1" in request.reason for request in result.requests)
