"""Build normalized EngineeringPlan objects from graph planning state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.graph.navigation_phases import PhasedNavigation
from engine.graph.workflow_navigation import WorkflowNavigationConfig
from engine.planner.generic_plan import build_generic_engineering_plan
from engine.reference.standards_reader import StandardsReader
from models.engineering_plan import EngineeringPlan
from models.fact import Fact
from models.task import Task


def build_engineering_plan(
    task: Task,
    reader: StandardsReader,
    *,
    preview: Any | None = None,
    phased: PhasedNavigation | None = None,
    existing_inputs: dict[str, Fact] | None = None,
    path_decision: dict[str, str] | None = None,
    nav_config: WorkflowNavigationConfig | None = None,
    has_execution: bool = False,
    post_thickness_outputs: dict[str, Any] | None = None,
) -> EngineeringPlan | None:
    del nav_config, post_thickness_outputs
    plan = build_generic_engineering_plan(
        task,
        reader,
        preview=preview,
        phased=phased,
        existing_inputs=existing_inputs,
        path_decision=path_decision,
    )
    if plan is None:
        return None

    if has_execution:
        _promote_late_phase_inputs(plan)
    return plan


def _promote_late_phase_inputs(plan: EngineeringPlan) -> None:
    """Promote ask_later definition-phase inputs when earlier equations are resolved."""
    resolved_equations = [
        req
        for req in plan.requirements.values()
        if req.requirement_class == "equation_result" and req.status == "resolved"
    ]
    pending_equations = [
        req
        for req in plan.requirements.values()
        if req.requirement_class == "equation_result"
        and req.status in {"missing", "blocked", "ready"}
    ]
    if not resolved_equations or not pending_equations:
        return

    for req in plan.requirements.values():
        if req.phase != "definition_equation_completion":
            continue
        if req.question_spec and req.question_spec.ask_policy == "ask_later":
            req.question_spec.ask_policy = "ask_now"


@dataclass
class EngineeringPlanBuildContext:
    """Inputs for building a normalized engineering plan."""

    task: Task
    reader: StandardsReader | None = None
    preview: Any | None = None
    phased: PhasedNavigation | None = None
    existing_inputs: dict[str, Fact] | None = None
    path_decision: dict[str, str] | None = None
    nav_config: WorkflowNavigationConfig | None = None


def build_engineering_plan_from_context(context: EngineeringPlanBuildContext) -> EngineeringPlan | None:
    """Build normalized EngineeringPlan from a structured context object."""
    if context.reader is None:
        raise ValueError("EngineeringPlanBuildContext.reader is required")
    return build_engineering_plan(
        context.task,
        context.reader,
        preview=context.preview,
        phased=context.phased,
        existing_inputs=context.existing_inputs,
        path_decision=context.path_decision,
        nav_config=context.nav_config,
    )
