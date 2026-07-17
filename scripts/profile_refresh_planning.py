"""Profile sub-steps inside refresh_task_planning."""
from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback
from contextlib import contextmanager
from pathlib import Path

os.environ.setdefault("DEV_INSPECTION_ENABLED", "1")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.desktop_service import DesktopApiService  # noqa: E402
from api.workflow_bootstrap import refresh_task_planning  # noqa: E402
from config.loader import CLIConfig  # noqa: E402
from engine.reference.standards_reader import StandardsReader  # noqa: E402
from engine.state.state_manager import TaskStateManager  # noqa: E402


@contextmanager
def timed(label: str, timings: list[tuple[str, float]]):
    t0 = time.perf_counter()
    yield
    timings.append((label, (time.perf_counter() - t0) * 1000.0))


def _build_service() -> DesktopApiService:
    sessions_dir = Path(tempfile.mkdtemp(prefix="profile-planning-"))
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=sessions_dir,
        standards_root=ROOT / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def profile_refresh(task, reader: StandardsReader) -> list[tuple[str, float]]:
    from api.workflow_bootstrap import _finalize_planning_state
    from engine.planning.planning_refresh import refresh_task_planning_state

    timings: list[tuple[str, float]] = []
    t0 = time.perf_counter()
    ctx = refresh_task_planning_state(task, reader, propose_defaults=False)
    if ctx is not None:
        _finalize_planning_state(
            task,
            reader,
            workflow_id=ctx.workflow_id,
            root_slug=ctx.root_slug,
            preview=ctx.preview,
            graph=ctx.graph,
            engine=ctx.engine,
            active_nodes=ctx.active_nodes,
            uses_micro=ctx.uses_micro,
        )
    timings.append(("refresh_task_planning_total", (time.perf_counter() - t0) * 1000.0))
    return timings


def main() -> None:
    service = _build_service()
    project = service.create_project("Profile Planning")
    session_id = service.activate_project(project["id"])["session_id"]
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    submissions = [
        ("straight_pipe_section", True, "dimensionless"),
        ("pressure_loading", "internal_pressure", None),
    ]

    reader = StandardsReader(ROOT / "knowledge" / "standards", standard="asme_b31.3")
    manager = service._load_manager()

    for param, value, unit in submissions:
        state = service.submit_input(
            task_id,
            parameter=param,
            value=value,
            unit=unit,
            session_id=session_id,
        )
        task = manager.get_task(task_id)
        print(f"\n=== after submit {param!r} ===")
        timings = profile_refresh(task, reader)
        for label, ms in timings:
            print(f"  {label:40} {ms:8.1f} ms")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
