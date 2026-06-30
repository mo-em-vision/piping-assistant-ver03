"""Eq. (1c) — f = min(6.0*N^(-0.2), f_m)."""

from __future__ import annotations


def compute(variables: dict[str, float]) -> tuple[str, float, str]:
    N = variables["N"]
    f_m = variables["f_m"]
    f = min(6.0 * (N ** -0.2), f_m)
    return "f", f, "dimensionless"
