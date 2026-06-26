"""Desktop API helpers for engineering report generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.reports.formatters import is_valid_pdf_file
from engine.reports.report_generator import ReportGenerator
from engine.state.state_manager import TaskNotFoundError, TaskStateManager
from models.report import ReportData, ReportStorage
from storage.project_session_store import ProjectSessionStore


SUPPORTED_FORMATS = frozenset({"pdf", "html", "markdown", "md", "json"})
PREVIEW_FORMATS = frozenset({"html", "markdown", "md"})
DOWNLOAD_FORMATS = frozenset({"pdf", "html", "markdown", "md", "json"})

_FORMAT_GROUPS: dict[str, tuple[str, ...]] = {
    "pdf": ("pdf", "html", "markdown", "json"),
    "html": ("html", "markdown", "json", "pdf"),
    "markdown": ("markdown", "json"),
    "md": ("markdown", "json"),
    "json": ("json",),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_info(path: str | None) -> dict[str, Any]:
    if not path:
        return {"available": False, "filename": None, "updated_at": None, "path": None}
    file_path = Path(path)
    if not file_path.exists():
        return {"available": False, "filename": file_path.name, "updated_at": None, "path": str(file_path)}
    if file_path.suffix.lower() == ".pdf" and not is_valid_pdf_file(file_path):
        return {"available": False, "filename": file_path.name, "updated_at": None, "path": str(file_path)}
    updated = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc).isoformat()
    return {
        "available": True,
        "filename": file_path.name,
        "updated_at": updated,
        "path": str(file_path),
    }


def _report_files(storage: ReportStorage | None, output_dir: Path, task_id: str) -> dict[str, dict[str, Any]]:
    if storage:
        return {
            "markdown": _file_info(storage.markdown_path),
            "html": _file_info(storage.html_path),
            "pdf": _file_info(storage.pdf_path),
            "json": _file_info(storage.json_path),
            "report_data": _file_info(storage.report_data_path),
        }

    base = output_dir / task_id
    candidates = {
        "markdown": base.with_suffix(".md"),
        "html": base.with_suffix(".html"),
        "pdf": base.with_suffix(".pdf"),
        "json": base.with_suffix(".json"),
        "report_data": output_dir / f"{task_id}_report_data.json",
    }
    return {key: _file_info(str(path) if path.exists() else None) for key, path in candidates.items()}


def _serialize_report_summary(report: ReportData, files: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "task_id": report.task_id,
        "title": report.title,
        "status": report.status,
        "conclusion": report.conclusion,
        "missing_inputs": list(report.missing_inputs),
        "formula_display": report.formula_display,
        "files": files,
        "generated": any(item.get("available") for item in files.values()),
    }


def get_report_status(
    store: ProjectSessionStore,
    config: Any,
    manager: TaskStateManager,
    task_id: str,
) -> dict[str, Any]:
    task = manager.get_task(task_id)
    generator = ReportGenerator(
        config.standards_root,
        standard=config.default_standard.lower(),
    )
    report = generator.build(task_id, manager)
    output_dir = store.session_path / "reports"
    files = _report_files(None, output_dir, task_id)
    summary = _serialize_report_summary(report, files)
    summary["workflow_id"] = str(task.outputs.get("workflow") or report.workflow or "")
    summary["task_status"] = task.status.value
    return summary


def generate_task_report(
    store: ProjectSessionStore,
    config: Any,
    manager: TaskStateManager,
    task_id: str,
    *,
    report_format: str = "html",
    with_ai: bool = False,
    draft: bool = False,
) -> dict[str, Any]:
    normalized = report_format.lower()
    if normalized not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported report format: {report_format}")

    generator = ReportGenerator(
        config.standards_root,
        standard=config.default_standard.lower(),
    )
    report = generator.build(task_id, manager)
    output_dir = store.session_path / "reports"

    if draft:
        draft_path = generator.save_draft(report, output_dir)
        files = _report_files(None, output_dir, task_id)
        payload = _serialize_report_summary(report, files)
        payload["draft_path"] = str(draft_path)
        payload["generation_status"] = "draft_saved"
        _save_report_artifact(store, task_id, payload)
        return payload

    storage = generator.generate(
        report,
        output_dir,
        formats=_FORMAT_GROUPS[normalized],
        use_ai=with_ai,
    )
    files = _report_files(storage, output_dir, task_id)
    payload = _serialize_report_summary(report, files)
    payload["generation_status"] = "ready"
    payload["with_ai"] = with_ai
    payload["selected_format"] = normalized
    _save_report_artifact(store, task_id, payload)
    return payload


def get_report_preview(
    store: ProjectSessionStore,
    config: Any,
    manager: TaskStateManager,
    task_id: str,
    *,
    preview_format: str = "html",
) -> dict[str, Any]:
    normalized = preview_format.lower()
    if normalized == "md":
        normalized = "markdown"
    if normalized not in PREVIEW_FORMATS:
        raise ValueError(f"Unsupported preview format: {preview_format}")

    output_dir = store.session_path / "reports"
    extension = ".html" if normalized == "html" else ".md"
    file_path = output_dir / f"{task_id}{extension}"

    if not file_path.exists():
        generate_task_report(store, config, manager, task_id, report_format=normalized)

    content = file_path.read_text(encoding="utf-8")
    return {
        "task_id": task_id,
        "format": normalized,
        "content": content,
        "filename": file_path.name,
    }


def resolve_report_download(
    store: ProjectSessionStore,
    task_id: str,
    *,
    download_format: str,
) -> tuple[Path, str]:
    normalized = download_format.lower()
    if normalized == "md":
        normalized = "markdown"
    if normalized not in DOWNLOAD_FORMATS:
        raise ValueError(f"Unsupported download format: {download_format}")

    output_dir = store.session_path / "reports"
    extension_map = {
        "pdf": ".pdf",
        "html": ".html",
        "markdown": ".md",
        "json": ".json",
    }
    file_path = output_dir / f"{task_id}{extension_map[normalized]}"
    if not file_path.exists():
        raise FileNotFoundError(f"Report file not found: {file_path.name}")

    mime_map = {
        "pdf": "application/pdf",
        "html": "text/html; charset=utf-8",
        "markdown": "text/markdown; charset=utf-8",
        "json": "application/json",
    }
    return file_path, mime_map[normalized]


def _save_report_artifact(store: ProjectSessionStore, task_id: str, payload: dict[str, Any]) -> None:
    store.repository.save_task_artifact(
        store.session_id,
        task_id,
        kind="report",
        payload_json=json.dumps(payload),
    )
