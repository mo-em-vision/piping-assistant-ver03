
We are now entering an Architecture Audit phase.

## CRITICAL RULES

- DO NOT modify any code.
- DO NOT refactor.
- DO NOT rename files.
- DO NOT move files.
- DO NOT delete files.
- DO NOT generate new architecture.
- DO NOT make assumptions about my intended design.
- DO NOT "improve" anything.

Your ONLY responsibility is to inspect the existing implementation and document it accurately.

If you are uncertain about anything, explicitly state:

> "Unknown from static analysis."

Do not guess.

---

# Goal

I want to completely understand how my application currently works before making any further changes.

Treat this project as if you are auditing a codebase written by another developer.

Your objective is to create complete documentation of the current implementation.

---

# For every folder

Create or update a README.md containing:

## Purpose
Explain the responsibility of this folder.

## Files
Briefly describe every file.

## Entry Points
Identify which files can be entered directly.

## Dependencies
What folders/files does this folder depend on?

Who depends on this folder?

## Runtime Usage
Is this folder currently part of the execution path?

How do you know?

## Possible Dead Code
List files that appear unused.

DO NOT delete them.

Simply explain why they appear unused.

## Notes
Document anything unusual or potentially duplicated.

---

# For every file

Document:

- Purpose
- Public classes/functions
- Inputs
- Outputs
- Side effects
- Files that import it
- Files it imports
- Whether it appears to be actively used
- Confidence level (High / Medium / Low)

---

# Trace execution

Whenever possible, trace execution.

Example:

User Action
    ↓
Planner
    ↓
Workflow
    ↓
Graph
    ↓
Knowledge Node
    ↓
Renderer
    ↓
UI

Use actual file names.

If multiple execution paths exist, document every one.

---

# Duplicate Implementations

Identify situations where multiple implementations appear to exist.

Examples:

- Two planners
- Two graph loaders
- Two node parsers
- Two traversal systems
- Two renderers
- Old and new implementations

Do NOT recommend which one to keep.

Only document them.

---

# Dead Code

If something appears unreachable:

Explain:

- Why it appears unreachable
- What originally may have used it
- Confidence level

Never delete it.

---

# Output Format

Work through ONE folder at a time.

After completing each folder:

1. Present your findings.
2. Wait for my approval.
3. Only then continue to the next folder.

Do not scan the whole project at once.

---

# Most Important Rule

Accuracy is more important than speed.

If you cannot prove something from the code, do not infer it.

Documentation should reflect the code as it exists today—not what you think the architecture should be.
