"""Starlette REST + WebSocket server for the developer graph explorer."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from config.loader import CLIConfig
from dev.graph_explorer.explorer_config import apply_desktop_user_data_env, resolve_session_id
from dev.graph_explorer.adapter import GraphExplorerAdapter
from dev.graph_explorer.analysis import analyze_graph
from dev.graph_explorer.delta import compute_delta
from dev.graph_explorer.serializer import GraphSnapshotDto
from dev.graph_explorer.watcher import GraphWatcher, auto_rebuild_enabled


class GraphExplorerService:
    def __init__(self, adapter: GraphExplorerAdapter) -> None:
        self.adapter = adapter
        self._snapshot: GraphSnapshotDto | None = None
        self._lock = asyncio.Lock()
        self._subscribers: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._preferred_task_id: str | None = None
        self._preferred_session_id: str | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def resolve_task_id(self, task_id: str | None) -> str | None:
        if task_id:
            self._preferred_task_id = task_id
        return self._preferred_task_id

    def resolve_session_id(self, session_id: str | None) -> str:
        if session_id:
            self._preferred_session_id = session_id
        return self._preferred_session_id or self.adapter.session_id

    async def get_snapshot(
        self,
        task_id: str | None = None,
        session_id: str | None = None,
    ) -> GraphSnapshotDto:
        task_id = self.resolve_task_id(task_id)
        session_id = self.resolve_session_id(session_id)
        async with self._lock:
            self.adapter.reload()
            snapshot = self.adapter.get_snapshot(task_id=task_id, session_id=session_id)
            self._snapshot = snapshot
            return snapshot

    def _refresh_and_broadcast(self) -> None:
        self.adapter.reload()
        session_id = self.resolve_session_id(None)
        snapshot = self.adapter.get_snapshot(
            task_id=self._preferred_task_id,
            session_id=session_id,
        )
        previous = self._snapshot
        self._snapshot = snapshot
        delta = compute_delta(previous, snapshot)
        if self._loop is not None and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(snapshot, delta), self._loop)

    async def _broadcast(self, snapshot: GraphSnapshotDto, delta: Any) -> None:
        if delta is None:
            message: dict[str, Any] = {"type": "snapshot", **snapshot.to_dict()}
        else:
            message = delta.to_dict()

        dead: set[WebSocket] = set()
        for websocket in self._subscribers:
            try:
                await websocket.send_json(message)
            except Exception:
                dead.add(websocket)
        self._subscribers -= dead

    async def subscribe(self, websocket: WebSocket) -> None:
        task_id = websocket.query_params.get("task")
        session_id = websocket.query_params.get("session_id")
        await websocket.accept()
        self._subscribers.add(websocket)
        snapshot = await self.get_snapshot(task_id, session_id)
        await websocket.send_json({"type": "snapshot", **snapshot.to_dict()})

    def unsubscribe(self, websocket: WebSocket) -> None:
        self._subscribers.discard(websocket)


def create_app(project_root: Path | None = None) -> Starlette:
    root = project_root or Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
    apply_desktop_user_data_env(root)
    config = CLIConfig.load(project_root=root)
    requested_session = os.environ.get("GRAPH_EXPLORER_SESSION", "auto")
    session_id = resolve_session_id(config, requested_session)
    adapter = GraphExplorerAdapter(config, session_id)
    service = GraphExplorerService(adapter)

    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def graph_context(request: Request) -> JSONResponse:
        task_id = request.query_params.get("task")
        session_id = request.query_params.get("session_id")
        resolved_task = service.resolve_task_id(task_id)
        resolved_session = service.resolve_session_id(session_id)
        return JSONResponse(
            service.adapter.get_context(task_id=resolved_task, session_id=resolved_session).to_dict(),
        )

    async def graph_snapshot(request: Request) -> JSONResponse:
        task_id = request.query_params.get("task")
        session_id = request.query_params.get("session_id")
        revision = request.query_params.get("revision")
        snapshot = await service.get_snapshot(task_id, session_id)
        if revision and snapshot.revision == revision:
            return JSONResponse({"unchanged": True, "revision": revision})
        return JSONResponse(snapshot.to_dict())

    async def graph_node(request: Request) -> JSONResponse:
        node_id = request.path_params["node_id"]
        task_id = request.query_params.get("task")
        session_id = request.query_params.get("session_id")
        detail = service.adapter.get_node(
            node_id,
            task_id=service.resolve_task_id(task_id),
            session_id=service.resolve_session_id(session_id),
        )
        if detail is None:
            return JSONResponse({"error": "Node not found"}, status_code=404)
        return JSONResponse(detail.to_dict())

    async def graph_analysis(request: Request) -> JSONResponse:
        task_id = request.query_params.get("task")
        session_id = request.query_params.get("session_id")
        snapshot = await service.get_snapshot(task_id, session_id)
        report = analyze_graph(snapshot.nodes, snapshot.edges)
        return JSONResponse(report.to_dict())

    async def graph_search(request: Request) -> JSONResponse:
        query = request.query_params.get("q", "")
        task_id = request.query_params.get("task")
        session_id = request.query_params.get("session_id")
        matches = service.adapter.search_nodes(
            query,
            task_id=service.resolve_task_id(task_id),
            session_id=service.resolve_session_id(session_id),
        )
        return JSONResponse({"results": [node.to_dict() for node in matches]})

    async def websocket_graph(websocket: WebSocket) -> None:
        await service.subscribe(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            service.unsubscribe(websocket)

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        on_startup(_app)
        try:
            yield
        finally:
            on_shutdown(_app)

    routes = [
        Route("/health", health),
        Route("/api/graph/context", graph_context),
        Route("/api/graph/snapshot", graph_snapshot),
        Route("/api/graph/nodes/{node_id}", graph_node),
        Route("/api/graph/analysis", graph_analysis),
        Route("/api/graph/search", graph_search),
        WebSocketRoute("/ws/graph", websocket_graph),
    ]

    app = Starlette(routes=routes, lifespan=lifespan)
    app.state.service = service
    app.state.config = config
    app.state.project_root = root
    app.state.session_id = session_id
    return app


def on_startup(app: Starlette) -> None:
    service: GraphExplorerService = app.state.service
    config: CLIConfig = app.state.config
    root: Path = app.state.project_root
    session_id: str = app.state.session_id

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    service.set_loop(loop)

    def trigger_refresh() -> None:
        service._refresh_and_broadcast()

    watcher = GraphWatcher(
        standards_root=config.standards_root,
        sessions_dir=config.sessions_dir,
        session_id=session_id,
        on_change=trigger_refresh,
        auto_rebuild=auto_rebuild_enabled(),
        project_root=root,
    )
    watcher.start()
    app.state.watcher = watcher
    service._refresh_and_broadcast()


def on_shutdown(app: Starlette) -> None:
    watcher = getattr(app.state, "watcher", None)
    if watcher is not None:
        watcher.stop()
