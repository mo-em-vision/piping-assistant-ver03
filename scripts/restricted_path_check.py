"""Protected-path gate: load manifest, parse task context, validate changed paths."""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "config" / "restricted_paths.yaml"

VALID_CATEGORIES = frozenset(
    {
        "constitutional",
        "contract",
        "agent_rule",
        "architecture_authoritative",
        "architecture_explanatory",
        "explanatory",
        "generated",
    }
)

ALWAYS_BLOCKED_IN_IMPL = frozenset(
    {
        "constitutional",
        "contract",
        "agent_rule",
        "architecture_authoritative",
        "generated",
    }
)

SYNC_ELIGIBLE = frozenset({"explanatory", "architecture_explanatory"})

AUTHORITATIVE = ALWAYS_BLOCKED_IN_IMPL - {"generated"}

CODE_PATH_PREFIXES = (
    "api/",
    "engine/",
    "tests/",
    "desktopApp/",
    "models/",
    "storage/",
    "ai/",
    "scripts/",
    "workflows/",
    "dev/",
    "config/",
    "contracts/",
)

NORMATIVE_RE = re.compile(
    r"\b(must|shall|required|forbidden)\b",
    re.IGNORECASE,
)

LIST_SECTION_RE = re.compile(
    r"^(?P<key>Mode|Allowed files|Implementation impact report)\s*:\s*(?P<value>.*)$",
    re.IGNORECASE | re.MULTILINE,
)

BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class TaskContext:
    mode: str = "implementation"
    allowed_files: frozenset[str] = field(default_factory=frozenset)
    impact_report: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Manifest:
    globs: tuple[tuple[str, str], ...]
    entries: dict[str, str]

    def classify(self, path: str) -> str | None:
        normalized = normalize_path(path)
        if normalized in self.entries:
            return self.entries[normalized]
        matches: list[tuple[int, str]] = []
        for pattern, category in self.globs:
            if _path_matches_glob(normalized, pattern):
                matches.append((len(pattern), category))
        if not matches:
            return None
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]


@dataclass(frozen=True)
class Violation:
    message: str
    paths: tuple[str, ...]
    categories: tuple[str, ...] = ()
    detail: str = ""

    def format_agent_message(self) -> str:
        parts = [self.message]
        if self.paths:
            parts.append(f"Paths: {', '.join(self.paths)}")
        if self.categories:
            parts.append(f"Categories: {', '.join(self.categories)}")
        if self.detail:
            parts.append(self.detail)
        parts.append("See docs/protected-files/registry.md and config/restricted_paths.yaml.")
        return " ".join(parts)


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _path_matches_glob(path: str, pattern: str) -> bool:
    path_posix = PurePosixPath(path)
    pattern_posix = pattern.replace("\\", "/")
    if path_posix.match(pattern_posix):
        return True
    return fnmatch.fnmatch(path, pattern_posix)


def load_manifest(path: Path | None = None) -> Manifest:
    manifest_path = path or MANIFEST_PATH
    if not manifest_path.is_file():
        raise FileNotFoundError(f"restricted path manifest not found: {manifest_path}")
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping")

    globs: list[tuple[str, str]] = []
    for item in data.get("globs") or []:
        if not isinstance(item, dict):
            raise ValueError("glob entry must be a mapping")
        pattern = normalize_path(str(item.get("pattern") or ""))
        category = str(item.get("category") or "").strip()
        if not pattern or not category:
            raise ValueError("glob entry requires pattern and category")
        if category not in VALID_CATEGORIES:
            raise ValueError(f"unknown category in glob: {category}")
        globs.append((pattern, category))

    entries: dict[str, str] = {}
    for item in data.get("entries") or []:
        if not isinstance(item, dict):
            raise ValueError("manifest entry must be a mapping")
        entry_path = normalize_path(str(item.get("path") or ""))
        category = str(item.get("category") or "").strip()
        if not entry_path or not category:
            raise ValueError("manifest entry requires path and category")
        if category not in VALID_CATEGORIES:
            raise ValueError(f"unknown category in entry: {category}")
        entries[entry_path] = category

    return Manifest(globs=tuple(globs), entries=entries)


def classify_path(path: str, manifest: Manifest) -> str | None:
    return manifest.classify(path)


def parse_task_context(user_message: str) -> TaskContext:
    if not user_message:
        return TaskContext()

    mode = "implementation"
    allowed: list[str] = []
    impact: list[str] = []

    lines = user_message.splitlines()
    current_section: str | None = None
    for line in lines:
        header = LIST_SECTION_RE.match(line)
        if header:
            key = header.group("key").strip().lower()
            value = header.group("value").strip()
            if key == "mode":
                mode = value.lower().replace(" ", "-")
                current_section = None
            elif key == "allowed files":
                current_section = "allowed"
                if value:
                    allowed.append(normalize_path(value))
            elif key == "implementation impact report":
                current_section = "impact"
                if value:
                    impact.append(normalize_path(value))
            continue

        bullet = BULLET_RE.match(line)
        if bullet and current_section:
            path = normalize_path(bullet.group(1))
            if current_section == "allowed":
                allowed.append(path)
            elif current_section == "impact":
                impact.append(path)

    if mode == "documentation-edit":
        return TaskContext(
            mode=mode,
            allowed_files=frozenset(allowed),
            impact_report=frozenset(impact),
        )
    return TaskContext(mode="implementation", impact_report=frozenset(impact))


def is_code_path(path: str) -> bool:
    normalized = normalize_path(path)
    return normalized.startswith(CODE_PATH_PREFIXES)


