# engine/planner/

Navigation intelligence: phased questions, assumption handling, engineering plan construction, and coordination between graph expansion and task state.

## Purpose

`Planner` decides **what to ask next** and **when execution can proceed**. It does not run calculations or mutate standards data.

Normalized **`EngineeringPlan`** output (`models/engineering_plan.py`) captures requirements, phases, input strategy, and **`PlannerTraversalState`** for debugging how the planner walks the graph (active node, pending expansion, branch decisions, traversal events).

## Entry Points

| Symbol | File |
|--------|------|
| `Planner` | `planner.py` |
| `GraphTools`, `StateTools`, `RuleTools` | `tools.py` |
| `build_pipe_wall_engineering_plan`, `build_engineering_plan` | `engineering_plan_builder.py` |
| `build_planner_traversal_state` | `planner_traversal.py` |
| `build_planner_inspector_summary` | `plan_inspector.py` |
| `store_engineering_plan_on_task` | `legacy_goal_adapter.py` |

## Dependencies

**Depends on:** `engine/graph/` (navigation, assumptions, graph_engine, path_decision), `engine/events/`, `engine/reference/`, `engine/state/`, `models/planning`, `models/engineering_plan`, `models/agent`

**Used by:** `ai/agents/planner_agent.py`, `api/workflow_bootstrap.py`, `tests/`, `tests/e2e/scenario_runner.py`, `tests/acceptance/`

## Runtime Usage

**Active** via `PlannerAgent` (CLI chat) and `api/workflow_bootstrap.py` (`GraphTools`, navigation phases, `build_engineering_plan` → `store_engineering_plan_on_task`). User-facing parameter prompts live in `engine/messaging/workflow_parameter_prompts.py` and `parameter_input_prompt.py`.

Inspector payloads include `planner_inspector_summary.traversal_summary` and `planner_traversal_view` when an engineering plan is stored on the task.

## Possible Dead Code

| Item | Confidence |
|------|------------|
| `Planner._rules` / `RuleTools` instance | **High** — constructed, never used |
| `GraphTools.limitation_hints` | **High** — duplicate of `RuleTools`, no callers |
| `RuleTools.limitation_hints` | **High** — no callers |

## Notes

- Hard-coded `_DEFAULT_PRIORITIES` for `pipe_wall_thickness_design` in `planner.py`; MAWP uses graph-driven navigation more heavily.
- Default parameter prompt copy is owned by `engine/messaging/workflow_parameter_prompts.py`, not the planner.
- **`PlannerTraversalState`** is derived from plan requirements + `input_strategy` + graph preview (not a second traversal engine). `current_active_node_id` follows phase order and must not jump to coefficient lookups before expansion/path gates resolve.

## Execution Traces

```
User message (CLI)
  → ai/agents/planner_agent.PlannerAgent
  → Planner.plan(task, intent)
  → GraphTools (expand, assumptions, interactions)
  → StateTools (persist inputs, registry)
  → NavigationPlan / AgentAction
```

```
api/workflow_bootstrap.refresh_planning_state
  → GraphTools + navigation_phases
  → build_engineering_plan / build_pipe_wall_engineering_plan
  → build_planner_traversal_state (attach plan.traversal)
  → store_engineering_plan_on_task
      → engineering_plan, engineering_plan_view
      → planner_inspector_summary (traversal_summary, planner_traversal_view)
      → graph_navigation
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Public exports | `Planner`, tool classes | external |
| `planner.py` | **Navigation coordinator** | `Planner` | planner_agent, tests |
| `tools.py` | Facades over graph/state | `GraphTools`, `StateTools`, `RuleTools` | planner, desktop_service, workflow_bootstrap |
| `engineering_plan_builder.py` | Normalized plan assembly | `build_pipe_wall_engineering_plan`, `build_engineering_plan` | goal_builder, workflow_bootstrap, tests |
| `pipe_wall_plan.py` | Pipe wall requirement templates | `build_pipe_wall_requirements`, `build_pipe_wall_dependencies` | engineering_plan_builder |
| `planner_traversal.py` | Traversal debug snapshot | `build_planner_traversal_state`, `build_traversal_summary`, `build_planner_traversal_inspector_view` | engineering_plan_builder, plan_inspector |
| `plan_inspector.py` | Inspector summaries / plan view | `build_planner_inspector_summary`, `build_engineering_plan_view` | legacy_goal_adapter, tests |
| `plan_validation.py` | Plan invariants | `validate_engineering_plan` | engineering_plan_builder, tests |
| `graph_navigation.py` | Categorized missing-field lists | `build_graph_navigation_from_plan` | legacy_goal_adapter |
| `activation_conditions.py` | Requirement activation eval | `evaluate_activation_condition` | engineering_plan_builder |
| `legacy_goal_adapter.py` | Goal tree + task outputs | `store_engineering_plan_on_task`, `build_goal_tree` | goal_builder |

### planner_traversal.py — detail

- **Inputs:** `plan_id`, `workflow_id`, requirements map, `input_strategy`, `PlanGraph`, optional `path_decision`, task facts
- **Outputs:** `PlannerTraversalState` (`current_active_node`, `pending_expansion_nodes`, `expanded_nodes`, `branch_decisions`, `traversal_events`, …)
- **Side effects:** None (pure derivation)
- **Tests:** `tests/planner/test_planner_traversal.py`

### planner.py — detail

- **Inputs:** `StandardsReader`, `TaskStateManager`, optional `EventLogger`
- **Outputs:** `NavigationPlan`, stores planning metadata on task
- **Side effects:** Task input/planning field updates via `StateTools`

### tools.py — detail

- **GraphTools:** wraps `GraphEngine` (expand, plan, interactions, registry)
- **StateTools:** CRUD on `TaskStateManager`
- **RuleTools:** read limitation strings from node metadata (unused at runtime)
