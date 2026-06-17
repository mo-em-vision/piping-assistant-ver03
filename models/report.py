"""Report data and traceability structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ReportSection:
    node: str
    paragraph: str | None = None
    source_text: str | None = None
    decision: str | None = None
    formula: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TraceabilityEntry:
    node: str
    paragraph: str | None = None
    source_text: str | None = None
    decision: str | None = None
    formula: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportData:
    report_id: str
    title: str
    graph_version: str
    sections: list[ReportSection] = field(default_factory=list)
    traceability: list[TraceabilityEntry] = field(default_factory=list)


@dataclass(frozen=True)
class ReportStorage:
    report_data_path: str
    pdf_path: str | None = None
    html_path: str | None = None
