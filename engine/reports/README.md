# engine/reports/

Engineering report generation: build `ReportData` from task state and render markdown/HTML/JSON/PDF.

## Purpose

Turn completed (or partial) tasks into auditable engineering documents. Templates live in `templates/`; formatting is deterministic unless `enrich_report_with_ai` is enabled.

## Entry Points

| Symbol | File |
|--------|------|
| `ReportGenerator` | `report_generator.py` |
| `build_report_from_task` | `report_data.py` |
| `render_markdown`, `render_html`, `render_json` | `formatters.py` |

## Dependencies

**Depends on:** `engine/reference/`, `engine/reports/*`, `models/report`, optional AI in `presentation.py`

**Used by:** `cli/commands/reports.py`, `api/report_service.py`, `ai/agents/synthesis_agent.py`, acceptance/e2e tests

## Runtime Usage

**Active** when user exports a report or e2e scenarios validate report structure.

## Possible Dead Code

| Item | Confidence |
|------|------------|
| `report_data._flatten_traversal` legacy path | **Medium** — may be unused if micro-graph trace preferred; verify when editing |

## Notes

- `block_renderer.py` converts desktop `display_blocks` to report sections (shared with live UI blocks).
- `equation_format.py` is internal to formatters/block_renderer (LaTeX helpers).
- Templates: `pipe_wall_thickness_design_report.md`, `mawp_design_report.md`, `generic_task_report.md`, `calculation_report.md`, `audit_report.md`, `integrity_report.md`.

## Execution Traces

```
Task (completed)
  → report_data.build_report_from_task(reader, task)
  → ReportGenerator.generate(report, output_dir, formats)
    → formatters.render_markdown | render_html | render_json
    → optional presentation.enrich_report_with_ai
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Export `ReportGenerator` | — | external |
| `block_renderer.py` | Display blocks → sections | `blocks_to_display_sections` | report_data, tests |
| `equation_format.py` | LaTeX/markdown equation helpers | `display_to_latex`, `equation_markdown` | formatters, block_renderer |
| `formatters.py` | **Multi-format render** | `render_markdown`, `render_html`, `write_pdf` | report_generator, synthesis_agent, tests |
| `number_format.py` | Report number rounding | `format_report_number` | report_data, tests |
| `presentation.py` | Optional AI enrichment | `apply_presentation`, `enrich_report_with_ai` | report_generator |
| `report_data.py` | **Build ReportData** | `build_report_from_task` | report_generator, e2e |
| `report_generator.py` | File output orchestration | `ReportGenerator` | cli, tests |
| `template_registry.py` | Workflow → template name | `resolve_template_name` | report_data, formatters |
| `templates/*.md` | Jinja-style report bodies | — | formatters (loaded by name) |
