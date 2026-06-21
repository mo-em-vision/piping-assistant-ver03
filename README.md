# Engineering Knowledge Graph Assistant (Ver03)

Deterministic engineering assistant that turns standards into executable dependency graphs. Standards paragraphs become nodes; dependencies form a directed graph; calculations run only after required inputs are collected; reports are built from the execution trace.

AI handles navigation and explanation. Engineering truth lives in the graph engine, validation layer, and execution layer — not in the LLM.

**Chat input collection** is phased and mostly deterministic: assumptions and path decisions use numbered options; calculation steps show the governing formula with known/missing parameters on separate lines. The LLM is used for initial intent routing and ambiguous/off-topic messages, not for every follow-up prompt.

## Architecture

```
User → AI (intent / input) → Planner → Graph Engine → Validation → Execution → Report
```

| Layer | Role |
|-------|------|
| **Planner** | Root discovery, missing-input detection |
| **Graph Engine** | Dependency resolution, execution plan |
| **Validation** | Compliance gate before execution |
| **Execution** | Formula and table lookups |
| **Report** | Traceable output from task state |

Canonical workflow: **pipe wall thickness design** (`ASME B31.3` §304.1.1).

Full design docs: [`docs/core/`](docs/core/) — start with [Architecture](docs/core/1.%20Architecture.md) and the [Build Sequence](docs/core/12.%20Cursor%20Build%20Sequence%20(SAFE%20STEP-BY-STEP%20PLAN).md).

## Requirements

- Python 3.11+
- See [`requirements.txt`](requirements.txt)

## Setup

```bash
cd Ver03
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Optional environment variables (for AI chat):

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model name (optional) |
| `OPENAI_BASE_URL` | Custom API base URL (optional) |

Configuration file: [`config/config.yaml`](config/config.yaml) (`default_standard`, `standards_root`, `sessions_dir`, etc.).

## Usage

```bash
# Interactive engineering chat
python main.py chat

# Task management
python main.py task list
python main.py task show <task_id>

# Inspect standards graph
python main.py graph show pipe_wall_thickness_design
python main.py node show B313-304.1.1

# Generate report
python main.py report generate <task_id> --format html
python main.py report generate <task_id> --format pdf --with-ai
```

Equivalent module invocation: `python -m cli chat`

## Standards layout

Standards are grouped under `standards/`:

```
standards/
├── asme/
│   ├── asme_b31.3/     # nodes, roots, allowable stress tables
│   ├── asme_b36.10/    # pipe NPS / OD / schedule dimensions
│   └── bpvc_section_viii/
├── astm/
│   ├── astm_a106/      # carbon steel pipe material properties
│   └── astm_a312/      # stainless steel pipe material properties
└── api/
    ├── api_570/
    └── api_650/
```

Each pack is self-contained (`nodes/`, `roots/`, `tables/`, `index.md`). The reader resolves paths via `engine/reference/standards_paths.py` — use slug `asme_b31.3`, not the full folder path.

### Reference lookups (Python)

```python
from pathlib import Path

from engine.executor.pipe_dimension_lookup import PipeDimensionLookup
from engine.executor.material_properties_lookup import MaterialPropertiesLookup

root = Path("standards")

# ASME B36.10M pipe dimensions
PipeDimensionLookup(root).lookup("2", schedule="40")

# ASTM material properties
MaterialPropertiesLookup(root, standard="astm_a106").lookup("SA-106B")
MaterialPropertiesLookup(root, standard="astm_a312").lookup("TP316L")
```

## Project structure

```
Ver03/
├── main.py              # CLI entry point
├── cli/                 # Typer + Rich CLI
├── ai/                  # Agents, prompts, LLM client
├── engine/              # Graph, planner, validation, executor, reports, state
├── models/              # Pure dataclass data models
├── standards/           # On-disk engineering knowledge
├── config/              # CLI configuration
├── tests/               # Pytest suite
└── docs/core/           # Architecture and design documentation
```

## Tests

```bash
python -m pytest tests/ -q
```

## Implementation status

| Step | Component | Status |
|------|-----------|--------|
| 0–3 | Scaffold, models, state, router | Complete |
| 4 | Graph engine + execution layer | Complete |
| 5 | Planner layer | Complete |
| 5.5 | Validation layer | Complete |
| 6 | Workflow engine | Planned |
| — | AI agents + CLI + reports | Complete |

See [Build Sequence](docs/core/12.%20Cursor%20Build%20Sequence%20(SAFE%20STEP-BY-STEP%20PLAN).md) for the full step-by-step plan.

## License / data disclaimer

Sample table values under `standards/` are for development and testing. Verify against licensed standards (ASME, ASTM, API) before production engineering use.
