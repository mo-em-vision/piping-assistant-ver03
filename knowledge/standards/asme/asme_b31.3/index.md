# ASME B31.3 — Master Index

Navigation only. Paragraph content lives in node folders under `nodes/` (flat `nodes/{node_id}/` layout).

## Analysis entry points

| Analysis | Root |
|----------|------|
| Pipe Wall Thickness Design | [nodes/workflows/pipe-wall-thickness.yaml](nodes/workflows/pipe-wall-thickness.yaml) |
| Maximum Allowable Working Pressure (MAWP) | [nodes/workflows/mawp.yaml](nodes/workflows/mawp.yaml) |

## Section 302 — Allowable stresses

| Node ID | Path | Description |
|---------|------|-------------|
| B313-302.3.3 | `nodes/B313-302.3.3/` | Quality factor determination (Tables A-2, A-3, 302.3.3C) |
| B313-302.3.5 | `nodes/B313-302.3.5/` | Limits of calculated stresses, including W in subsection (e) |
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

## Appendix A — Tables

| Node ID | Path | Description |
|---------|------|-------------|
| B313-table-A-1 | `nodes/tables/B313-table-A-1.yaml` | Basic Allowable Stresses in Tension for Metals |
| B313-table-A-2 | `nodes/tables/B313-table-A-2.yaml` | Table A-2 basic casting quality factor lookup |
| B313-table-A-3 | `nodes/tables/B313-table-A-3.yaml` | Table A-3 longitudinal weld joint quality factor lookup |
