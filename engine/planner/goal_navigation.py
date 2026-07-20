"""Goal-guided navigation: pick the next user-facing ask from the runtime goal tree."""

from __future__ import annotations

from typing import Any

from engine.messaging.parameter_input_prompt import (
    build_parameter_input_prompt,
    build_short_parameter_input_prompt,
)
from engine.messaging.parameter_prompt_context import parameter_metadata_context
from engine.reference.standards_reader import StandardsReader
from models.fact import fact_is_expansion_ready
from models.goal import Goal, GoalClass, SatisfactionStatus, goal_parameter_key
from models.task import Task

_USER_ASK_GOAL_CLASSES = frozenset({GoalClass.INPUT, GoalClass.SELECTION})


def _param_satisfied(task: Task, parameter: str) -> bool:
    fact = task.fact_store.active_fact(parameter)
    if fact is None:
        return False
    return fact_is_expansion_ready(fact)


def _sorted_child_goals(task: Task, root: Goal) -> list[Goal]:
    children = task.goal_store.children(root.id)

    def sort_key(goal: Goal) -> tuple[int, str]:
        meta_order = goal.metadata.get("order")
        meta = int(meta_order) if isinstance(meta_order, int) else 10_000
        return (meta, goal.key)

    return sorted(children, key=sort_key)


def next_actionable_goal(task: Task) -> Goal | None:
    """First unsatisfied input/selection goal that is ready for user submission."""
    roots = task.goal_store.roots()
    if not roots:
        return None

    root = roots[0]
    for goal in _sorted_child_goals(task, root):
        if goal.goal_class not in _USER_ASK_GOAL_CLASSES:
            continue
        if goal.satisfaction.status in {
            SatisfactionStatus.SATISFIED,
            SatisfactionStatus.SUPERSEDED,
        }:
            continue
        if goal.state.blocked_by:
            continue
        if goal.satisfaction.status == SatisfactionStatus.BLOCKED:
            continue
        param = goal_parameter_key(goal)
        if _param_satisfied(task, param):
            continue
        from engine.navigation import composer_parameter_id, step_applies_for_timeline
        from engine.graph.definition_equations import has_execution_trace
        from engine.planner.workflow_goal_metadata import goal_output_value_for_task
        from models.planning import NavigationPhase

        if (
            str(goal.metadata.get("phase") or "") == NavigationPhase.DEFINITION_EQUATION_COMPLETION.value
            and not (has_execution_trace(task) and goal_output_value_for_task(task) is not None)
        ):
            continue

        if not step_applies_for_timeline(task, param):
            continue
        if goal.satisfaction.status in {SatisfactionStatus.PENDING, SatisfactionStatus.READY}:
            goal.metadata["composer_parameter"] = composer_parameter_id(task, param)
            return goal
    return None


def clarify_blocked_goal(task: Task) -> Goal | None:
    """First blocked goal with a user-facing clarify prompt when no input is actionable."""
    if next_actionable_goal(task) is not None:
        return None
    for goal in task.goal_store.blocked_goals():
        if goal.question and goal.question.prompt.strip():
            return goal
    return None


def goal_collection_parameter_ids(task: Task) -> list[str]:
    """Parameter keys in planner / node-expansion order."""
    roots = task.goal_store.roots()
    if not roots:
        return []
    ordered: list[str] = []
    seen: set[str] = set()
    for goal in _sorted_child_goals(task, roots[0]):
        if goal.goal_class not in _USER_ASK_GOAL_CLASSES:
            continue
        param = goal_parameter_key(goal)
        if param in seen:
            continue
        seen.add(param)
        ordered.append(param)
    return ordered


def goal_guided_parameter_ids(task: Task) -> list[str]:
    """Parameter ids the user should submit next (one primary ask)."""
    goal = next_actionable_goal(task)
    if goal is None:
        return []
    composer = goal.metadata.get("composer_parameter")
    if isinstance(composer, str) and composer.strip():
        return [composer]
    from engine.navigation import composer_parameter_id

    return [composer_parameter_id(task, goal_parameter_key(goal))]


