"""Filesystem watcher for graph explorer live updates."""

from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class GraphChangeHandler(FileSystemEventHandler):
    def __init__(
        self,
        on_change: Callable[[], None],
        *,
        standards_root: Path,
        auto_rebuild: bool,
        project_root: Path,
    ) -> None:
        super().__init__()
        self._on_change = on_change
        self._standards_root = standards_root
        self._auto_rebuild = auto_rebuild
        self._project_root = project_root
        self._debounce_timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._should_ignore(path):
            return
        if path.suffix in {".yaml", ".yml", ".md"} and self._auto_rebuild:
            self._maybe_rebuild_pack(path)
        self._schedule_notify()

    def _should_ignore(self, path: Path) -> bool:
        name = path.name
        if name.endswith(".pyc") or name.startswith("."):
            return True
        return False

    def _maybe_rebuild_pack(self, path: Path) -> None:
        try:
            relative = path.relative_to(self._standards_root)
        except ValueError:
            return
        parts = relative.parts
        if len(parts) < 2:
            return
        pack_root = self._standards_root / parts[0] / parts[1]
        if not (pack_root / "nodes").is_dir():
            return
        try:
            if str(self._project_root) not in sys.path:
                sys.path.insert(0, str(self._project_root))
            from scripts.build_graph_db import build_pack_graph_db

            build_pack_graph_db(pack_root)
        except Exception:
            return

    def _schedule_notify(self) -> None:
        with self._lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(0.35, self._on_change)
            self._debounce_timer.daemon = True
            self._debounce_timer.start()


class GraphWatcher:
    def __init__(
        self,
        *,
        standards_root: Path,
        sessions_dir: Path,
        session_id: str,
        on_change: Callable[[], None],
        auto_rebuild: bool,
        project_root: Path,
    ) -> None:
        self._observer = Observer()
        handler = GraphChangeHandler(
            on_change,
            standards_root=standards_root,
            auto_rebuild=auto_rebuild,
            project_root=project_root,
        )
        self._observer.schedule(handler, str(standards_root), recursive=True)
        session_path = sessions_dir / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        self._observer.schedule(handler, str(session_path), recursive=False)
        tasks_file = session_path / "tasks.json"
        if tasks_file.is_file():
            self._observer.schedule(handler, str(tasks_file), recursive=False)

    def start(self) -> None:
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=2)


def auto_rebuild_enabled() -> bool:
    return os.environ.get("GRAPH_EXPLORER_AUTO_REBUILD", "0").strip() in {"1", "true", "yes"}
