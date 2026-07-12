# Protected files registry

**Owner approval required before any edit to files listed or matched here.**

Cursor agents must read this registry at the start of each session (via [`.cursor/rules/protected-documentation.mdc`](../../.cursor/rules/protected-documentation.mdc)) and treat matched paths as **non-editable without explicit user approval**.

## Protected glob patterns

| Pattern | Purpose |
| --- | --- |
| `docs/**` | Architecture, process, templates, desktopApp specs, tests docs, standards notes |
| `docs/protected-files/**` | This registry and protected-files policy (includes this file) |
| `audits/**` | Standalone audit / review notes at repository root |
| `knowledge/standards/**` | Engineering standards knowledge packs: paragraph/equation/table/lookup nodes, pack metadata, section indexes, and compiled SQLite caches under each standard |

`docs/audit/**` is included under `docs/**`.

`docs/standards/**` (documentation about standards layout) is included under `docs/**`.

## Edit policy

1. **Do not edit** any matched file unless the user **explicitly** asks to change that file (or a specific section) in the current conversation.
2. **Propose first** — if a change seems necessary, describe it and wait for approval before editing.
3. **User-requested edits** are allowed when the user names the file or clearly requests updates to protected content.
4. **Do not** fix typos, reformat, or sync protected files opportunistically while implementing unrelated code.
5. **Disclosure before any protected edit** — when proposing or performing an approved edit, state explicitly:
   - **Which file(s)** will change (full repo-relative paths)
   - **What** will change (sections, fields, or behavior affected)
   - **Why** the edit is needed (user request, standards correction, registry maintenance, etc.)

## Required reading (before significant work)

Read the relevant sections — not necessarily every file on every turn:

| When | Read first |
| --- | --- |
| Any non-trivial feature or architecture change | [`docs/rules.md`](../rules.md) |
| Feature planning | [`docs/process/plan_review_gate.md`](../process/plan_review_gate.md), [`docs/core/3. component_responsibilities.md`](../core/3.%20component_responsibilities.md) |
| Desktop / API work | Matching files under [`docs/desktopApp/`](../desktopApp/) |
| Node / workflow authoring | [`audits/contracts/nodes/`](../audits/contracts/nodes/00-START-HERE.md) and [`audits/contracts/runtime/`](../audits/contracts/runtime/) |
| Standards pack / node content | Relevant files under `knowledge/standards/` (read-only unless user approves edits) |
| Audit or “what exists today” questions | [`docs/audit/INDEX.md`](../audit/INDEX.md) |

Do not use protected files as a substitute for reading implementation code; use both.

---

## `knowledge/standards/` (glob — do not enumerate as permission to edit unlisted files)

All files under `knowledge/standards/**` are protected, including but not limited to:

- `knowledge/standards/README.md`
- `knowledge/standards/workflows.db`, `standards_config.db`
- `knowledge/standards/asme/**` (ASME B31.3, B36.10 packs, nodes, `*.db` caches)
- `knowledge/standards/astm/**` (ASTM packs, nodes, `*.db` caches)

Prefer `python scripts/build_graph_db.py` and related build scripts over hand-editing compiled `*_graph.db` files unless the user explicitly approves.

---

## `docs/` — root files

- `docs/Feature creation prompt template.md`
- `docs/developer_inspection_framework.md`
- `docs/rules.md`

## `docs/architecture/`

- `docs/architecture/Constitution.md`
- `docs/architecture/ontology architecture.md`
- `docs/architecture/Principles.md`

## `docs/audit/`

- `docs/audit/ARCHITECTURE_AUDIT.md`
- `docs/audit/DUPLICATES.md`
- `docs/audit/EXECUTION_TRACES.md`
- `docs/audit/INDEX.md`
- `docs/audit/MAINTENANCE.md`
- `docs/audit/PROGRESS.md`

## `docs/core/`

- `docs/core/1. Architecture.md`
- `docs/core/2. system_overview.md`
- `docs/core/3. component_responsibilities.md`
- `docs/core/4. data_models.md`
- `docs/core/5. workflow_design.md`
- `docs/core/6. ai_agent_design.md`
- `docs/core/7. node_structure_design.md`
- `docs/core/8. Node Template.md`
- `docs/core/10. report_generation_design.md`
- `docs/core/11. planner_layer_design.md`
- `docs/core/12. Cursor Build Sequence (SAFE STEP-BY-STEP PLAN).md`
- `docs/core/13. execution_layer_design.md`
- `docs/core/14. graph_engine_design.md`
- `docs/core/15. validation_layer.md`

## `docs/desktopApp/`

