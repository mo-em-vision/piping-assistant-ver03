# ASME B31.3 — Master Index

Navigation only. Paragraph content lives in node folders under `nodes/` (flat `nodes/{node_id}/` layout).

## Analysis entry points

| Analysis | Root |
|----------|------|
| Pipe Wall Thickness Design | [nodes/workflows/pipe-wall-thickness.yaml](nodes/workflows/pipe-wall-thickness.yaml) (`WF-PIPE-WALL-THICKNESS`, sidecar `workflows/WF-PIPE-WALL-THICKNESS/runtime.yaml`) |
| Maximum Allowable Working Pressure (MAWP) | [nodes/workflows/mawp.yaml](nodes/workflows/mawp.yaml) (`WF-MAWP`, sidecar `workflows/WF-MAWP/runtime.yaml`) |

Workflow ontology files use template frontmatter (`key`, `phases`, `goal_expansion`, …) with executor-critical metadata in `workflows/{id}/runtime.yaml` sidecars.

## Section 302 — Allowable stresses

| Node ID | Path | Description |
|---------|------|-------------|
| 302.3.3 | `nodes/paragraph/302.3.3.yaml` | Quality factor determination (Tables A-2, A-3, 302.3.3C) |
| 302.3.5 | `nodes/paragraph/302.3.5.yaml` | Limits of calculated stresses, including W in subsection (e) |
| B313-table-302-3-3C | `nodes/B313-table-302-3-3C/` | Table 302.3.3C increased casting quality factors |
| B313-table-302-3-5-1 | `nodes/tables/B313-table-302-3-5-1.yaml` | Table 302.3.5-1 weld strength reduction lookup |

### Table 302.3.3C notes

| Node ID | Path | Description |
|---------|------|-------------|
| B313-note-302-3-3C-1 | `nodes/B313-note-302-3-3C-1/` | Note (1) — machine all surfaces |
| B313-note-302-3-3C-2a | `nodes/B313-note-302-3-3C-2a/` | Note (2)(a) — magnetic particle examination |
| B313-note-302-3-3C-2b | `nodes/B313-note-302-3-3C-2b/` | Note (2)(b) — liquid penetrant examination |
| B313-note-302-3-3C-3a | `nodes/B313-note-302-3-3C-3a/` | Note (3)(a) — ultrasonic examination |
| B313-note-302-3-3C-3b | `nodes/B313-note-302-3-3C-3b/` | Note (3)(b) — radiographic examination |

## Section 304 — Pressure design

| Node ID | Path | Description |
|---------|------|-------------|
| 304 | `nodes/paragraph/304.yaml` | Section 304 — Pressure Design of Components (structural) |
| 304.1 | `nodes/paragraph/304.1.yaml` | §304.1 — Design of Straight Pipe (structural) |
| 304.1.1 | `nodes/paragraph/304.1.1.yaml` | Required thickness relationship and nomenclature (eq. 2, symbols) |
| 304.1.2 | `nodes/paragraph/304.1.2.yaml` | Internal pressure wall thickness calculation (thin-wall) |
| 304.1.3 | `nodes/paragraph/304.1.3.yaml` | External pressure wall thickness (stub) |
| B313-table-304-1-1-1 | `nodes/tables/B313-table-304-1-1-1.yaml` | Table 304.1.1-1 coefficient Y lookup |
| 304.3 | `nodes/paragraph/304.3.yaml` | §304.3 — Branch Connections (structural) |
| 304.3.1 | `nodes/paragraph/304.3.1.yaml` | Branch connections — general applicability and limits |
| 304.3.2 | `nodes/paragraph/304.3.2.yaml` | Branch connections — strength and assumed-adequate cases |
| 304.3.3 | `nodes/paragraph/304.3.3.yaml` | Welded branch reinforcement — nomenclature and area equations |

## Equation nodes (`asme_b313_*`)

Standalone equation ontology files under `nodes/equation/` (template frontmatter + `equation/{id}/execution.yaml` sidecars).

| Node ID | Paragraph | Description |
|---------|-----------|-------------|
| `asme_b313_304_1_1_eq_2` | 304.1.1 | Minimum required thickness (eq. 2) |
| `asme_b313_304_1_2_wall_thickness` | 304.1.2 | Internal pressure wall thickness |
| `asme_b313_mawp_pressure` | 304.1.2 | Maximum allowable working pressure |
| `asme_b313_thick_wall_y` | 304.1.2 | Thick-wall temperature coefficient Y |
| `asme_b313_pressure_design_thickness` | WF-MAWP | Pressure design thickness from actual thickness |
| `asme_b313_302_3_5_eq_1a` | 302.3.5 | Allowable displacement stress range (eq. 1a) |
| `asme_b313_302_3_5_eq_1b` | 302.3.5 | Displacement stress range with margin (eq. 1b) |
| `asme_b313_302_3_5_eq_1c` | 302.3.5 | Stress range factor (eq. 1c) |
| `asme_b313_304_3_3_eq_6` | 304.3.3 | Required reinforcement area (eq. 6) |
| `asme_b313_304_3_3_eq_6a` | 304.3.3 | Available reinforcement area check (eq. 6a) |
| `asme_b313_304_3_3_eq_7` | 304.3.3 | Run pipe excess thickness area (eq. 7) |
| `asme_b313_304_3_3_eq_8` | 304.3.3 | Branch pipe excess thickness area (eq. 8) |

## Appendix A — Tables

| Node ID | Path | Description |
|---------|------|-------------|
| B313-table-A-1 | `nodes/tables/B313-table-A-1.yaml` | Basic Allowable Stresses in Tension for Metals |
| B313-table-A-2 | `nodes/tables/B313-table-A-2.yaml` | Table A-2 basic casting quality factor lookup |
| B313-table-A-3 | `nodes/tables/B313-table-A-3.yaml` | Table A-3 longitudinal weld joint quality factor lookup |
