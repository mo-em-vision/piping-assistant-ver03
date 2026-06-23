"""REST API server for the desktop application."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from api.desktop_service import ApiError, DesktopApiService
from api.error_catalog import enrich_api_error_payload


def _api_error_payload(code: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": enrich_api_error_payload(code, message, details=details)}


def _api_error_from_exception(exc: ApiError) -> dict[str, Any]:
    return _api_error_payload(exc.code, exc.message, details=exc.details)


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        try:
            if path == "/health":
                _json_response(self, 200, {"status": "ok"})
                return

            if path == "/api/v1/workflows":
                _json_response(self, 200, {"workflows": self.service.list_workflows()})
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

            if path == "/api/v1/chat/messages":
                session_id = query.get("session_id", [None])[0]
                _json_response(self, 200, self.service.list_chat_messages(session_id))
                return

            if path == "/api/v1/materials/search":
                search_query = str(query.get("q", [""])[0] or "")
                _json_response(self, 200, self.service.search_materials(search_query))
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

                if suffix is None:
                    _json_response(self, 200, self.service.get_task(task_id, session_id))
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
                resolved_task_id = str(task_id) if task_id else None
                _json_response(
                    self,
                    200,
                    self.service.post_chat_message(
                        message,
                        task_id=resolved_task_id,
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


def create_handler(service: DesktopApiService) -> type[ApiHandler]:
    return type("BoundApiHandler", (ApiHandler,), {"service": service})


def main() -> None:
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    project_root = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent))
    service = DesktopApiService.from_project_root(project_root)
    handler = create_handler(service)
    server = HTTPServer((host, port), handler)
    print(f"API server listening on http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
