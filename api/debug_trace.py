"""Session debug logging (temporary instrumentation)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_LOG_PATH = Path(__file__).resolve().parents[1] / "debug-2495e2.log"
_SESSION_ID = "2495e2"


def agent_debug_log(
    location: str,
    message: str,
    data: dict[str, Any],
    *,
    hypothesis_id: str,
    run_id: str = "pre-fix",
) -> None:
    entry = {
        "sessionId": _SESSION_ID,
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": message,
        "data": data,
        "hypothesisId": hypothesis_id,
        "runId": run_id,
    }
    try:
        with _LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass
