"""Canonical equation display trace produced by execution/report layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

EquationDisplayStatus = Literal["evaluated", "blocked", "failed"]
EquationDisplayLatexSource = Literal[
    "metadata_display_latex",
    "metadata_display_text",
    "sympy_generated",
]
EquationDisplaySourceType = Literal[
    "user_input",
    "table_lookup",
    "equation_output",
    "default",
    "system",
]


@dataclass(frozen=True)
class EquationDisplayQuantity:
    symbol: str
    value: float
    unit: str
    display_value: str


@dataclass(frozen=True)
class EquationDisplayInput:
    symbol: str
    parameter_id: str | None
    label: str
    value: float | None
    unit: str | None
    display_value: str | None
    source_type: EquationDisplaySourceType | None
    source_ref: str | None


@dataclass(frozen=True)
class EquationDisplayTrace:
    equation_id: str
    node_id: str
    paragraph: str | None
    title: str | None
    symbolic_latex: str
    substituted_latex: str | None
    result_latex: str | None
    latex_source: EquationDisplayLatexSource
    result: EquationDisplayQuantity | None
    inputs: tuple[EquationDisplayInput, ...]
    intermediate_values: tuple[EquationDisplayQuantity, ...]
    status: EquationDisplayStatus

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EquationDisplayTrace:
        result_payload = payload.get("result")
        result = None
        if isinstance(result_payload, dict):
            result = EquationDisplayQuantity(**result_payload)

        inputs: list[EquationDisplayInput] = []
        for item in payload.get("inputs") or []:
            if isinstance(item, dict):
                inputs.append(EquationDisplayInput(**item))

        intermediates: list[EquationDisplayQuantity] = []
        for item in payload.get("intermediate_values") or []:
            if isinstance(item, dict):
                intermediates.append(EquationDisplayQuantity(**item))

        return cls(
            equation_id=str(payload.get("equation_id") or ""),
            node_id=str(payload.get("node_id") or ""),
            paragraph=payload.get("paragraph"),
            title=payload.get("title"),
            symbolic_latex=str(payload.get("symbolic_latex") or ""),
            substituted_latex=payload.get("substituted_latex"),
            result_latex=payload.get("result_latex"),
            latex_source=payload.get("latex_source") or "metadata_display_text",
            result=result,
            inputs=tuple(inputs),
            intermediate_values=tuple(intermediates),
            status=payload.get("status") or "blocked",
        )
