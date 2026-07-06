"""REST API server for the desktop application."""

from __future__ import annotations

import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from api.desktop_service import ApiError, DesktopApiService
from api.operation_tracker import get_operations_payload
from engine.inspection.operation_tracker import track_operation
from api.dev_studio.routes import (
    handle_dev_delete,
    handle_dev_get,
    handle_dev_post,
    handle_dev_put,
)
from api.dev_studio.service import DevStudioService
from api.error_catalog import enrich_api_error_payload
from api.json_encoding import dumps as json_dumps


def _api_error_payload(code: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": enrich_api_error_payload(code, message, details=details)}


def _api_error_from_exception(exc: ApiError) -> dict[str, Any]:
    return _api_error_payload(exc.code, exc.message, details=exc.details)


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json_dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    data = json.loads(raw.decode("utf-8"))
    return data if isinstance(data, dict) else {}


def _file_response(
    handler: BaseHTTPRequestHandler,
    *,
    file_path: Path,
    content_type: str,
    download_name: str,
) -> None:
    body = file_path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _parse_task_route(path: str) -> tuple[str, str | None] | None:
    prefix = "/api/v1/tasks/"
    if not path.startswith(prefix):
        return None
    remainder = path.removeprefix(prefix).strip("/")
    if not remainder:
        return None
    if "/" not in remainder:
        return remainder, None
    task_id, suffix = remainder.split("/", 1)
    return task_id, suffix


class ApiHandler(BaseHTTPRequestHandler):
    service: DesktopApiService
    dev_studio: DevStudioService | None = None
    backend_instance_id: str = ""

    def log_message(self, format: str, *args: object) -> None:
        return

    def handle_one_request(self) -> None:
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ""
                self.request_version = ""
                self.command = ""
                self.send_error(414)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not self.parse_request():
                return
            mname = "do_" + self.command
            if not hasattr(self, mname):
                self.send_error(501, f"Unsupported method ({self.command!r})")
                return
            path = urlparse(self.path).path.rstrip("/") or "/"
            skip_tracking = self.command == "OPTIONS" or path == "/health"
            if skip_tracking:
                getattr(self, mname)()
            else:
                with track_operation(
                    f"{self.command} {path}",
                    category="http",
                    path=path,
                    method=self.command,
                ):
                    getattr(self, mname)()
            self.wfile.flush()
        except ConnectionResetError:
            self.close_connection = True

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        try:
            if path == "/health":
                _json_response(
                    self,
                    200,
                    {"status": "ok", "instance_id": type(self).backend_instance_id},
                )
                return

            if path == "/api/v1/workflows":
                _json_response(self, 200, {"workflows": self.service.list_workflows()})
                return

            if path == "/api/v1/graph/neighbors":
                node_id = str(query.get("nodeId", query.get("node_id", [""]))[0] or "")
                depth = int(query.get("depth", ["1"])[0] or "1")
                if not node_id:
                    raise ApiError("invalid_request", "nodeId is required", status=400)
                _json_response(self, 200, self.service.get_graph_neighbors(node_id, depth=depth))
                return

            if path == "/api/v1/projects":
                _json_response(self, 200, {"projects": self.service.list_projects()})
                return

            if path.startswith("/api/v1/projects/"):
                project_id = path.removeprefix("/api/v1/projects/").strip("/")
                _json_response(self, 200, self.service.get_project(project_id))
                return

            if path == "/api/v1/tasks":
                session_id = query.get("session_id", [None])[0]
                _json_response(self, 200, self.service.list_tasks(session_id))
                return

            if path == "/api/v1/recent-tasks":
                _json_response(self, 200, self.service.list_recent_tasks_global())
                return

            if path == "/api/v1/chat/messages":
                session_id = query.get("session_id", [None])[0]
                task_id = query.get("task_id", [None])[0]
                resolved_task_id = str(task_id) if task_id else None
                _json_response(
                    self,
                    200,
                    self.service.list_chat_messages(session_id, task_id=resolved_task_id),
                )
                return

            if path.startswith("/api/v1/materials/"):
                material_remainder = path.removeprefix("/api/v1/materials/").strip("/")
                if material_remainder == "search":
                    search_query = str(query.get("q", [""])[0] or "")
                    _json_response(self, 200, self.service.search_materials(search_query))
                    return
                if material_remainder == "warm":
                    _json_response(self, 200, self.service.warm_material_catalog())
                    return
                if material_remainder:
                    _json_response(self, 200, self.service.get_material_detail(material_remainder))
                    return

            if path == "/api/v1/standards/browse":
                standard = query.get("standard", ["asme_b31.3"])[0]
                _json_response(self, 200, self.service.get_standards_browse(standard))
                return

            if path.startswith("/api/v1/standards/nodes/"):
                remainder = path.removeprefix("/api/v1/standards/nodes/").strip("/")
                if not remainder:
                    raise ApiError("invalid_request", "node_id is required", status=400)
                if "/subsections/" in remainder:
                    node_id, subsection_id = remainder.split("/subsections/", 1)
                    node_id = node_id.strip("/")
                    subsection_id = subsection_id.strip("/")
                    if not node_id or not subsection_id:
                        raise ApiError(
                            "invalid_request",
                            "node_id and subsection_id are required",
                            status=400,
                        )
                    _json_response(
                        self,
                        200,
                        self.service.get_standards_node_subsection(node_id, subsection_id),
                    )
                    return
                _json_response(self, 200, self.service.get_standards_node(remainder))
                return

            if path == "/api/v1/dev/operations":
                _json_response(self, 200, get_operations_payload())
                return

            if path.startswith("/api/v1/dev/"):
                payload = handle_dev_get(path, query, self.dev_studio)
                _json_response(self, 200, payload)
                return

            if path.startswith("/api/v1/standards/tables/"):
                table_id = path.removeprefix("/api/v1/standards/tables/").strip("/")
                if not table_id:
                    raise ApiError("invalid_request", "table_id is required", status=400)
                _json_response(self, 200, self.service.get_standards_table(table_id))
                return

            task_route = _parse_task_route(path)
            if task_route:
                task_id, suffix = task_route
                session_id = query.get("session_id", [None])[0]

                if suffix == "reports/preview":
                    preview_format = str(query.get("format", ["html"])[0] or "html")
                    _json_response(
                        self,
                        200,
                        self.service.preview_task_report(
                            task_id,
                            preview_format=preview_format,
                            session_id=session_id,
                        ),
                    )
                    return

                if suffix == "reports/download":
                    download_format = str(query.get("format", ["html"])[0] or "html")
                    file_path, content_type = self.service.download_task_report(
                        task_id,
                        download_format=download_format,
                        session_id=session_id,
                    )
                    _file_response(
                        self,
                        file_path=file_path,
                        content_type=content_type,
                        download_name=file_path.name,
                    )
                    return

                if suffix == "reports":
                    _json_response(self, 200, self.service.get_task_report(task_id, session_id))
                    return

                if suffix == "continuation-suggestions":
                    _json_response(
                        self,
                        200,
                        self.service.get_task_continuation_suggestions(task_id, session_id),
                    )
                    return

                if suffix == "workflow-state":
                    _json_response(
                        self,
                        200,
                        self.service.get_workflow_state(task_id, session_id),
                    )
                    return

                if suffix == "inspection":
                    _json_response(
                        self,
                        200,
                        self.service.get_inspection(task_id, session_id),
                    )
                    return

                if suffix == "inspection/integrity":
                    _json_response(
                        self,
                        200,
                        self.service.run_inspection_integrity(session_id),
                    )
                    return

                if suffix is None:
                    _json_response(self, 200, self.service.get_task(task_id, session_id))
                    return

                if suffix.startswith("inputs/") and suffix.endswith("/edit-impact"):
                    parameter = suffix.removeprefix("inputs/").removesuffix("/edit-impact")
                    _json_response(
                        self,
                        200,
                        self.service.preview_parameter_edit(
                            task_id,
                            parameter,
                            session_id=session_id,
                        ),
                    )
                    return

            _json_response(
                self,
                404,
                _api_error_payload("not_found", f"No route for {path}"),
            )
        except ApiError as exc:
            _json_response(self, exc.status, _api_error_from_exception(exc))
        except Exception as exc:  # noqa: BLE001 — surface as API error for desktop client
            _json_response(
                self,
                500,
                _api_error_payload("internal_error", str(exc)),
            )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        session_id = query.get("session_id", [None])[0]

        try:
            if path.startswith("/api/v1/dev/"):
                status, payload = handle_dev_post(path, query, _read_json_body(self), self.dev_studio)
                _json_response(self, status, payload)
                return

            if path == "/api/v1/tasks":
                body = _read_json_body(self)
                workflow_id = str(body.get("workflow_id") or "")
                if not workflow_id:
                    raise ApiError("invalid_request", "workflow_id is required", status=400)
                _json_response(self, 201, self.service.create_task(workflow_id, session_id))
                return

            if path == "/api/v1/projects":
                body = _read_json_body(self)
                name = str(body.get("name") or "")
                _json_response(self, 201, self.service.create_project(name))
                return

            if path.startswith("/api/v1/projects/") and path.endswith("/activate"):
                project_id = path.removeprefix("/api/v1/projects/").removesuffix("/activate").strip("/")
                _json_response(self, 200, self.service.activate_project(project_id))
                return

            if path.startswith("/api/v1/tasks/") and path.endswith("/inputs"):
                task_id = path.removeprefix("/api/v1/tasks/").removesuffix("/inputs").strip("/")
                body = _read_json_body(self)
                parameter = str(body.get("parameter") or "")
                if not parameter:
                    raise ApiError("invalid_request", "parameter is required", status=400)
                _json_response(
                    self,
                    200,
                    self.service.submit_input(
                        task_id,
                        parameter=parameter,
                        value=body.get("value"),
                        unit=body.get("unit"),
                        session_id=session_id,
                    ),
                )
                return

            if path.startswith("/api/v1/tasks/") and path.endswith("/activate"):
                task_id = path.removeprefix("/api/v1/tasks/").removesuffix("/activate").strip("/")
                _json_response(self, 200, self.service.activate_task(task_id, session_id))
                return

            task_route = _parse_task_route(path)
            if task_route:
                task_id, suffix = task_route
                if suffix == "inspection/breakpoint":
                    body = _read_json_body(self)
                    _json_response(
                        self,
                        200,
                        self.service.set_inspection_breakpoint(
                            task_id,
                            session_id=session_id,
                            paused=bool(body.get("paused")),
                            step=bool(body.get("step")),
                        ),
                    )
                    return

                if suffix and suffix.startswith("inputs/") and suffix.endswith("/edit"):
                    parameter = suffix.removeprefix("inputs/").removesuffix("/edit")
                    if not parameter:
                        raise ApiError("invalid_request", "parameter is required", status=400)
                    _json_response(
                        self,
                        200,
                        self.service.begin_parameter_edit(
                            task_id,
                            parameter,
                            session_id=session_id,
                        ),
                    )
                    return

                if suffix == "reports":
                    body = _read_json_body(self)
                    report_format = str(body.get("format") or "html")
                    with_ai = bool(body.get("with_ai"))
                    draft = bool(body.get("draft"))
                    _json_response(
                        self,
                        201,
                        self.service.generate_task_report(
                            task_id,
                            report_format=report_format,
                            with_ai=with_ai,
                            draft=draft,
                            session_id=session_id,
                        ),
                    )
                    return

            if path == "/api/v1/chat/messages":
                body = _read_json_body(self)
                message = str(body.get("message") or "")
                task_id = body.get("task_id")
                display_message = body.get("display_message")
                mode = body.get("mode")
                resolved_task_id = str(task_id) if task_id else None
                resolved_display_message = (
                    str(display_message).strip() if display_message else None
                )
                resolved_mode = str(mode).strip() if mode else None
                _json_response(
                    self,
                    200,
                    self.service.post_chat_message(
                        message,
                        display_message=resolved_display_message,
                        task_id=resolved_task_id,
                        mode=resolved_mode,
                        session_id=session_id,
                    ),
                )
                return

            _json_response(
                self,
                404,
                _api_error_payload("not_found", f"No route for {path}"),
            )
        except ApiError as exc:
            _json_response(self, exc.status, _api_error_from_exception(exc))
        except Exception as exc:  # noqa: BLE001
            _json_response(
                self,
                500,
                _api_error_payload("internal_error", str(exc)),
            )

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        try:
            if path.startswith("/api/v1/dev/"):
                payload = handle_dev_put(path, query, _read_json_body(self), self.dev_studio)
                _json_response(self, 200, payload)
                return

            _json_response(
                self,
                404,
                _api_error_payload("not_found", f"No route for {path}"),
            )
        except ApiError as exc:
            _json_response(self, exc.status, _api_error_from_exception(exc))
        except Exception as exc:  # noqa: BLE001
            _json_response(
                self,
                500,
                _api_error_payload("internal_error", str(exc)),
            )

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        session_id = query.get("session_id", [None])[0]

        try:
            if path.startswith("/api/v1/projects/"):
                project_id = path.removeprefix("/api/v1/projects/").strip("/")
                if project_id and "/" not in project_id:
                    body = _read_json_body(self)
                    name = str(body.get("name") or "")
                    _json_response(self, 200, self.service.rename_project(project_id, name))
                    return

            task_route = _parse_task_route(path)
            if task_route:
                task_id, suffix = task_route
                if suffix is None:
                    body = _read_json_body(self)
                    name = str(body.get("name") or "")
                    _json_response(self, 200, self.service.rename_task(task_id, name, session_id))
                    return

            _json_response(
                self,
                404,
                _api_error_payload("not_found", f"No route for {path}"),
            )
        except ApiError as exc:
            _json_response(self, exc.status, _api_error_from_exception(exc))
        except Exception as exc:  # noqa: BLE001
            _json_response(
                self,
                500,
                _api_error_payload("internal_error", str(exc)),
            )

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        session_id = query.get("session_id", [None])[0]

        try:
            if path.startswith("/api/v1/dev/"):
                payload = handle_dev_delete(path, query, self.dev_studio)
                _json_response(self, 200, payload)
                return

            if path.startswith("/api/v1/projects/"):
                project_id = path.removeprefix("/api/v1/projects/").strip("/")
                if project_id and "/" not in project_id:
                    _json_response(self, 200, self.service.delete_project(project_id))
                    return

            task_route = _parse_task_route(path)
            if task_route:
                task_id, suffix = task_route
                if suffix is None:
                    _json_response(self, 200, self.service.delete_task(task_id, session_id))
                    return

            if path == "/api/v1/chat/messages":
                task_id = query.get("task_id", [None])[0]
                resolved_task_id = str(task_id) if task_id else None
                _json_response(
                    self,
                    200,
                    self.service.clear_chat_messages(session_id, task_id=resolved_task_id),
                )
                return

            _json_response(
                self,
                404,
                _api_error_payload("not_found", f"No route for {path}"),
            )
        except ApiError as exc:
            _json_response(self, exc.status, _api_error_from_exception(exc))
        except Exception as exc:  # noqa: BLE001
            _json_response(
                self,
                500,
                _api_error_payload("internal_error", str(exc)),
            )


def create_handler(
    service: DesktopApiService,
    *,
    dev_studio: DevStudioService | None = None,
    backend_instance_id: str = "",
) -> type[ApiHandler]:
    return type(
        "BoundApiHandler",
        (ApiHandler,),
        {
            "service": service,
            "dev_studio": dev_studio,
            "backend_instance_id": backend_instance_id,
        },
    )


def _build_dev_studio(service: DesktopApiService) -> DevStudioService | None:
    from api.dev_studio.routes import dev_studio_enabled

    if not dev_studio_enabled():
        return None
    return DevStudioService(
        standards_root=service.config.standards_root,
        on_pack_changed=lambda _pack: service.invalidate_standards_cache(),
    )


def main() -> None:
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    project_root = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent))
    instance_id = os.environ.get("BACKEND_INSTANCE_ID") or str(uuid.uuid4())
    service = DesktopApiService.from_project_root(project_root)
    dev_studio = _build_dev_studio(service)
    handler = create_handler(service, dev_studio=dev_studio, backend_instance_id=instance_id)
    # #region agent log
    import time as _time
    from engine.graph import display_emitter as _display_emitter

    with open("debug-12f291.log", "a", encoding="utf-8") as _f:
        _f.write(
            json.dumps(
                {
                    "sessionId": "12f291",
                    "hypothesisId": "F",
                    "location": "server.py:main",
                    "message": "backend startup",
                    "data": {
                        "instance_id": instance_id,
                        "display_emitter": _display_emitter.__file__,
                        "has_resolve_require_binding": hasattr(
                            _display_emitter, "resolve_require_binding"
                        ),
                    },
                    "timestamp": int(_time.time() * 1000),
                }
            )
            + "\n"
        )
    # #endregion
    server = HTTPServer((host, port), handler)
    print(f"API server listening on http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
