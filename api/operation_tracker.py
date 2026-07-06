"""Developer operation tracker API helpers."""

from __future__ import annotations

from typing import Any

from api.desktop_service import ApiError
from engine.inspection.dev_guard import inspection_enabled
from engine.inspection.operation_tracker import operations_snapshot


def require_operation_tracking_enabled() -> None:
    if not inspection_enabled():
        raise ApiError("not_found", "Developer operation tracking is not enabled", status=404)


def get_operations_payload() -> dict[str, Any]:
    require_operation_tracking_enabled()
    return operations_snapshot()
