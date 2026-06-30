"""Entry point: python -m dev.graph_explorer"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from dev.graph_explorer.server import create_app


def main() -> None:
    project_root = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
    host = os.environ.get("GRAPH_EXPLORER_HOST", "127.0.0.1")
    port = int(os.environ.get("GRAPH_EXPLORER_PORT", "8765"))

    # #region agent log
    try:
        import json
        import time
        _log_path = project_root / "debug-b5dce6.log"
        with _log_path.open("a", encoding="utf-8") as _f:
            _f.write(json.dumps({
                "sessionId": "b5dce6",
                "hypothesisId": "B",
                "location": "__main__.py:main",
                "message": "python dev server starting",
                "data": {"project_root": str(project_root), "host": host, "port": port},
                "timestamp": int(time.time() * 1000),
                "runId": os.environ.get("DEBUG_RUN_ID", "pre-fix"),
            }) + "\n")
    except Exception:
        pass
    # #endregion

    app = create_app(project_root)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
