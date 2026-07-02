"""Runtime Goal nodes — engineering objectives satisfied by Facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class GoalClass(str, Enum):
    CALCULATION = "calculation_goal"
    LOOKUP = "lookup_goal"
    VALIDATION = "validation_goal"
    SELECTION = "selection_goal"
    VERIFICATION = "verification_goal"
    REPORT = "report_goal"
    INPUT = "input_goal"
    DECISION = "decision_goal"
    EXPLANATION = "explanation_goal"


class SatisfactionStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    BLOCKED = "blocked"
    EXECUTING = "executing"
    SATISFIED = "satisfied"
    FAILED = "failed"
    DEFERRED = "deferred"
    SUPERSEDED = "superseded"


class GoalRuntimeStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    READY = "ready"
    EXECUTING = "executing"
    SATISFIED = "satisfied"
    FAILED = "failed"
    DEFERRED = "deferred"
    SUPERSEDED = "superseded"


@dataclass
class RequiredFactRef:
    parameter: str

    @staticmethod
    def from_value(value: Any) -> RequiredFactRef:
        if isinstance(value, RequiredFactRef):
            return value
        if isinstance(value, dict):
            param = value.get("parameter") or value.get("key") or ""
            return RequiredFactRef(parameter=str(param))
        return RequiredFactRef(parameter=str(value))


@dataclass
class RequiredOutput:
    parameter: str


@dataclass
class GoalSatisfaction:
    status: SatisfactionStatus = SatisfactionStatus.PENDING
    satisfied_by: str | None = None
    required_output: RequiredOutput | None = None
    validation_status: str | None = None


@dataclass
class GoalState:
    status: GoalRuntimeStatus = GoalRuntimeStatus.ACTIVE
    blocked_by: list[str] = field(default_factory=list)
    child_goals: list[str] = field(default_factory=list)
    parent_goal: str | None = None


@dataclass
class GoalProvenance:
    execution_context_id: str | None = None
    task_id: str | None = None
    project_id: str | None = None
    workflow_id: str | None = None
    created_from_user_intent: str | None = None
    created_by: str | None = None
    timestamp: str | None = None


@dataclass
class GoalQuestion:
    prompt: str
    reason: str | None = None
    expected_value_class: str | None = None


@dataclass
class GoalAuthority:
    references: list[str] = field(default_factory=list)


@dataclass
class Goal:
    id: str
    key: str
    name: str
    goal_class: GoalClass
    target_parameter: str
    satisfaction: GoalSatisfaction = field(default_factory=GoalSatisfaction)
    provenance: GoalProvenance = field(default_factory=GoalProvenance)
    state: GoalState = field(default_factory=GoalState)
    type: str = "goal"
    required_facts: list[RequiredFactRef] = field(default_factory=list)
    question: GoalQuestion | None = None
    authority: GoalAuthority | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    edges: list[dict[str, Any]] = field(default_factory=list)


def new_goal_id(prefix: str = "GOAL") -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_param(parameter: str) -> str:
    from engine.reference.param_resolver import resolve_parameter_id

    return resolve_parameter_id(parameter)


def _base_goal(
    *,
    key: str,
    name: str,
    goal_class: GoalClass,
    target_parameter: str,
    task_id: str,
    workflow_id: str | None = None,
    created_by: str = "planner",
    goal_id: str | None = None,
    parent_goal: str | None = None,
    required_facts: list[str] | None = None,
    phase: str | None = None,
    order: int | None = None,
) -> Goal:
    param_id = _resolve_param(target_parameter)
    refs = [RequiredFactRef(parameter=_resolve_param(p)) for p in (required_facts or [])]
    meta: dict[str, Any] = {}
    if phase:
        meta["phase"] = phase
    if order is not None:
        meta["order"] = order
    return Goal(
        id=goal_id or new_goal_id(),
        key=key,
        name=name,
        goal_class=goal_class,
        target_parameter=param_id,
        required_facts=refs,
        satisfaction=GoalSatisfaction(
            status=SatisfactionStatus.PENDING,
            required_output=RequiredOutput(parameter=param_id),
        ),
        provenance=GoalProvenance(
            task_id=task_id,
            workflow_id=workflow_id,
            created_by=created_by,
            timestamp=_utc_now_iso(),
        ),
        state=GoalState(parent_goal=parent_goal),
        metadata=meta,
    )


def input_goal(
    *,
    key: str,
    name: str,
    target_parameter: str,
    task_id: str,
    prompt: str,
    reason: str | None = None,
    workflow_id: str | None = None,
    parent_goal: str | None = None,
    phase: str | None = None,
    order: int | None = None,
) -> Goal:
    goal = _base_goal(
        key=key,
        name=name,
        goal_class=GoalClass.INPUT,
        target_parameter=target_parameter,
        task_id=task_id,
        workflow_id=workflow_id,
        parent_goal=parent_goal,
        phase=phase,
        order=order,
    )
    goal.question = GoalQuestion(prompt=prompt, reason=reason)
    return goal


def lookup_goal(
    *,
    key: str,
    name: str,
    target_parameter: str,
    task_id: str,
    required_facts: list[str],
    workflow_id: str | None = None,
    parent_goal: str | None = None,
    phase: str | None = None,
    order: int | None = None,
) -> Goal:
    return _base_goal(
        key=key,
        name=name,
        goal_class=GoalClass.LOOKUP,
        target_parameter=target_parameter,
        task_id=task_id,
        workflow_id=workflow_id,
        parent_goal=parent_goal,
        required_facts=required_facts,
        phase=phase,
        order=order,
    )


def calculation_goal(
    *,
    key: str,
    name: str,
    target_parameter: str,
    task_id: str,
    required_facts: list[str] | None = None,
    workflow_id: str | None = None,
    parent_goal: str | None = None,
    phase: str | None = None,
    order: int | None = None,
) -> Goal:
    return _base_goal(
        key=key,
        name=name,
        goal_class=GoalClass.CALCULATION,
        target_parameter=target_parameter,
        task_id=task_id,
        workflow_id=workflow_id,
        parent_goal=parent_goal,
        required_facts=required_facts or [],
        phase=phase,
        order=order,
    )


def selection_goal(
    *,
    key: str,
    name: str,
    target_parameter: str,
    task_id: str,
    prompt: str,
    reason: str | None = None,
    workflow_id: str | None = None,
    parent_goal: str | None = None,
    phase: str | None = None,
    order: int | None = None,
) -> Goal:
    goal = _base_goal(
        key=key,
        name=name,
        goal_class=GoalClass.SELECTION,
        target_parameter=target_parameter,
        task_id=task_id,
        workflow_id=workflow_id,
        parent_goal=parent_goal,
        phase=phase,
        order=order,
    )
    goal.question = GoalQuestion(prompt=prompt, reason=reason)
    return goal


def validation_goal(
    *,
    key: str,
    name: str,
    target_parameter: str,
    task_id: str,
    required_facts: list[str],
    workflow_id: str | None = None,
    parent_goal: str | None = None,
    authority_refs: list[str] | None = None,
    phase: str | None = None,
    order: int | None = None,
) -> Goal:
    goal = _base_goal(
        key=key,
        name=name,
        goal_class=GoalClass.VALIDATION,
        target_parameter=target_parameter,
        task_id=task_id,
        workflow_id=workflow_id,
        parent_goal=parent_goal,
        required_facts=required_facts,
        phase=phase,
        order=order,
    )
    if authority_refs:
        goal.authority = GoalAuthority(references=list(authority_refs))
    return goal


def goal_parameter_key(goal: Goal) -> str:
    """Runtime parameter key derived from target_parameter."""
    param = goal.target_parameter
    if param.startswith("PARAM-"):
        slug = param[len("PARAM-") :].replace("-", "_")
        return slug
    return param


def goal_to_dict(goal: Goal) -> dict[str, Any]:
    from dataclasses import asdict

    return asdict(goal)


def goal_from_dict(data: dict[str, Any]) -> Goal:
    satisfaction_data = data.get("satisfaction") or {}
    state_data = data.get("state") or {}
    provenance_data = data.get("provenance") or {}

    required_output = satisfaction_data.get("required_output")
    req_out = None
    if isinstance(required_output, dict) and required_output.get("parameter"):
        req_out = RequiredOutput(parameter=str(required_output["parameter"]))

    sat_status = satisfaction_data.get("status", SatisfactionStatus.PENDING.value)
    if isinstance(sat_status, SatisfactionStatus):
        ss = sat_status
    else:
        ss = SatisfactionStatus(str(sat_status))

    runtime_status = state_data.get("status", GoalRuntimeStatus.ACTIVE.value)
    if isinstance(runtime_status, GoalRuntimeStatus):
        rs = runtime_status
    else:
        rs = GoalRuntimeStatus(str(runtime_status))

    goal_class = data.get("goal_class", GoalClass.INPUT.value)
    if isinstance(goal_class, GoalClass):
        gc = goal_class
    else:
        gc = GoalClass(str(goal_class))

    refs = [
        RequiredFactRef.from_value(item)
        for item in (data.get("required_facts") or [])
    ]

    question = None
    q_data = data.get("question")
    if isinstance(q_data, dict) and q_data.get("prompt"):
        question = GoalQuestion(
            prompt=str(q_data["prompt"]),
            reason=q_data.get("reason"),
            expected_value_class=q_data.get("expected_value_class"),
        )

    authority = None
    a_data = data.get("authority")
    if isinstance(a_data, dict):
        authority = GoalAuthority(references=list(a_data.get("references") or []))

    return Goal(
        id=str(data["id"]),
        type=str(data.get("type", "goal")),
        key=str(data.get("key", "")),
        name=str(data.get("name", "")),
        goal_class=gc,
        target_parameter=str(data.get("target_parameter", "")),
        required_facts=refs,
        satisfaction=GoalSatisfaction(
            status=ss,
            satisfied_by=satisfaction_data.get("satisfied_by"),
            required_output=req_out,
            validation_status=satisfaction_data.get("validation_status"),
        ),
        provenance=GoalProvenance(
            execution_context_id=provenance_data.get("execution_context_id"),
            task_id=provenance_data.get("task_id"),
            project_id=provenance_data.get("project_id"),
            workflow_id=provenance_data.get("workflow_id"),
            created_from_user_intent=provenance_data.get("created_from_user_intent"),
            created_by=provenance_data.get("created_by"),
            timestamp=provenance_data.get("timestamp"),
        ),
        state=GoalState(
            status=rs,
            blocked_by=list(state_data.get("blocked_by") or []),
            child_goals=list(state_data.get("child_goals") or []),
            parent_goal=state_data.get("parent_goal"),
        ),
        question=question,
        authority=authority,
        metadata=dict(data.get("metadata") or {}),
        edges=list(data.get("edges") or []),
    )
