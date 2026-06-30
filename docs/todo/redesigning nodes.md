# Graph Architecture Redesign Specification

> **Purpose**
> 
> This document defines the redesign of the application's knowledge graph and workflow engine. The objective is to transform the application into a deterministic, graph-based engineering platform where:
> 
> - the Knowledge Graph is the source of truth,
>     
> - workflows are reproducible,
>     
> - calculations are deterministic,
>     
> - rendering is separated from execution,
>     
> - and the graph remains reusable across multiple tasks.
>     

---

# Overall Strategy

This redesign **must not** be performed in one large refactor.

Instead, complete the redesign in the following phases. Each phase should leave the application in a working state before moving to the next phase.

---

# Phase 1 — Establish the Architecture

## Objective

Redesign the project around clear architectural layers.

## Target Architecture

```
Knowledge Graph (Persistent)
        │
        ▼
Workflow Execution Engine
        │
        ▼
Workflow State (Runtime)
        │
        ▼
Presentation Engine
        │
        ▼
Report Generator
```

---

## Design Principles

These principles are mandatory.

### 1. Knowledge Graph is the source of truth.

All engineering knowledge lives inside the graph.

Examples:

- standards
    
- equations
    
- workflow definitions
    
- lookup definitions
    
- quantities
    
- tables
    
- documentation
    

---

### 2. Graph nodes are immutable.

Nodes never store:

- user inputs
    
- calculated values
    
- workflow progress
    
- temporary selections
    

---

### 3. Workflow State stores runtime data.

Anything that changes during execution belongs inside Workflow State.

---

### 4. Separate engineering knowledge from execution.

The graph describes engineering knowledge.

The execution engine performs engineering tasks.

---

### 5. Separate rendering from execution.

Traversal should never render UI directly.

Traversal produces events.

Renderers consume those events.

---

### 6. LLM calls 
only available on right selecting text in the central panel and selecting ask AI during workflow execution, which would output the response in the left chat tab (currently working).

Everything required for workflow execution must be deterministic.

---

# Phase 2 — Redesign Node Types

Review every existing node type.

Ensure every node has a single responsibility.

---

## Quantity Node

Represents a physical engineering quantity.

Example

```
Pressure

Temperature

Diameter

Stress

Thickness
```

A quantity node contains

```
id

name

dimension

description

documentation
```

It never stores

```
value

user input

runtime units
```

---

## Equation Node

Represents symbolic mathematics.

Contains

```
formula

latex

variables

documentation

references
```

Never stores calculated values.

---

## Workflow Node

Represents engineering procedures.

Contains

```
title

entry point

execution order

child nodes

documentation
```

---

## Lookup Node

Represents engineering lookups.

Examples

```
ASME B36.10

ASME B36.19

Material Tables
```

Contains

```
lookup keys

lookup outputs

documentation
```

---

## Documentation Nodes

Existing nodes remain

```
Standard

Section

Paragraph

Annex

Figure

Table

Note
```

These remain documentation nodes.

---

## Designation Nodes (NEW)

Create a new node type.

Purpose

Represent engineering designations.

Examples

```
NPS

DN

Pipe Schedule

Material Grade

Flange Rating
```

These are NOT quantities.

---

# Phase 3 — Redesign Relationships

Do NOT duplicate quantity nodes.

Instead use relationship metadata.

Example

Equation

↓

Pressure

Relationship metadata

```
alias

role

displayName

required

defaultValue

validation
```

Example

```
Equation
        |
        | alias=P
        | role=Internal Pressure
        |
        ▼
Pressure
```

Another equation

```
Equation
        |
        | alias=Pe
        | role=External Pressure
        |
        ▼
Pressure
```

Only one Pressure node exists.

---

# Phase 4 — Introduce Workflow State

Create a runtime Workflow State.

Workflow State stores

```
Task ID

Workflow ID

Current Node

Visited Nodes

Variable Values

Lookup Results

Selections

Warnings

Errors

History

Timestamp

Version
```

Workflow State is completely separate from the graph.

It should be serializable so workflows can be restored later.

---

# Phase 5 — Parameter System

Parameters belong to Workflow State.

Each parameter should contain

```
name

value

dimension

unit

priority

source

status
```

Possible sources

```
User Input

Lookup

Equation

Default

Derived
```

The execution engine should retrieve parameter values according to priority.

---

# Phase 6 — Unit System

Separate units from quantities.

Introduce a Unit Registry.

Example

```
Length

Pressure

Temperature

Mass

Density
```

Each quantity references only its dimension.

Example

```
Pressure

dimension = Pressure
```

Allowed units are resolved from the registry.

---

Designations

```
NPS

DN

Schedule
```

must never appear inside the unit registry.

They are engineering designations.

---

# Phase 7 — Documentation Fields

Replace generic text fields with structured documentation.

Every node should expose

```
title

summary

description

beforeEnter

afterExit

instructions

warnings

tips

references

reportSummary
```

These are deterministic.

No AI required.

---

Parameterized templates are supported.

Example

```
Pipe size {{NPS}} Schedule {{Schedule}}

corresponds to

{{OD}} mm outside diameter.
```

---

# Phase 8 — Execution Engine

The execution engine traverses the graph.

It should NOT render UI.

Responsibilities

```
Traverse nodes

Maintain Workflow State

Resolve parameters

Execute lookups

Execute equations

Generate events
```

---

Events

```
beforeEnter

onEnter

onExecute

onExit

onError
```

---

# Phase 9 — Presentation Engine

Presentation is completely separated.

Responsibilities

```
Render workflow documentation

Render equations

Render lookup outputs

Render warnings

Render tables

Render parameter requests
```

Presentation should consume

```
Knowledge Graph

Workflow State
```

Nothing else.

---

# Phase 10 — Equation Renderer

Equation rendering should use SymPy.

Display

### Step 1

Original equation

### Step 2

Substituted equation

### Step 3

Simplified equation

### Step 4

Final evaluated result

Use symbolic substitution rather than string replacement.

---

# Phase 11 — Node Outputs

Every executable node produces outputs.

Examples

Lookup Node

Produces

```
Outside Diameter

Wall Thickness
```

Equation Node

Produces

```
Required Thickness
```

Selection Node

Produces

```
Selected Material
```

Workflow Node

Produces

```
Completed Task
```

Outputs become inputs for downstream nodes.

---

# Phase 12 — Naming Convention

All nodes must use predictable IDs.

Examples

```
asme_b313

asme_b313_section_304

asme_b313_para_304_1_2

asme_b313_table_302_3_5

asme_b313_table_302_3_5_note_1

asme_b313_figure_328_5

workflow_pipe_thickness

equation_pipe_thickness

lookup_b3610_dimensions

quantity_pressure

designation_nps
```

Avoid arbitrary UUID-based names for built-in graph nodes.

---

# Phase 13 — Report Generation

Report generation is the only stage allowed to use an LLM.

Inputs

```
Workflow State

Visited Nodes

Rendered Equations

Results

Documentation Fields
```

The graph itself should already contain enough structured documentation to allow high-quality reports.

Provide

- a default report template
    
- optional workflow-specific template overrides
    

---

# Final Verification Checklist

Before completing the redesign, verify that:

- Graph nodes are immutable.
    
- Workflow State contains all runtime information.
    
- Quantity nodes never store values.
    
- Units are separated from designations.
    
- Relationship metadata replaces duplicate quantity nodes.
    
- Rendering is separated from execution.
    
- Execution is deterministic.
    
- SymPy performs symbolic evaluation.
    
- Reports are reproducible from Workflow State.
    
- The Knowledge Graph remains reusable across multiple concurrent tasks.