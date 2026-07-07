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

## API — chat assist (in-task Q&A)

```
desktopApp/src/services/api/chatApi.ts
  → api/server.py (POST .../chat)
  → api/chat_service.py
  → ai/agents/task_assist_agent.py
  → engine/reference/standards_reader.py (context)
```

## Flow Guidance — task state snapshot

```
serializers.task_state
  → api/flow_guidance.build_flow_guidance_payload(task, reader)
  → engine/presentation/guidance_resolver.GuidanceResolver.resolve
    → presentation/guidance/workflows/<workflow_id>.yaml
  → engine/presentation/response_composer.ResponseComposer.compose
    → engine/messaging/ (step_prompt, formula_parameter_prompt)
  → task_state["flow_guidance"]  (presentation_blocks, transcript_blocks, active_prompt)
```

## Flow Guidance — chat turn (waiting_input)

```
api/chat_orchestrator.ChatOrchestrator.handle_turn
  → GuidanceResolver + ResponseComposer
  → ChatResponse.data: presentation, new_transcript_blocks
  → storage/session_store.SessionStore.append_message(transcript_blocks=...)
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

