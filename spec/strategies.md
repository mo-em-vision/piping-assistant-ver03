# Lookup rule strategies

Each `lookup_rules` entry must declare exactly one `strategy`. Required logical inputs and allowed resolvers are fixed per strategy.

| Strategy | Required inputs | Allowed resolvers |
| --- | --- | --- |
| `pipe_nps` | `nominal_pipe_size` | `nps_key` |
| `pipe_nps_schedule` | `nominal_pipe_size`, `pipe_schedule` | `nps_key`, `schedule_key` |
| `material_temperature` | `material_grade`, `design_temperature` | `material_catalog`, `identity` |
| `material_group_temperature` | `metallurgical_group`, `design_temperature` | `metallurgical_group_key`, `identity` |
| `material_category` | `material_grade`, `pipe_construction_type` | `material_catalog`, `joint_category_normalize` |
| `material_category_temperature` | `material_grade`, `pipe_construction_type`, `design_temperature` | `material_catalog`, `joint_category_normalize`, `identity` |
| `material_only` | `material_grade` | `material_catalog` |

Temperature strategies require a `row_resolution.<temperature_input_key>` block with breakpoint axis policy and explicit `interpolate_columns` (or per-column `output_columns` when behavior differs).

Implementation: `engine/executor/lookup_rule_strategies.py`, `engine/executor/table_resolver.py`.
