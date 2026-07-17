"""Layer import boundary contract tests."""



from __future__ import annotations



import ast

from pathlib import Path



import pytest



_REPO_ROOT = Path(__file__).resolve().parents[3]



_NAVIGATION_SCAN_TARGETS: tuple[tuple[str, tuple[str, ...]], ...] = (

    (

        "engine/planner",

        (

            "api.workflow_timeline",

            "api.workflow_display",

            "api.workflow_bootstrap",

            "api.workflow_execution",

        ),

    ),

    (

        "engine/state",

        (

            "api.workflow_timeline",

            "api.workflow_bootstrap",

            "api.workflow_display",

            "api.workflow_execution",

        ),

    ),

    (

        "engine/navigation",

        (

            "api.workflow_timeline",

            "api.workflow_display",

            "api.workflow_bootstrap",

            "api.workflow_execution",

        ),

    ),

)



_GRAPH_SCAN_TARGETS: tuple[tuple[str, tuple[str, ...]], ...] = (

    ("engine/graph", ("api",)),

)





def _module_imports(path: Path) -> set[str]:

    tree = ast.parse(path.read_text(encoding="utf-8"))

    imports: set[str] = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                imports.add(alias.name)

        elif isinstance(node, ast.ImportFrom):

            if node.module:

                imports.add(node.module)

    return imports





def _violations_for_root(relative_root: str, forbidden: tuple[str, ...]) -> list[str]:

    root = _REPO_ROOT / relative_root

    if not root.exists():

        return []

    violations: list[str] = []

    for path in sorted(root.rglob("*.py")):

        imports = _module_imports(path)

        rel = path.relative_to(_REPO_ROOT).as_posix()

        for module_name in imports:

            for rule in forbidden:

                if module_name == rule or module_name.startswith(f"{rule}."):

                    violations.append(f"{rel}: {module_name}")

    return violations





def test_engine_navigation_layers_do_not_import_api_navigation() -> None:

    violations: list[str] = []

    for relative_root, forbidden in _NAVIGATION_SCAN_TARGETS:

        violations.extend(_violations_for_root(relative_root, forbidden))

    assert violations == [], "Forbidden API navigation imports:\n" + "\n".join(violations)





def test_engine_graph_layers_do_not_import_api() -> None:

    violations: list[str] = []

    for relative_root, forbidden in _GRAPH_SCAN_TARGETS:

        violations.extend(_violations_for_root(relative_root, forbidden))

    assert violations == [], "Forbidden API imports in engine/graph:\n" + "\n".join(violations)

