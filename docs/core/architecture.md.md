# System Architecture

## Purpose

This document defines the architecture of the engineering knowledge graph system.

The system converts engineering standards into executable dependency graphs where:

- standards paragraphs are represented as nodes
- dependencies form a directed graph
- calculations execute only after required information is collected
- reports are generated from the execution trace
- AI is responsible only for user interaction and explanation


---

# 1. Core Architecture Principle

The system is not a collection of workflows.

It is a dependency graph traversal engine.

A user request identifies an engineering intent.

The system discovers all required nodes, resolves dependencies, collects required information, executes calculations, and generates a traceable engineering report.


Flow:
```
User

↓

AI Interaction Layer

↓

Intent Identification

↓

Root Node Discovery

↓

Dependency Graph Traversal

↓

Input Collection

↓

DAG Execution

↓

Report Generation

↓

AI Explanation
```



---

# 2. AI Responsibility Boundary

AI is the interaction layer only.

AI responsibilities:

- understand user request
- identify engineering intent
- communicate missing information
- explain calculation results
- explain warnings
- summarize reports
- answer questions about completed analysis
- retrieve relevant session information


AI must NOT:

- select formulas
- decide engineering paths
- perform calculations
- replace standard logic
- determine dependencies


Engineering decisions come from nodes.

AI explains the decisions.


---

# 3. Project Structure

```
project/

├── ai/

│ ├── prompts/

│ ├── agents/

│ └── response/

│

├── engine/

│ ├── graph/

│ ├── executor/

│ ├── state/

│ ├── events/

│ └── reports/

│

├── standards/

│  
│ ├── asme_b31.3/

│ │  
│ │ ├── index.md  
│ │ ├── readme.md  
│ │ │  
│ │ ├── roots/  
│ │ │  
│ │ ├── nodes/  
│ │ │  
│ │ ├── templates/  
│ │ │  
│ │ ├── tables/  
│ │ │  
│ │ ├── figures/  
│ │ │  
│ │ └── reports/  
│  
│ ├── api_570/  
│ │  
│ ├── api_650/  
│ │  
│ └── bpvc_section_viii/  
│

├── sessions/

└── config/
```

  
---  
  
# 4. Standard Organization  
  
  
Each standard is self-contained.  
  
  
Example:
```
asme_b31.3/

index.md

readme.md

nodes/

tables/

figures/

templates/

roots/

reports/
```

No central database exists.  
  
Engineering knowledge belongs to the standard.  
  
---  
  
# 5. Master Index  
  
  
index.md is only navigation.  
  
It contains:  
  
- sections  
- links  
- root analysis entry points  
  
  
Example:
```
Integrity Verification

link:

integrity_check/index.md

Material Selection

link:

materials/index.md

Pressure Design

link:

pressure_design/index.md
```


index.md never contains paragraph content.


---

# 6. Root Nodes


Root nodes represent user-level engineering requests.


Example:

```
integrity_check/

root.md
```



A root node declares:


- analysis purpose
- required checks
- dependencies
- report template


Example:


```yaml

id:

B313-INTEGRITY


type:

root


depends_on:

 - B313-WALL-THICKNESS

 - B313-PRESSURE-RATING

 - B313-FLEXIBILITY

 - B313-PRESSURE-TEST

```
---
# 7. Node Architecture

A node represents an engineering knowledge unit.

A node may contain:

- paragraph text
- formulas
- decisions
- lookup logic
- validation rules
- outputs
- report information
- children

Node types:
```

calculation

lookup

decision

validation

informational

constraint

composite

root

```

# 8. Graph Discovery

The system executes in two phases.

## Phase 1 — Discovery

Start:

User intent root node

Process:

1. Load root node
2. Read dependencies
3. Recursively expand dependencies
4. Build directed graph
5. Validate dependencies
6. Perform topological sorting

Output:

```
Execution graph
```

Example:
```
Integrity Check  
  
|  
  
+-- Wall Thickness  
  
| |  
  
| +-- Allowable Stress  
  
|  
  
+-- Pressure Test
```
---
# Phase 2 — Information Collection

Before calculation:

The system determines:

