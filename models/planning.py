"""Planner layer navigation and planning data structures."""

from __future__ import annotations

from dataclasses import dataclass, field

from .agent import AgentAction


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
    questions: list[str] = field(default_factory=list)
    alternative_paths: list[str] = field(default_factory=list)
    confidence: float = 0.0
    action: AgentAction = AgentAction.PROPOSE_PATH
    priorities: list[str] = field(default_factory=list)
