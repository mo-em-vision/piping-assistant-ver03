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
class ReportInputEntry:
    input_id: str
    name: str
    original_value: Any
    original_unit: str
    calculation_value: Any | None = None
    calculation_unit: str | None = None


@dataclass
class ReportTraversalStep:
    node_id: str
    title: str | None = None


@dataclass
class ReportDecision:
    node: str
    reason: str
    condition: str | None = None
    result: str | None = None


@dataclass
class ReportWarning:
    message: str
    level: str = "warning"


@dataclass
class ReportOverride:
    rule: str
    original_rule: str
    user_decision: str
    effect: str


@dataclass
class ReportVersionInfo:
    report_version: str = "1.0"
    graph_version: str = ""
    node_versions: dict[str, str] = field(default_factory=dict)
    created_date: str = ""
    task_id: str = ""


@dataclass
class ReportData:
    report_id: str
    title: str
    graph_version: str
    sections: list[ReportSection] = field(default_factory=list)
    traceability: list[TraceabilityEntry] = field(default_factory=list)
    task_id: str = ""
    workflow: str = ""
    status: str = "INCOMPLETE"
    version_info: ReportVersionInfo | None = None
    user_request: str = ""
    standards: list[str] = field(default_factory=list)
    input_entries: list[ReportInputEntry] = field(default_factory=list)
    traversal: list[ReportTraversalStep] = field(default_factory=list)
    decisions: list[ReportDecision] = field(default_factory=list)
    report_warnings: list[ReportWarning] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    overrides: list[ReportOverride] = field(default_factory=list)
    conclusion: str = ""
    missing_inputs: list[str] = field(default_factory=list)
    formula_display: str | None = None


@dataclass(frozen=True)
class ReportStorage:
    report_data_path: str
    pdf_path: str | None = None
    html_path: str | None = None
    markdown_path: str | None = None
    json_path: str | None = None
