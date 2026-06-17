"""AI agent context and structured agent output models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentAction(str, Enum):
    REQUEST_INPUT = "request_input"
    CLARIFY = "clarify"
    PROPOSE_PATH = "propose_path"
    ROUTE_STANDARD = "route_standard"
    CONTEXT_SWITCH = "context_switch"
    SYNTHESIZE_REPORT = "synthesize_report"
    GENERAL_RESPONSE = "general_response"
    CONFIRM_OVERRIDE = "confirm_override"


@dataclass
class AgentContext:
    intent: str | None = None
    available_nodes: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    active_task_id: str | None = None
    user_message: str | None = None
    workflow: str | None = None


@dataclass
class IntentResult:
    intent: str | None
    domain: str | None
    possible_standards: list[str] = field(default_factory=list)
    root_nodes: list[str] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    confidence: float = 0.0
    workflow: str | None = None
    action: AgentAction = AgentAction.CLARIFY
    message: str | None = None


@dataclass
class PlannerResult:
    priorities: list[str] = field(default_factory=list)
    root_nodes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    action: AgentAction = AgentAction.PROPOSE_PATH


@dataclass
class InputRequest:
    action: AgentAction
    input_id: str
    reason: str
    node_id: str | None = None
    symbol: str | None = None


@dataclass
class InputAgentResult:
    requests: list[InputRequest] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    action: AgentAction = AgentAction.REQUEST_INPUT


@dataclass
class StandardOption:
    standard: str
    description: str


@dataclass
class RoutingResult:
    options: list[StandardOption] = field(default_factory=list)
    action: AgentAction = AgentAction.ROUTE_STANDARD
    message: str | None = None
    selected_standard: str | None = None


@dataclass
class ContextResult:
    context_switch_detected: bool
    preserve_task: bool
    active_task_id: str | None = None
    message: str = ""
    action: AgentAction = AgentAction.CONTEXT_SWITCH


@dataclass
class AlternativePathRecord:
    selected: str
    alternative: str
    reason: str | None = None


@dataclass
class SynthesisResult:
    presentation: str
    action: AgentAction = AgentAction.SYNTHESIZE_REPORT


@dataclass
class OverrideConfirmation:
    violated_rule: str
    user_decision: str
    reason: str
    action: AgentAction = AgentAction.CONFIRM_OVERRIDE