def get_changed_paths(repo_root: Path | None = None) -> list[str]:
    root = repo_root or ROOT
    paths: set[str] = set()

    def _run_git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "git command failed")
        return result.stdout

    for line in _run_git("diff", "--name-only", "HEAD").splitlines():
        if line.strip():
            paths.add(normalize_path(line.strip()))
    for line in _run_git("diff", "--cached", "--name-only").splitlines():
        if line.strip():
            paths.add(normalize_path(line.strip()))
    for line in _run_git("ls-files", "--others", "--exclude-standard").splitlines():
        if line.strip():
            paths.add(normalize_path(line.strip()))
    return sorted(paths)


def get_path_diff(repo_root: Path, path: str) -> str:
    normalized = normalize_path(path)
    result = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "HEAD", "--", normalized],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    staged = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--cached", "--", normalized],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout + staged.stdout


def check_normative_language(diff_text: str) -> bool:
    """Return True if diff adds normative language (violation)."""
    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:].lstrip()
        if not content or content.startswith(">"):
            continue
        if _normative_outside_quotes(content):
            return True
    return False


def _normative_outside_quotes(text: str) -> bool:
    stripped = _strip_quoted_regions(text)
    return bool(NORMATIVE_RE.search(stripped))


def _strip_quoted_regions(text: str) -> str:
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r'"[^"]*"', "", text)
    text = re.sub(r"'[^']*'", "", text)
    return text


def validate_changed_paths(
    changed_paths: list[str],
    context: TaskContext,
    manifest: Manifest,
    *,
    repo_root: Path | None = None,
    path_diffs: dict[str, str] | None = None,
) -> tuple[bool, list[Violation]]:
    root = repo_root or ROOT
    violations: list[Violation] = []
    path_diffs = path_diffs or {}

    classified: dict[str, str | None] = {
        path: classify_path(path, manifest) for path in changed_paths
    }

    if context.mode == "documentation-edit":
        for path in changed_paths:
            category = classified[path]
            if category == "generated":
                violations.append(
                    Violation(
                        message="GENERATED FILE — MANUAL EDIT BLOCKED",
                        paths=(path,),
                        categories=(category,),
                    )
                )
            elif path not in context.allowed_files:
                if category:
                    violations.append(
                        Violation(
                            message="RESTRICTED-FILE EDIT NOT AUTHORIZED",
                            paths=(path,),
                            categories=(category or "",),
                            detail="Path is not in Allowed files for documentation-edit mode.",
                        )
                    )
                elif is_code_path(path):
                    violations.append(
                        Violation(
                            message="MIXED RESTRICTED-FILE AND IMPLEMENTATION TASK — BLOCKED",
                            paths=(path,),
                            detail="Code and tests are read-only in documentation-edit mode.",
                        )
                    )
        return (not violations, violations)

    # Implementation mode
    blocked_paths: list[str] = []
    blocked_categories: list[str] = []
    code_paths: list[str] = []

    for path in changed_paths:
        category = classified[path]
        if category in ALWAYS_BLOCKED_IN_IMPL:
            blocked_paths.append(path)
            blocked_categories.append(category or "")
        elif is_code_path(path) and category is None:
            code_paths.append(path)

    if blocked_paths and code_paths:
        violations.append(
            Violation(
                message="MIXED RESTRICTED-FILE AND IMPLEMENTATION TASK — BLOCKED",
                paths=tuple(blocked_paths + code_paths),
                categories=tuple(blocked_categories),
            )
        )
        return (False, violations)

    for path in changed_paths:
        category = classified[path]
        if category in ALWAYS_BLOCKED_IN_IMPL:
            if category == "generated":
                msg = "GENERATED FILE — MANUAL EDIT BLOCKED"
            else:
                msg = "RESTRICTED DOCUMENTATION PHASE REQUIRED — IMPLEMENTATION BLOCKED"
            violations.append(
                Violation(
                    message=msg,
                    paths=(path,),
                    categories=(category,),
                    detail="Use Mode: documentation-edit with Allowed files.",
                )
            )
            continue

        if category in SYNC_ELIGIBLE:
            if path not in context.impact_report:
                violations.append(
                    Violation(
                        message="EXPLANATORY SYNC VIOLATION — NOT IN IMPACT REPORT",
                        paths=(path,),
                        categories=(category,),
                        detail="List the path under Implementation impact report: in the user request.",
                    )
                )
                continue
            diff_text = path_diffs.get(path)
            if diff_text is None:
                try:
                    diff_text = get_path_diff(root, path)
                except RuntimeError:
                    diff_text = ""
            if check_normative_language(diff_text):
                violations.append(
                    Violation(
                        message="EXPLANATORY SYNC VIOLATION — NORMATIVE LANGUAGE",
                        paths=(path,),
                        categories=(category,),
                        detail="Added lines contain must/shall/required/forbidden outside quotes.",
                    )
                )

    return (not violations, violations)


def validate_repo(
    user_message: str,
    *,
    repo_root: Path | None = None,
    manifest_path: Path | None = None,
) -> tuple[bool, list[Violation]]:
    root = repo_root or ROOT
    manifest = load_manifest(manifest_path)
    context = parse_task_context(user_message)
    changed = get_changed_paths(root)
    if not changed:
        return (True, [])
    path_diffs = {path: get_path_diff(root, path) for path in changed}
    return validate_changed_paths(
        changed,
        context,
        manifest,
        repo_root=root,
        path_diffs=path_diffs,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate protected-path changes")
    parser.add_argument("--message-file", type=Path, help="File containing user message")
    parser.add_argument("--message", type=str, default="", help="User message text")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args(argv)

    if args.message_file:
        user_message = args.message_file.read_text(encoding="utf-8")
    else:
        user_message = args.message

    try:
        ok, violations = validate_repo(
            user_message,
            repo_root=args.repo_root,
            manifest_path=args.manifest,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2

    if ok:
        print("OK")
        return 0

    for violation in violations:
        print(violation.format_agent_message(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
