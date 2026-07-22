# Protected files

This folder holds policy for repository paths that agents must not edit without authorization.

| Resource | Role |
| --- | --- |
| [`registry.md`](registry.md) | Why paths are protected, task modes, categories, workflow, ownership |
| [`config/restricted_paths.yaml`](../../config/restricted_paths.yaml) | Machine-readable path manifest (hooks read this file) |

**Cursor rule:** [`.cursor/rules/protected-documentation.mdc`](../../.cursor/rules/protected-documentation.mdc)

**Documentation-edit mode** — declare `Mode: documentation-edit` and an `Allowed files:` list in the user request before editing authoritative protected paths.
