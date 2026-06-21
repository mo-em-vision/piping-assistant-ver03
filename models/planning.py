"""Planner layer navigation and planning data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .agent import AgentAction


class NavigationPhase(str, Enum):
    """Ordered phases for assumption-first parameter gathering."""

    EXPANSION_ASSUMPTIONS = "expansion_assumptions"
    PATH_DECISIONS = "path_decisions"
    PARAMETER_GATHERING = "parameter_gathering"
    COEFFICIENT_RESOLUTION = "coefficient_resolution"
    EXECUTION_ASSUMPTIONS = "execution_assumptions"
    READY = "ready"


@dataclass
class StructuredIntent:
    """Structured engineering intent from user language (doc 11 §5)."""

    action: str | None = None
    object: str | None = None
    domain: str | None = None
    confidence: float = 0.0
    workflow: str | None = None


@dataclass
class WorkflowCandidate:
    """Candidate workflow root discovered by the Graph Engine."""

    root_id: str
    title: str
    engineering_intent: str | None = None
    standard: str = "ASME B31.3"
    confidence: float = 0.0
    implemented: bool = True


@dataclass
class NavigationPlan:
    """Detailed navigation plan produced by the Planner Layer (doc 11 §10)."""

    goal: str | None = None
    intent: str | None = None
    candidate_roots: list[WorkflowCandidate] = field(default_factory=list)
    selected_root: str | None = None
    selected_nodes: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    missing_assumptions: list[str] = field(default_factory=list)
    missing_execution_assumptions: list[str] = field(default_factory=list)
    blocked_nodes: list[str] = field(default_factory=list)
    block_messages: list[str] = field(default_factory=list)
    path_decision: dict[str, str] | None = None
    questions: list[str] = field(default_factory=list)
    alternative_paths: list[str] = field(default_factory=list)
    confidence: float = 0.0
    action: AgentAction = AgentAction.PROPOSE_PATH
    priorities: list[str] = field(default_factory=list)
    current_phase: NavigationPhase = NavigationPhase.EXPANSION_ASSUMPTIONS
    phase_missing: dict[str, list[str]] = field(default_factory=dict)
