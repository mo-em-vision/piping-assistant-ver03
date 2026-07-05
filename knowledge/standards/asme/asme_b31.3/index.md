# ASME B31.3 — Master Index

Navigation only. Paragraph content lives in flat `nodes/paragraph/{id}.yaml` files with optional sidecars.

## Analysis entry points

| Analysis | Root |
|----------|------|
| Pipe Wall Thickness Design | [`workflows/pipe-wall-thickness.yaml`](../../../../workflows/pipe-wall-thickness.yaml) (`WF-PIPE-WALL-THICKNESS`, sidecar `WF-PIPE-WALL-THICKNESS/runtime.yaml`) |
| Maximum Allowable Working Pressure (MAWP) | [`workflows/mawp.yaml`](../../../../workflows/mawp.yaml) (`WF-MAWP`, sidecar `WF-MAWP/runtime.yaml`) |

## Section 302 — Allowable stresses

| Node ID | Path | Description |
|---------|------|-------------|
| 302.3.3-a | `nodes/paragraph/302.3.3-a.yaml` | Casting quality factor — general |
| 302.3.3-b | `nodes/paragraph/302.3.3-b.yaml` | Basic quality factors (Table A-2) |
| 302.3.3-c | `nodes/paragraph/302.3.3-c.yaml` | Increased quality factors (Table 302.3.3C) |
| 302.3.5-a … 302.3.5-f | `nodes/paragraph/302.3.5-*.yaml` | Limits of calculated stresses (W in `302.3.5-e`) |
| B313-table-302-3-3C | `nodes/tables/B313-table-302-3-3C.yaml` | Table 302.3.3C increased casting quality factors |
| B313-table-302-3-5-1 | `nodes/tables/B313-table-302-3-5-1.yaml` | Table 302.3.5-1 weld strength reduction lookup |

## Section 304 — Pressure design

| Node ID | Path | Description |
|---------|------|-------------|
| 304 | `nodes/paragraph/304.yaml` | Section 304 — structural |
| 304.1 | `nodes/paragraph/304.1.yaml` | §304.1 — structural |
| 304.1.1-a | `nodes/paragraph/304.1.1-a.yaml` | Required thickness (eq. 2) |
| 304.1.1-b | `nodes/paragraph/304.1.1-b.yaml` | Nomenclature |
| 304.1.2-a | `nodes/paragraph/304.1.2-a.yaml` | Internal pressure — thin wall (eq. 3a/3b) |
| 304.1.2-b | `nodes/paragraph/304.1.2-b.yaml` | Internal pressure — thick wall special consideration |
| 304.1.3 | `nodes/paragraph/304.1.3.yaml` | External pressure |
| 304.3 | `nodes/paragraph/304.3.yaml` | §304.3 — structural |
| 304.3.1, 304.3.1-b … d | `nodes/paragraph/304.3.1*.yaml` | Branch connections — general |
| 304.3.2-a … c | `nodes/paragraph/304.3.2-*.yaml` | Branch connection strength |
| 304.3.3-a … f | `nodes/paragraph/304.3.3-*.yaml` | Welded branch reinforcement |

## Equation nodes (`asme_b313_*`)

| Node ID | Paragraph | Description |
|---------|-----------|-------------|
| `asme_b313_304_1_1_eq_2` | 304.1.1-a | Minimum required thickness (eq. 2) |
| `asme_b313_304_1_2_eq_3a` | 304.1.2-a | Internal pressure wall thickness (eq. 3a) |
| `asme_b313_304_1_2_eq_3b` | 304.1.2-a | Internal pressure wall thickness (eq. 3b) |
| `asme_b313_mawp_pressure` | 304.1.2-a | Maximum allowable working pressure |
| `asme_b313_thick_wall_y` | 304.1.2-a | Thick-wall temperature coefficient Y |
| `asme_b313_302_3_5_eq_1a` … `1c` | 302.3.5-d | Displacement stress range equations |
| `asme_b313_304_3_3_eq_6` | 304.3.3-b | Required reinforcement area (eq. 6) |
| `asme_b313_304_1_2_valrule_b` | 304.1.2-b | Thick-wall special consideration (§304.1.2(b)) |
| `asme_b313_304_3_3_valrule_6a` | 304.3.3-c | Available reinforcement area check (eq. 6a) |
| `asme_b313_304_3_3_eq_7` / `eq_8` | 304.3.3-c | Areas A_2 / A_3 |

Naming convention: see [docs/node-templates/Paragraph Node.md](../../../docs/node-templates/Paragraph%20Node.md) and `.cursor/rules/paragraph-subsection-naming.mdc`.
