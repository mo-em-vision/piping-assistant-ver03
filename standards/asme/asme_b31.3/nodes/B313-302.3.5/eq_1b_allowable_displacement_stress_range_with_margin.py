"""Eq. (1b) — S_A = f * (1.25*(S_c + S_h) - S_L)."""

from __future__ import annotations


def compute(variables: dict[str, float]) -> tuple[str, float, str]:
    f = variables["f"]
    S_c = variables["S_c"]
    S_h = variables["S_h"]
    S_L = variables["S_L"]
    S_A = f * (1.25 * (S_c + S_h) - S_L)
    return "S_A", S_A, "Pa"
