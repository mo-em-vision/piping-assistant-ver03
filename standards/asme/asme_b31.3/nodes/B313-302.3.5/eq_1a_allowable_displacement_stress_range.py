"""Eq. (1a) — S_A = f * (1.25*S_c + 0.25*S_h)."""

from __future__ import annotations


def compute(variables: dict[str, float]) -> tuple[str, float, str]:
    f = variables["f"]
    S_c = variables["S_c"]
    S_h = variables["S_h"]
    S_A = f * (1.25 * S_c + 0.25 * S_h)
    return "S_A", S_A, "Pa"
