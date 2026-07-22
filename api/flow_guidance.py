"""Flow Guidance Layer payload for desktop/API task state."""

from __future__ import annotations

from typing import Any

from engine.presentation.guidance_resolver import GuidanceResolver, guidance_context_from_navigation
from engine.presentation.response_composer import ResponseComposer
from engine.reference.standards_reader import StandardsReader
from engine.state.goal_projection import planning_projection
from models.planning import NavigationPhase, NavigationPlan
from models.presentation import PresentationBlock, PresentationResponse
from models.task import Task


def navigation_plan_from_task(
    task: Task,
    *,
    reader: StandardsReader | None = None,
) -> NavigationPlan:
    """Build a NavigationPlan view from stored EngineeringPlan or goal-store projection."""
    from engine.planner.navigation_projection import navigation_plan_from_engineering_plan
    from engine.planner.plan_selection import engineering_plan_for_task

    engineering_plan = engineering_plan_for_task(task)
    if engineering_plan is not None:
        path_decision = task.outputs.get("path_decision")
        return navigation_plan_from_engineering_plan(
            engineering_plan,
            task=task,
            reader=reader,
            path_decision=path_decision if isinstance(path_decision, dict) else None,
        )

    planning = planning_projection(task)
    try:
        phase = NavigationPhase(
            str(planning.get("current_phase") or NavigationPhase.READY.value)
        )
    except ValueError:
        phase = NavigationPhase.READY

    path_decision = planning.get("path_decision")
    return NavigationPlan(
        current_phase=phase,
        phase_missing={
            str(phase_name): list(fields)
            for phase_name, fields in (planning.get("phase_missing") or {}).items()
            if isinstance(fields, list)
        },
        missing_inputs=[
            str(item) for item in (planning.get("missing_inputs") or []) if item
        ],
        path_decision=path_decision if isinstance(path_decision, dict) else None,
        selected_nodes=[
            str(item) for item in (planning.get("selected_nodes") or []) if item
        ],
    )


def _active_node_id_for_guidance(task: Task, navigation_plan: NavigationPlan) -> str | None:
    if navigation_plan.selected_nodes:
        return navigation_plan.selected_nodes[-1]
    selected = task.outputs.get("selected_root")
    if isinstance(selected, str) and selected:
        return selected
    return None


def _node_role_for_guidance(navigation_plan: NavigationPlan) -> str | None:
    if navigation_plan.current_phase == NavigationPhase.PARAMETER_GATHERING:
        return "equation"
    if navigation_plan.current_phase in {
        NavigationPhase.EXPANSION_ASSUMPTIONS,
        NavigationPhase.PATH_DECISIONS,
    }:
        return "paragraph"
    return None


def build_flow_guidance_payload(
    task: Task,
    reader: StandardsReader,
    *,
    transcript_blocks: tuple[PresentationBlock, ...] = (),
) -> dict[str, Any]:
    """Return UI-neutral Flow Guidance output for API/Desktop consumers."""
    workflow_id = str(
        task.outputs.get("workflow")
        or task.outputs.get("selected_root")
        or ""
    )
    if not workflow_id:
        empty = PresentationResponse()
        return empty.to_dict()

    navigation_plan = navigation_plan_from_task(task, reader=reader)
    task_facts = {
        key: fact.value for key, fact in task.fact_store.active_facts().items()
    }
    guidance_context = guidance_context_from_navigation(
        workflow_id=workflow_id,
        current_phase=navigation_plan.current_phase.value,
        phase_missing=navigation_plan.phase_missing,
        active_node_id=_active_node_id_for_guidance(task, navigation_plan),
        node_role=_node_role_for_guidance(navigation_plan),
        task_facts=task_facts,
    )

    resolver = GuidanceResolver()
    guidance_blocks = resolver.resolve(guidance_context)
    composer = ResponseComposer()
    response = composer.compose(
        task=task,
        reader=reader,
        guidance_blocks=guidance_blocks,
        transcript_blocks=transcript_blocks,
        navigation_plan=navigation_plan,
        missing_input_ids=navigation_plan.missing_inputs,
        validation_warnings=tuple(task.warnings),
    )
    return response.to_dict()