- required user inputs
- dependency outputs required
- unresolved conditions

The user is asked only for missing information.

---

# 9. Conditional Nodes

Conditions do not create hidden workflows.

Conditions create decisions in the graph.

Example:
```
304.1.1  
  
condition:  
  
t < D/6  
  
  
TRUE:  
  
continue thin wall calculation  
  
  
FALSE:  
  
load thick wall node
```
All decisions are stored.

---

# 10. Execution Engine

The calculation engine executes nodes.

Execution:

1. Load resolved inputs
2. Inject dependency outputs
3. Execute formula steps
4. Perform validations
5. Store outputs
6. Create trace event

Formula execution:
```yaml

formula:

 steps:

  - expression:

      "P*D/(2*(S*E*W+P*Y))"

    assign:

      thickness

```
Python executes the expression safely.

---

# 11. Formula Representation

Nodes contain two formula formats.

Machine format:

Used by executor.

```yaml
steps:  
  
- expression:
```

Human format:

Used by reports.
```yaml
display:  
  
t = PD / 2(SEW + PY)
```

This provides:

- calculation execution
- beautiful reporting
- traceability

---

# 12. Session State

Each conversation has independent memory.

Structure:

```

sessions/

session_id/

    conversation.json

    task_state.json

    events.json

    reports/


```

Stored:

- messages
- discovered nodes
- inputs
- decisions
- outputs
- warnings
- reports

---

# 13. Event System

Events record everything.

Examples:
```

node_discovered

dependency_resolved

input_requested

input_received

condition_checked

decision_made

calculation_started

calculation_completed

warning_generated

report_created

```

Reports can be rebuilt from events.

---

# 14. Report Generation  
  
  
Reports are generated from the engineering execution trace.  
  
The report is not created from final values only.  
  
The report must preserve the reasoning path:  


```
standard paragraph → dependency → decision → formula → output → conclusion  
```
  

  
  
Flow:  
  
  ```
Execution Trace  
  
↓  
  
Immutable Report Data Model  
  
↓  
  
Report Structure Generator  
  
↓  
  
AI Presentation Layer  
  
↓  
  
PDF Generator  
  
↓  
  
Final Report  
  ```

  
  
---  
  
# Report Data Model  
  
  
The report data model is the source of truth.  
  
It contains:  
  
  
- discovered nodes  
- dependency chain  
- execution order  
- input values  
- formulas  
- calculation steps  
- outputs  
- warnings  
- decisions  
- references  
  
  
The report data model must not be modified by AI.  
  
  
---  
  
# AI Presentation Layer  
  
  
The AI receives the completed report data model.  
  
  
The AI is responsible for:  
  
  
- improving readability  
- explaining engineering reasoning  
- organizing sections  
- creating human-friendly summaries  
- improving wording  
  
  
The AI must not:  
  
  
- change inputs  
- change outputs  
- modify formulas  
- alter calculation results  
- remove warnings  
- change PASS/FAIL status  
- modify standard references  
  
  
The AI changes presentation only.  
  
  
---  
  
# PDF Report  
  
  
The final report is stored as a PDF file.  
  
  
Each report must include:  
  
  
- analysis objective  
- discovered graph path  
- decision history  
- calculations  
- engineering notes  
- warnings  
- final assessment  
- traceability appendix

---

# 15. Report Traceability Requirements

Every report must show:

- selected nodes
- traversal order
- dependency reasons
- decisions
- formulas
- inputs
- outputs
- warnings
- standard references

the system output must pass through ai for generating a beautifully written text from the inputs. the ai must not alter any data and should only rearrange the inputs so that it would be visually appealing to the user.

Example:

```

Decision:


Paragraph 304.1.1 was evaluated.


Condition:

t < D/6


Result:

TRUE


Action:

Continue with thin-wall equation.


```

# 16. Standard Reference

Each report section includes:

- standard name
- paragraph number
- verbatim paragraph text
- applied notes
- referenced tables
- referenced figures

---

# 17. Design Goal

The final system behaves as:

A traceable engineering reasoning engine.

Every result can answer:

"Why was this calculation performed?"

"Which paragraph caused this decision?"

"Where did this value come from?"