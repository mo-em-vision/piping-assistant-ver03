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
    app = create_app(project_root)

    print(f"Graph explorer API listening on http://{host}:{port}", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
