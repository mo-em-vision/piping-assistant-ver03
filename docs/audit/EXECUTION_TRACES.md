# Master Execution Traces

End-to-end paths using **actual file names**. From Architecture Audit Mode.

## Desktop — task input to rendered output

```
User (WorkflowPanel / ComposerInlineInput)
  → desktopApp/src/store/taskStore.ts (or workflowStore)
  → desktopApp/src/services/api/taskApi.ts
  → api/server.py (POST /api/v1/tasks/{id}/inputs)
  → api/desktop_service.py
  → engine/planner/planner.py
  → engine/graph/micro_graph_engine.py
  → engine/validation/validation_engine.py
  → engine/executor/executor.py
  → engine/executor/node_runner.py
  → engine/state/state_manager.py (TaskStateManager)
  → api/serializers.py (task_state)
  → desktopApp/src/components/outputs/OutputRenderer.tsx
```

## Desktop — new task / workflow bootstrap

```
User (CreateTaskDialog)
  → desktopApp/src/services/api/projectApi.ts
  → api/server.py (POST /api/v1/tasks)
  → api/workflow_bootstrap.py
  → engine/graph/graph_store.py
  → engine/planner/planner.py
  → serializers.task_state
  → desktopApp/src/components/workflow/WorkflowPanel.tsx
```

## CLI — interactive chat

```
main.py
  → cli/app.py
  → cli/commands/chat.py
  → cli/orchestrator.py
  → ai/agents/intent_agent.py (IntentAgent)
  → engine/router.py
  → ai/agents/planner_agent.py (PlannerAgent)
  → engine/planner/planner.py
  → ai/agents/input_agent.py (InputAgent)
  → engine/executor/executor.py
  → cli/display.py
```

## API — chat assist (in-task Q&A)

```
desktopApp/src/services/api/chatApi.ts
  → api/server.py (POST .../chat)
  → api/chat_service.py
  → ai/agents/task_assist_agent.py
  → engine/reference/standards_reader.py (context)
```

## Report generation

```
desktopApp/src/services/api/reportApi.ts
  → api/report_service.py
  → engine/reports/report_data.py
  → engine/reports/report_generator.py
  → engine/reports/block_renderer.py
  → (optional) engine/reports/presentation.py → ai/agents/synthesis_agent.py
```

## Knowledge compile (offline)

```
knowledge/standards/*/nodes/*.yaml (+ *.md)
  → engine/graph/graph_builder.py
  → engine/reference/graph_compile.py
  → PackGraph in memory
  → scripts/build_graph_db.py
  → knowledge/standards/*/*_graph.db
```

## Dev inspection (gated)

```
desktopApp/src/services/api/inspectionApi.ts
  → api/inspection.py (require_inspection_enabled)
  → engine/inspection/builder.py
  → engine/inspection/trace.py, provenance.py, integrity.py
  → dev/desktop_ui/inspector/DeveloperInspector.tsx
```

## Electron startup

```
desktopApp/electron/main.ts
  → desktopApp/electron/services/startup.ts
  → desktopApp/electron/services/backendProcess.ts (spawns python -m api.server)
  → api/server.py
  → Vite renderer (desktopApp/src/main.tsx)
```

## Graph Explorer (dev only)

```
python -m dev.graph_explorer
  → dev/graph_explorer/adapter.py (reads sessions/*/tasks.json)
  → engine/graph/graph_store.py
  → dev/graph_explorer/server.py (:8765)
  → dev/graph_explorer/web (React Flow :3000)
```
