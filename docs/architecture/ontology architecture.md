# Ontology Architecture

## Purpose

This document defines the conceptual ontology of the Engineering Operating System.

Unlike the implementation documents, this document does **not** describe software components, execution order, or project structure.

Instead, it defines the fundamental engineering concepts that exist within the system and the relationships between them.

Every schema, algorithm, workflow, and software component should ultimately derive from this ontology.

---

# Core Principle

The Engineering Operating System is **not** a workflow engine.

It is **not** a calculation engine.

It is **not** an AI assistant.

It is an Engineering Knowledge System capable of reasoning over reusable engineering knowledge to produce deterministic engineering conclusions.

---

# Philosophy

Engineering knowledge exists independently of any project.

Projects merely apply engineering knowledge to specific situations.

Therefore the architecture separates:

- Knowledge
- Runtime State
- Execution
- Presentation

These layers must never become coupled.

---

# The Four Layers

```
Engineering Knowledge

↓

Planning & Reasoning

↓

Execution

↓

Presentation
```

Only the Execution layer contains mutable runtime state.

Knowledge remains immutable.

---

# Knowledge Ontology

The Engineering Operating System represents engineering knowledge using reusable canonical concepts.

These concepts exist independently of any engineering standard.

Standards reference these concepts.

Projects instantiate these concepts.

---

# Canonical Knowledge Objects

The ontology consists of the following primary objects.

## Dimension

Represents a measurable physical dimension.

Examples:

- Pressure
- Length
- Temperature
- Time
- Mass
- Force

A Dimension defines:

- compatible units
- canonical unit
- dimensional compatibility

A Dimension never stores values.

---

## Unit

Represents a measurement unit.

Examples:

- Pa
- psi
- MPa
- mm
- inch
- Kelvin

A Unit belongs to exactly one Dimension.

A Unit defines:

- symbol
- conversion
- aliases

Units never belong to Parameters.

---

## Parameter

Represents an engineering concept.

Examples:

- Design Pressure
- Corrosion Allowance
- Outside Diameter
- Material Specification

A Parameter defines:

- semantic identity
- engineering meaning
- dimension
- aliases

Parameters never store values.

Parameters are reusable across standards.

---

## Equation

Represents deterministic engineering relationships.

Examples:

```
t = PD / 2(SEW + PY)
```

An Equation:

- consumes Parameters
- produces Parameters
- contains no runtime values

---

## Authority

Represents the origin of engineering knowledge.

Examples:

- ASME B31.3
- API 570
- ASTM A106

Authorities never perform calculations.

Authorities define engineering requirements.

---

## Paragraph

Represents a specific authoritative statement.

Paragraphs:

- belong to Authorities
- introduce Parameters
- reference Equations
- define limitations
- define assumptions
- define applicability

Paragraphs are sources of engineering authority.

They are not runtime objects.

---

## Workflow

Represents an engineering objective.

Examples:

- Pipe Wall Thickness Design
- Integrity Assessment
- Pressure Test

A Workflow defines:

- engineering goal
- required reasoning path

Workflows never contain engineering values.

---

# Runtime Ontology

Runtime objects represent engineering execution.

They are created for specific projects.

---

## Goal

Represents an engineering objective requested by the user.

Examples:

- Verify pipe thickness
- Calculate MAWP
- Determine allowable stress

Goals exist only during execution.

---

## Fact

Represents a known engineering value.

Examples:

```
Design Pressure = 8 bar

Material = ASTM A106 Grade B

Required Thickness = 8.23 mm
```

Facts contain:

- value
- provenance
- confidence
- timestamp
- source

Facts may be:

- user supplied
- calculated
- imported
- looked up

---

## Execution Context

Represents runtime state.

Contains:

- active goals
- active facts
- completed calculations
- assumptions
- warnings

Execution Context is mutable.

---

## Authority Context

Represents the currently active engineering references for one task execution.

Runtime implementation: [`models/authority_context.py`](../../models/authority_context.py) on each `Task` (peer to `execution_context`). Reference: [`audits/contracts/runtime/authority-context.md`](../../audits/contracts/runtime/authority-context.md).

Example:

```
ASME B31.3 2024

ASTM A106

ASME B36.10
```

This context determines which authoritative knowledge is applicable during execution.

---

## Authority Node

Immutable canonical authoritative sources (`AUTH-*`) in [`knowledge/global/authorities/`](../../knowledge/global/authorities/).

Contract: [`audits/contracts/nodes/authority.md`](../../audits/contracts/nodes/authority.md). Canonical type `authority` in [`engine/reference/node_types.py`](../../engine/reference/node_types.py).

Authority nodes define **what sources exist**. Authority Context selects **which sources are active** for one execution.

---

# Relationship Model

```
Dimension

↓

Unit

↓

Parameter

↓

Equation

↓

Fact

↓

Goal

↓

Workflow
```

Authority exists orthogonally.

```
Authority

↓

Paragraph

↓

Parameter

↓

Equation

↓

Workflow
```

Projects never modify Authority.

---

# Separation of Concerns

Knowledge objects never contain runtime state.

Runtime objects never redefine knowledge.

Examples:

A Parameter never stores:

- value
- source
- timestamp

A Fact never defines:

- engineering meaning
- unit compatibility
- aliases

A Paragraph never stores:

- execution status
- user inputs
- calculated values

---

# Execution Philosophy

The planner reasons over knowledge.

The execution engine reasons over facts.

The report generator explains the relationship between facts and knowledge.

---

# Traceability

Every engineering conclusion must be traceable through four chains.

## Knowledge Chain

```
Parameter

↓

Equation

↓

Paragraph

↓

Authority
```

---

## Execution Chain

```
Goal

↓

Facts

↓

Execution

↓

Results
```

---

## Provenance Chain

```
Fact

↓

Source

↓

Timestamp

↓

Evidence
```

---

## Explanation Chain

```
Question

↓

Reasoning

↓

Calculation

↓

Conclusion
```

---

# Future Extensions

The ontology intentionally supports future expansion.

Additional knowledge objects may include:

- Material
- Component
- Fluid
- Geometry
- Hazard
- Failure Mode
- Inspection Method
- Equipment

These should inherit from the same architectural principles without changing the existing ontology.

---

# Final Principle

The Engineering Operating System separates immutable engineering knowledge from mutable engineering execution.

Knowledge defines what is true.

Goals define what is desired.

Facts define what is known.

The Planner orders what to ask next from Goals and the engineering plan.

Graph expansion determines which requirements are active on the current path.

The Execution Layer determines what can be calculated.

The Report explains why the conclusion is correct.

Everything is reproducible, traceable, and grounded in authoritative engineering knowledge.