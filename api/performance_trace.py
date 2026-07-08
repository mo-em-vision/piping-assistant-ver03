"""Developer performance trace API helpers."""

from __future__ import annotations

from typing import Any

from api.desktop_service import ApiError
from engine.inspection.dev_guard import inspection_enabled
from engine.inspection.performance_trace import MAX_RECENT_TRACES, recent_traces_snapshot


def require_performance_tracing_enabled() -> None:
    if not inspection_enabled():
        raise ApiError(
            "not_found",
            "Developer performance tracing is not enabled",
            status=404,
        )


def get_performance_traces_payload(*, limit: int = MAX_RECENT_TRACES) -> dict[str, Any]:
    require_performance_tracing_enabled()
    return recent_traces_snapshot(limit=limit)
