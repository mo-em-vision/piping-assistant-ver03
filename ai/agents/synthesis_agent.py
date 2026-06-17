"""Report presentation synthesis — wording only, never engineering truth."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any

from models.agent import AgentAction, SynthesisResult
from models.report import ReportData

from ai.agents.base import BaseAgent
from ai.prompts_loader import load_prompt


class SynthesisAgent(BaseAgent):
    prompt_file = "synthesis_agent.md"

    def synthesize(self, report: ReportData) -> SynthesisResult:
        if self._client is None:
            return SynthesisResult(
                presentation=self._fallback_presentation(report),
                action=AgentAction.SYNTHESIZE_REPORT,
            )

        payload = self.complete_json(
            (
                "Structured report data (do not modify any values):\n"
                f"{json.dumps(asdict(report), indent=2, default=str)}"
            ),
            extra_system="Reproduce every numeric value and PASS/FAIL status exactly as given.",
        )
        presentation = str(payload.get("presentation", ""))
        self._assert_values_preserved(report, presentation)
        return SynthesisResult(
            presentation=presentation,
            action=AgentAction.SYNTHESIZE_REPORT,
        )

    @staticmethod
    def _fallback_presentation(report: ReportData) -> str:
        lines = [
            f"# {report.title}",
            "",
            f"Report ID: {report.report_id}",
            f"Graph version: {report.graph_version}",
            "",
            "## Sections",
        ]
        for section in report.sections:
            lines.append(f"- {section.node}: {section.paragraph or ''}")
            for key, value in section.inputs.items():
                lines.append(f"  - input {key}: {value}")
            for key, value in section.outputs.items():
                lines.append(f"  - output {key}: {value}")
        return "\n".join(lines)

    @staticmethod
    def _assert_values_preserved(report: ReportData, presentation: str) -> None:
        for section in report.sections:
            for value in section.inputs.values():
                token = str(value)
                if token and token not in presentation:
                    raise ValueError(
                        f"Synthesis output omitted engineering value: {token}"
                    )
            for value in section.outputs.values():
                token = str(value)
                if token and re.search(r"\d", token) and token not in presentation:
                    raise ValueError(
                        f"Synthesis output omitted engineering value: {token}"
                    )

    def explain_section(self, section_payload: dict[str, Any]) -> str:
        payload = self.complete_json(
            f"Report section:\n{json.dumps(section_payload, indent=2, default=str)}",
            extra_system=load_prompt("report_explanation.md"),
        )
        return str(payload.get("explanation", ""))