- `docs/desktopApp/00_desktop_app_vision.md`
- `docs/desktopApp/01_technology_stack.md`
- `docs/desktopApp/02_application_structure.md`
- `docs/desktopApp/03_ui_design_system.md`
- `docs/desktopApp/04_ai_interaction_design.md`
- `docs/desktopApp/05_backend_ui_contract.md`
- `docs/desktopApp/06_component_architecture.md`
- `docs/desktopApp/07_frontend_data_models.md`
- `docs/desktopApp/08_frontend_development_workflow.md`
- `docs/desktopApp/09_desktop_app_folder_structure.md`
- `docs/desktopApp/10_frontend_api_integration.md`
- `docs/desktopApp/11_frontend_testing_strategy.md`
- `docs/desktopApp/12_frontend_deployment_and_distribution.md`
- `docs/desktopApp/13_frontend_development_workflow_with_cursor.md`
- `docs/desktopApp/14_desktop_app_implementation_roadmap.md`
- `docs/desktopApp/center_panel_output_contract.md`

## `docs/migration/`

- `docs/migration/graph_edges_migration_report.json`
- `docs/migration/graph_edges_migration_report.md`

## `audits/contracts/nodes/` (YAML authoring contracts)

Human-readable node authoring source. **Enforcement authority:** `engine/validation/*_node_validator.py` and ontology tests — not the Markdown contracts.

- `audits/contracts/nodes/00-START-HERE.md`
- `audits/contracts/nodes/01-shared-node-contract.md`
- `audits/contracts/nodes/paragraph.md`
- `audits/contracts/nodes/parameter.md`
- `audits/contracts/nodes/equation.md`
- `audits/contracts/nodes/lookup.md`
- `audits/contracts/nodes/validation-rule.md`
- `audits/contracts/nodes/workflow.md`
- `audits/contracts/nodes/table.md`
- `audits/contracts/nodes/unit.md`
- `audits/contracts/nodes/dimension.md`
- `audits/contracts/nodes/concept.md`
- `audits/contracts/nodes/authority.md`
- `audits/contracts/nodes/text.md`
- `audits/contracts/nodes/quantity.md`
- `audits/contracts/nodes/designation.md`
- `audits/contracts/nodes/sidecars/paragraph-execution.md`
- `audits/contracts/nodes/sidecars/paragraph-nomenclature.md`
- `audits/contracts/nodes/sidecars/equation-execution.md`
- `audits/contracts/nodes/sidecars/workflow-runtime.md`
- `audits/contracts/nodes/sidecars/pack-metadata.md`

## `audits/contracts/runtime/` (runtime model reference — not YAML authoring)

- `audits/contracts/runtime/fact.md`
- `audits/contracts/runtime/goal.md`
- `audits/contracts/runtime/execution-context.md`
- `audits/contracts/runtime/authority-context.md`

## `audits/reports/nodes/`

- `audits/reports/nodes/current-node-yaml-audit.md` (generated by `scripts/audit_current_node_yaml.py`)

## `docs/process/`

- `docs/process/plan_review_gate.md`

## `docs/protected-files/`

- `docs/protected-files/README.md`
- `docs/protected-files/registry.md`

## `docs/workflows/`

- `docs/workflows/pipe_wall_thickness/acceptance_contract.md`

## `docs/standards/` (documentation only — not `knowledge/standards/`)

- `docs/standards/b313_asset_inline_summary.md`
- `docs/standards/b313_folder_flatten_summary.md`
- `docs/standards/b313_graph_node_move_map.md`
- `docs/standards/b313_reorganize_map.md`

## `docs/temp folder/`

- `docs/temp folder/ASTM_A106.md`
- `docs/temp folder/material_families.yaml.md`
- `docs/temp folder/table_304.1.1.md`

## `docs/tests/`

- `docs/tests/1. end_to_end_test_cases.md`
- `docs/tests/2. acceptance_criteria.md`
- `docs/tests/3. mvp_test_strategy.md`
- `docs/tests/node_test_cases.md`
- `docs/tests/regression_test_strategy.md`
- `docs/tests/test_data_design.md`

## `docs/todo/`

- `docs/todo/Architecture Audit Mode.md`
- `docs/todo/Developer Inspection Framework.md`
- `docs/todo/Graph Algorithms.md`
- `docs/todo/redesigning nodes.md`
- `docs/todo/Refactor Standards Folder Structure (Do Not Modify Node Content).md`
- `docs/todo/to do.md`

## `contracts/` (repository root)

Authoritative shared presentation contracts consumed by API, tests, and desktop app:

- `contracts/center_panel_report_role_order.json` — generated from `models/display_role.DISPLAY_ROLE_ORDER` via `scripts/generate_center_panel_role_order.py`

## `audits/contracts/` (repository root)

Standalone audit / review contracts at repository root (`audits/**` glob):

- `audits/contracts/Equation Rendering.md`
- `audits/contracts/Global Rendering Contract.md`
- `audits/contracts/Graph Engine Behavior.md`
- `audits/contracts/Workflow Rendered Text and Block Output.md`

---

## Maintaining this registry

When new files are added under protected globs, update this registry **only after user approval** to edit protected files.

When adding a new top-level protected glob, update both this file and [`.cursor/rules/protected-documentation.mdc`](../../.cursor/rules/protected-documentation.mdc).
