"""Resolve standard pack paths under grouped standards/ layout."""

from __future__ import annotations

from pathlib import Path

STANDARD_GROUPS: tuple[str, ...] = ("asme", "api")


def normalize_standard_slug(standard: str) -> str:
    """Normalize config or user standard names to a slug (e.g. ASME_B31.3 -> asme_b31.3)."""
    text = standard.strip().replace("\\", "/")
    if "/" in text:
        return text.lower()
    return text.replace("-", "_").lower()


def is_standard_pack(path: Path) -> bool:
    """Return True when path looks like a standards pack root."""
    if not path.is_dir():
        return False
    markers = ("nodes", "roots", "tables", "index.md")
    return any((path / marker).exists() for marker in markers)


def resolve_standard_pack(standards_root: Path, standard: str) -> Path:
    """
    Resolve a standards pack directory.

    Supports:
    - Grouped layout: standards/asme/asme_b31.3, standards/api/api_570
    - Legacy flat layout: standards/asme_b31.3
    - Explicit relative path: asme/asme_b31.3
    """
    root = standards_root.resolve()
    text = normalize_standard_slug(standard)

    if "/" in text:
        candidate = root / text
        if is_standard_pack(candidate):
            return candidate
        raise FileNotFoundError(f"Standard pack not found: {standard} (resolved {candidate})")

    slug = text

    for group in STANDARD_GROUPS:
        grouped = root / group / slug
        if is_standard_pack(grouped):
            return grouped

    for path in sorted(root.glob(f"*/{slug}")):
        if is_standard_pack(path):
            return path

    direct = root / slug
    if is_standard_pack(direct):
        return direct

    raise FileNotFoundError(f"Standard pack not found under {root}: {standard}")


def list_standard_packs(standards_root: Path) -> list[tuple[str, Path]]:
    """Return (slug, path) for each discovered standards pack."""
    root = standards_root.resolve()
    found: dict[str, Path] = {}

    for group in STANDARD_GROUPS:
        group_dir = root / group
        if not group_dir.is_dir():
            continue
        for path in sorted(group_dir.iterdir()):
            if path.is_dir() and is_standard_pack(path):
                found[path.name] = path

    for path in sorted(root.iterdir()):
        if path.is_dir() and path.name not in STANDARD_GROUPS and is_standard_pack(path):
            found.setdefault(path.name, path)

    return sorted(found.items())
