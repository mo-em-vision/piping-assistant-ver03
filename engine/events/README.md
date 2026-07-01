# engine/events/

Structured in-memory event log for planner, validation, and execution layers.

## Purpose

`EventLogger` records typed `models.event.Event` entries (plan built, validation failed, node executed, etc.) for auditing and acceptance tests. Not persisted to disk by default.

## Entry Points

| Symbol | File |
|--------|------|
| `EventLogger` | `event_logger.py` |

## Dependencies

**Depends on:** `models/event`

**Used by:** `engine/executor/executor.py`, `engine/planner/planner.py`, `engine/validation/validation_engine.py`, `tests/acceptance/test_logging.py`

## Runtime Usage

**Active** — default `EventLogger()` constructed in `Executor` and `ValidationEngine` unless injected.

## Possible Dead Code

None.

## Notes

- Separate from `engine/execution/lifecycle_emitter.py` (workflow lifecycle events stored on task outputs).
- `events/__init__.py` re-exports only `EventLogger`.

## Execution Traces

```
Executor / Planner / ValidationEngine
  → EventLogger.emit(EventType.*, payload)
  → events list retained on logger instance
  → tests/acceptance assert event sequences
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Export `EventLogger` | — | external |
| `event_logger.py` | Append-only event list | `EventLogger` | executor, planner, validation |
