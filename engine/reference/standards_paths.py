"""Resolve standard pack paths under grouped standards/ layout."""

from __future__ import annotations

from pathlib import Path

STANDARD_GROUPS: tuple[str, ...] = ("asme", "astm")

# Material slugs that resolve to the consolidated knowledge/standards/astm/ pack.
ASTM_MATERIAL_SLUGS: frozenset[str] = frozenset(
    {"astm_a53", "astm_a106", "astm_a312", "a_105"}
)


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


def is_consolidated_astm_pack(standards_root: Path) -> bool:
    """True when ASTM material nodes live in a single pack at standards/astm/."""
    astm_pack = standards_root.resolve() / "astm"
    return (astm_pack / "nodes").is_dir() and is_standard_pack(astm_pack)


def resolve_astm_pack(standards_root: Path) -> Path:
    pack = standards_root.resolve() / "astm"
    if is_standard_pack(pack):
        return pack
    raise FileNotFoundError(f"Consolidated ASTM pack not found: {pack}")


def resolve_global_tasks_db(standards_root: Path) -> Path:
    """Return the compiled global workflows SQLite database path."""
    return standards_root.resolve() / "workflows.db"


def resolve_pack_workflows_dir(pack_root: Path) -> Path:
    """Return workflow YAML folder for a pack."""
    pack_root = pack_root.resolve()
    workflows = pack_root / "nodes" / "workflows"
    if workflows.is_dir():
        return workflows
    return resolve_pack_tasks_dir(pack_root)


def resolve_pack_tasks_dir(pack_root: Path) -> Path:
    """Return legacy pack task entry folder (`tasks/` or `roots/`)."""
    pack_root = pack_root.resolve()
    tasks = pack_root / "tasks"
    if tasks.is_dir():
        return tasks
    return pack_root / "roots"


def resolve_standard_pack(standards_root: Path, standard: str) -> Path:
    """
    Resolve a standards pack directory.

    Supports:
    - Grouped layout: standards/asme/asme_b31.3, standards/astm
    - Consolidated ASTM materials: astm_a106 -> standards/astm
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

    if slug in ASTM_MATERIAL_SLUGS and is_consolidated_astm_pack(root):
        return resolve_astm_pack(root)

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
        if is_standard_pack(group_dir):
            found[group_dir.name] = group_dir
            continue
        for path in sorted(group_dir.iterdir()):
            if path.is_dir() and is_standard_pack(path):
                found[path.name] = path

    for path in sorted(root.iterdir()):
        if path.is_dir() and path.name not in STANDARD_GROUPS and is_standard_pack(path):
            found.setdefault(path.name, path)

    return sorted(found.items())