def _prompt_for_goal(
    goal: Goal,
    planning: dict[str, Any],
    *,
    task: Task | None = None,
    reader: StandardsReader | None = None,
) -> str | None:
    param = goal_parameter_key(goal)
    if reader is not None and task is not None:
        built = build_parameter_input_prompt(reader, task, param, planning=planning)
        if built:
            return built

    if goal.question and goal.question.prompt.strip():
        return goal.question.prompt.strip()
    phase_questions = planning.get("phase_questions") or {}
    phase_missing = planning.get("phase_missing") or {}
    if not isinstance(phase_questions, dict) or not isinstance(phase_missing, dict):
        return None
    for phase, fields in phase_missing.items():
        if not isinstance(fields, list) or param not in fields:
            continue
        questions = phase_questions.get(phase)
        if isinstance(questions, dict):
            prompt = questions.get(param)
            if isinstance(prompt, str) and prompt.strip():
                return prompt.strip()
        elif isinstance(questions, list):
            index = fields.index(param)
            if index < len(questions):
                prompt = questions[index]
                if isinstance(prompt, str) and prompt.strip():
                    return prompt.strip()
    return None


def _attach_short_prompt(
    ask: dict[str, Any],
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None,
) -> dict[str, Any]:
    kind = ask.get("kind")
    if kind == "input":
        param = ask.get("parameter_id")
        if isinstance(param, str) and param.strip() and reader is not None:
            metadata_ctx = parameter_metadata_context(reader, param.strip())
            if metadata_ctx is not None and metadata_ctx.help_text:
                ask["help_text"] = metadata_ctx.help_text
            short = build_short_parameter_input_prompt(
                reader,
                task,
                param.strip(),
                planning=planning,
            )
            if short:
                ask["short_prompt"] = short
    elif kind == "clarify":
        prompt = ask.get("prompt")
        if isinstance(prompt, str) and prompt.strip():
            ask["short_prompt"] = prompt.strip()
    elif kind == "waiting":
        prompt = ask.get("prompt")
        if isinstance(prompt, str) and prompt.strip():
            ask["short_prompt"] = prompt.strip()
    return ask


def _clarify_ask(task: Task, planning: dict[str, Any], *, reader: StandardsReader | None) -> dict[str, Any] | None:
    for goal in task.goal_store.blocked_goals():
        if goal.question and goal.question.prompt.strip():
            prompt = goal.question.prompt.strip()
            return _attach_short_prompt(
                {
                    "kind": "clarify",
                    "parameter_id": None,
                    "prompt": prompt,
                },
                task,
                planning,
                reader=reader,
            )
    return None


def _build_input_ask_for_parameter(
    task: Task,
    planning: dict[str, Any],
    param: str,
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any]:
    from engine.navigation import composer_parameter_id

    composer_param = composer_parameter_id(task, param)
    prompt: str | None = None
    if reader is not None:
        prompt = build_parameter_input_prompt(reader, task, composer_param, planning=planning)
    if prompt is None:
        phase_questions = planning.get("phase_questions") or {}
        phase_missing = planning.get("phase_missing") or {}
        if isinstance(phase_questions, dict) and isinstance(phase_missing, dict):
            for phase, fields in phase_missing.items():
                if not isinstance(fields, list) or composer_param not in fields:
                    continue
                questions = phase_questions.get(phase)
                if isinstance(questions, dict):
                    candidate = questions.get(composer_param)
                    if isinstance(candidate, str) and candidate.strip():
                        prompt = candidate.strip()
                        break
    return _attach_short_prompt(
        {
            "kind": "input",
            "parameter_id": composer_param,
            "prompt": prompt,
        },
        task,
        planning,
        reader=reader,
    )


def _waiting_ask_from_phase_missing(planning: dict[str, Any]) -> dict[str, Any] | None:
    phase_missing = planning.get("phase_missing") or {}
    if isinstance(phase_missing, dict):
        for fields in phase_missing.values():
            if isinstance(fields, list) and fields:
                return {
                    "kind": "waiting",
                    "parameter_id": None,
                    "prompt": None,
                }
    return None


