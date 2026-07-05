"""Entry point: python -m dev.graph_explorer"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import uvicorn

from dev.graph_explorer.server import create_app


def main() -> None:
    # Avoid noisy ConnectionResetError callbacks when clients disconnect on Windows.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    project_root = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
    host = os.environ.get("GRAPH_EXPLORER_HOST", "127.0.0.1")
    port = int(os.environ.get("GRAPH_EXPLORER_PORT", "8765"))

    app = create_app(project_root)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
