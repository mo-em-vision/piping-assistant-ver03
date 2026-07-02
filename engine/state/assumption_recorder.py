"""Record runtime assumptions on ExecutionContext."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engine.reference.param_resolver import resolve_parameter_id
from models.execution_context import Assumption, ExecutionContext, new_assumption_id
from models.task import Task


_EXPANSION_ASSUMPTIONS = frozenset({"straight_pipe_section", "thin_wall"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record_assumption(
    ctx: ExecutionContext,
    *,
    parameter: str,
    value: Any,
    confirmed_by: str = "user",
    affects_expansion: bool = False,
) -> Assumption:
    param_id = resolve_parameter_id(parameter)
    for existing in ctx.assumptions:
        if existing.parameter == param_id:
            existing.value = value
            existing.confirmed_by = confirmed_by
            existing.affects_expansion = affects_expansion
            existing.timestamp = _utc_now_iso()
            return existing
    assumption = Assumption(
        id=new_assumption_id(),
        parameter=param_id,
        value=value,
        confirmed_by=confirmed_by,
        affects_expansion=affects_expansion,
        timestamp=_utc_now_iso(),
    )
    ctx.assumptions.append(assumption)
    return assumption


def record_assumption_for_task(
    task: Task,
    *,
    parameter: str,
    value: Any,
    confirmed_by: str = "user",
) -> Assumption:
    affects = parameter in _EXPANSION_ASSUMPTIONS
    return record_assumption(
        task.execution_context,
        parameter=parameter,
        value=value,
        confirmed_by=confirmed_by,
        affects_expansion=affects,
    )


def record_assumption_from_fact(task: Task, key: str, value: Any) -> Assumption | None:
    if key not in _EXPANSION_ASSUMPTIONS:
        return None
    return record_assumption_for_task(task, parameter=key, value=value)
