"""Map standards pack slugs to canonical AUTH-* authority node IDs."""

from __future__ import annotations

# standard slug → (authority_id, edition, runtime role in AuthorityContext)
STANDARD_PRIMARY_AUTHORITY: dict[str, tuple[str, str, str]] = {
    "asme_b31.3": ("AUTH-ASME-B31.3", "2024", "primary_design_code"),
    "asme-b31.3": ("AUTH-ASME-B31.3", "2024", "primary_design_code"),
}


def standard_primary_authority(standard: str) -> tuple[str, str | None, str]:
    """Return canonical AUTH id, edition, and role for a standards pack slug."""
    if standard in STANDARD_PRIMARY_AUTHORITY:
        authority_id, edition, role = STANDARD_PRIMARY_AUTHORITY[standard]
        return authority_id, edition, role
    slug = standard.replace("_", "-").upper()
    return f"AUTH-{slug}", None, "primary_design_code"


def known_authority_ids() -> frozenset[str]:
    return frozenset(item[0] for item in STANDARD_PRIMARY_AUTHORITY.values())
