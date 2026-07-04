"""Behavioral tests for SynthesisAgent and ResponseHandler."""

from __future__ import annotations

from ai.agents.synthesis_agent import SynthesisAgent
from ai.response.response_handler import ResponseHandler
from models.agent import IntentResult
from models.report import ReportData, ReportSection


def test_synthesis_agent_fallback_preserves_report_values() -> None:
    report = ReportData(
        report_id="001",
        title="Pipe Wall Thickness",
        graph_version="pipe_wall_thickness_design",
        sections=[
            ReportSection(
                node="304.1.2-a",
                paragraph="304.1.1",
                inputs={"design_pressure": 500},
                outputs={"required_thickness": 0.065},
            )
        ],
    )
    agent = SynthesisAgent(client=None)
    result = agent.synthesize(report)

    assert "500" in result.presentation
    assert "0.065" in result.presentation


def test_response_handler_formats_intent_without_hiding_structure() -> None:
    handler = ResponseHandler()
    text = handler.format_intent(
        IntentResult(
            intent="pipe_wall_thickness_design",
            domain="piping",
            possible_standards=["ASME B31.3"],
            root_nodes=["tasks/asme_b31.3/pipe_wall_thickness_design/root.md"],
            confidence=0.95,
        )
    )

    assert "pipe_wall_thickness_design" in text
    assert "ASME B31.3" in text