def _build_stored_plan_current_ask(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any] | None:
    from engine.planner.plan_selection import (
        planner_next_field_from_task,
        planner_next_field_is_submittable,
    )
    from models.task import TaskStatus

    if task.status != TaskStatus.AWAITING_INPUT:
        return None

    planner_next = planner_next_field_from_task(task)
    if planner_next:
        if not planner_next_field_is_submittable(task, planning):
            return _waiting_ask_from_phase_missing(planning) or {
                "kind": "waiting",
                "parameter_id": None,
                "prompt": None,
            }
        return _build_input_ask_for_parameter(
            task,
            planning,
            planner_next,
            reader=reader,
        )

    current_phase = str(planning.get("current_phase") or "")
    if current_phase == "ready":
        return None

    clarify = _clarify_ask(task, planning, reader=reader)
    if clarify is not None:
        return clarify

    return _waiting_ask_from_phase_missing(planning)


def _build_legacy_current_ask(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any] | None:
    goal = next_actionable_goal(task)
    if goal is not None:
        param = goal_parameter_key(goal)
        from engine.navigation import composer_parameter_id

        composer_param = goal.metadata.get("composer_parameter")
        if not isinstance(composer_param, str) or not composer_param.strip():
            composer_param = composer_parameter_id(task, param)
        return _attach_short_prompt(
            {
                "kind": "input",
                "parameter_id": composer_param,
                "prompt": _prompt_for_goal(goal, planning, task=task, reader=reader),
            },
            task,
            planning,
            reader=reader,
        )

    blocked = clarify_blocked_goal(task)
    if blocked is not None:
        prompt = blocked.question.prompt.strip() if blocked.question else "Workflow path is blocked."
        return _attach_short_prompt(
            {
                "kind": "clarify",
                "parameter_id": None,
                "prompt": prompt,
            },
            task,
            planning,
            reader=reader,
        )

    from engine.navigation import composer_parameter_id, submittable_parameter_ids

    submittable = submittable_parameter_ids(task, planning)
    if submittable:
        param = composer_parameter_id(task, submittable[0])
        prompt: str | None = None
        if reader is not None:
            prompt = build_parameter_input_prompt(reader, task, param, planning=planning)
        if prompt is None:
            phase_questions = planning.get("phase_questions") or {}
            phase_missing = planning.get("phase_missing") or {}
            if isinstance(phase_questions, dict) and isinstance(phase_missing, dict):
                for phase, fields in phase_missing.items():
                    if not isinstance(fields, list) or param not in fields:
                        continue
                    questions = phase_questions.get(phase)
                    if isinstance(questions, dict):
                        candidate = questions.get(param)
                        if isinstance(candidate, str) and candidate.strip():
                            prompt = candidate.strip()
                            break
        return _attach_short_prompt(
            {
                "kind": "input",
                "parameter_id": param,
                "prompt": prompt,
            },
            task,
            planning,
            reader=reader,
        )

    current_phase = str(planning.get("current_phase") or "")
    if current_phase == "ready":
        return None

    phase_missing = planning.get("phase_missing") or {}
    if isinstance(phase_missing, dict) and current_phase:
        phase_fields = phase_missing.get(current_phase)
        if isinstance(phase_fields, list) and phase_fields:
            from engine.navigation import composer_parameter_id

            param = composer_parameter_id(task, str(phase_fields[0]))
            prompt = None
            if reader is not None:
                prompt = build_parameter_input_prompt(reader, task, param, planning=planning)
            return _attach_short_prompt(
                {
                    "kind": "input",
                    "parameter_id": param,
                    "prompt": prompt,
                },
                task,
                planning,
                reader=reader,
            )

    return _waiting_ask_from_phase_missing(planning)


def build_current_ask(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any] | None:
    """API-facing current ask for the desktop workflow composer."""
    from engine.planner.plan_selection import task_has_stored_engineering_plan
    from models.task import TaskStatus

    if task.status != TaskStatus.AWAITING_INPUT:
        return None

    if task_has_stored_engineering_plan(task):
        return _build_stored_plan_current_ask(task, planning, reader=reader)
    return _build_legacy_current_ask(task, planning, reader=reader)
