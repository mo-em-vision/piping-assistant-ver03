# engine/planner/

Navigation intelligence: phased questions, assumption handling, and coordination between graph expansion and task state.

## Purpose

`Planner` decides **what to ask next** and **when execution can proceed**. It does not run calculations or mutate standards data.

## Entry Points

| Symbol | File |
|--------|------|
| `Planner` | `planner.py` |
| `GraphTools`, `StateTools`, `RuleTools` | `tools.py` |

## Dependencies

**Depends on:** `engine/graph/` (navigation, assumptions, graph_engine), `engine/events/`, `engine/reference/`, `engine/state/`, `models/planning`, `models/agent`

**Used by:** `ai/agents/planner_agent.py`, `tests/`, `tests/e2e/scenario_runner.py`, `tests/acceptance/`

## Runtime Usage

**Active** via `PlannerAgent` (CLI chat) and indirectly via `api/workflow_bootstrap.py` (uses `GraphTools`, `_INPUT_QUESTIONS`, navigation phases — not full `Planner` class on every API call).

## Possible Dead Code

| Item | Confidence |
|------|------------|
| `Planner._rules` / `RuleTools` instance | **High** — constructed, never used |
| `GraphTools.limitation_hints` | **High** — duplicate of `RuleTools`, no callers |
| `RuleTools.limitation_hints` | **High** — no callers |

## Notes

- Hard-coded `_INPUT_QUESTIONS` and `_DEFAULT_PRIORITIES` for `pipe_wall_thickness_design` in `planner.py`; MAWP uses graph-driven navigation more heavily.
- `api/workflow_bootstrap.py` imports `_INPUT_QUESTIONS` directly (private API).

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
  → GraphTools + navigation_phases (parallel path to Planner logic)
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Public exports | `Planner`, tool classes | external |
| `planner.py` | **Navigation coordinator** | `Planner`, `_INPUT_QUESTIONS` | planner_agent, tests, workflow_bootstrap |
| `tools.py` | Facades over graph/state | `GraphTools`, `StateTools`, `RuleTools` | planner, desktop_service, workflow_bootstrap |

### planner.py — detail

- **Inputs:** `StandardsReader`, `TaskStateManager`, optional `EventLogger`
- **Outputs:** `NavigationPlan`, stores planning metadata on task
- **Side effects:** Task input/planning field updates via `StateTools`

### tools.py — detail

- **GraphTools:** wraps `GraphEngine` (expand, plan, interactions, registry)
- **StateTools:** CRUD on `TaskStateManager`
- **RuleTools:** read limitation strings from node metadata (unused at runtime)
