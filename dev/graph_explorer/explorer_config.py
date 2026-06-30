"""Graph explorer configuration helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from config.loader import CLIConfig
from storage.project_repository import ProjectRepository
from storage.project_session_store import get_database_for_config


def resolve_desktop_user_data(project_root: Path) -> Path | None:
    """Match Electron desktop app user-data when DESKTOP_USER_DATA is unset."""
    explicit = os.environ.get("DESKTOP_USER_DATA") or os.environ.get("GRAPH_EXPLORER_USER_DATA")
    if explicit:
        return Path(explicit).resolve()

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidate = Path(appdata) / "engineering-desktop-app"
            if (candidate / "data" / "desktop.db").is_file():
                return candidate

    return None


def apply_desktop_user_data_env(project_root: Path) -> Path | None:
    user_data = resolve_desktop_user_data(project_root)
    if user_data is not None:
        os.environ.setdefault("DESKTOP_USER_DATA", str(user_data))
    return user_data


def resolve_session_id(config: CLIConfig, requested: str | None) -> str:
    """Pick project/session id; auto-select active desktop project when requested is auto."""
    if requested and requested not in {"", "auto"}:
        return requested

    database = get_database_for_config(config.sessions_dir)
    projects = ProjectRepository(database).list_projects()
    for project in projects:
        if project.get("active_task_id"):
            return str(project["id"])
    for project in projects:
        if int(project.get("task_count") or 0) > 0:
            return str(project["id"])
    return requested or "default"


def debug_log(hypothesis_id: str, message: str, data: dict) -> None:
    # #region agent log
    try:
        import json
        import time

        project_root = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
        log_path = project_root / "debug-b5dce6.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "sessionId": "b5dce6",
                        "hypothesisId": hypothesis_id,
                        "location": "dev.graph_explorer.explorer_config",
                        "message": message,
                        "data": data,
                        "timestamp": int(time.time() * 1000),
                        "runId": os.environ.get("DEBUG_RUN_ID", "pre-fix"),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
