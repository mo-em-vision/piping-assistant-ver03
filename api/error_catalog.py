"""User-facing error recovery guidance for the desktop API."""

from __future__ import annotations

from typing import Any

_ERROR_GUIDANCE: dict[str, dict[str, str]] = {
    "invalid_input": {
        "title": "Invalid engineering input",
        "possible_reason": "The submitted value failed backend validation or is outside allowed limits.",
        "next_action": "Correct the highlighted parameter and save again.",
    },
    "invalid_request": {
        "title": "Request could not be processed",
        "possible_reason": "A required field was missing or formatted incorrectly.",
        "next_action": "Review the form and try again.",
    },
    "task_not_found": {
        "title": "Task not found",
        "possible_reason": "The task may have been removed or belongs to another project.",
        "next_action": "Reload the workspace or select a different task.",
    },
    "project_not_found": {
        "title": "Project not found",
        "possible_reason": "The selected project is no longer available in local storage.",
        "next_action": "Choose another project or create a new one.",
    },
    "workflow_unavailable": {
        "title": "Workflow unavailable",
        "possible_reason": "This engineering workflow is not enabled in the current release.",
        "next_action": "Select an available workflow from the left panel.",
    },
    "report_not_found": {
        "title": "Report not available",
        "possible_reason": "The requested report file has not been generated yet.",
        "next_action": "Generate the report, then retry the download or preview.",
    },
    "calculation_failed": {
        "title": "Calculation failed",
        "possible_reason": "The engineering workflow stopped because inputs or assumptions became invalid.",
        "next_action": "Review warnings, update inputs, and restart the affected calculation.",
    },
    "backend_unavailable": {
        "title": "Backend unavailable",
        "possible_reason": "The local engineering API is not running or cannot be reached.",
        "next_action": "Retry the connection. If the problem continues, restart the desktop application.",
    },
    "api_unreachable": {
        "title": "Cannot reach API",
        "possible_reason": "The desktop app could not complete a health check against the backend.",
        "next_action": "Retry after confirming the Python API process is running.",
    },
    "internal_error": {
        "title": "Unexpected server error",
        "possible_reason": "The backend encountered an unhandled failure while processing the request.",
        "next_action": "Retry the action. If it keeps failing, check backend logs for details.",
    },
    "not_found": {
        "title": "Resource not found",
        "possible_reason": "The requested API route or resource does not exist.",
        "next_action": "Reload the workspace and try again.",
    },
    "unknown_error": {
        "title": "Something went wrong",
        "possible_reason": "An unexpected error occurred in the desktop client or API.",
        "next_action": "Retry the action or reload the workspace.",
    },
}


def build_recovery(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, str]:
    guidance = _ERROR_GUIDANCE.get(code, _ERROR_GUIDANCE["unknown_error"])
    affected_parameter = ""
    affected_task = ""
    if details:
        affected_parameter = str(details.get("parameter") or "")
        affected_task = str(details.get("task_id") or "")

    next_action = guidance["next_action"]
    if code == "invalid_input" and affected_parameter:
        next_action = f"Update `{affected_parameter}` and submit again."

    return {
        "title": guidance["title"],
        "what_happened": message,
        "possible_reason": guidance["possible_reason"],
        "next_action": next_action,
        "affected_parameter": affected_parameter,
        "affected_task": affected_task,
    }


def enrich_api_error_payload(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details or {},
        "recovery": build_recovery(code, message, details=details),
    }
