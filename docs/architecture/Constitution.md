## Law 1 — Separation of Knowledge and Execution

Engineering knowledge is immutable and independent of execution. Runtime state, calculations, and user data must never be stored within the knowledge graph.

## Law 2 — Knowledge Before Data

Engineering concepts exist independently of any project. Projects create Facts about concepts but never redefine the concepts themselves.

## Law 3 — Single Responsibility of Knowledge Nodes

Each node represents exactly one independently meaningful engineering concept. Nodes should never bundle multiple unrelated responsibilities.

## Law 4 — Explicit Relationships

All relationships between nodes must be explicit and semantically typed. Meaning must arise from relationships rather than hidden assumptions.

## Law 5 — Planner Orders Navigation; Graph Determines Active Requirements

The Planner translates Goals into a plan and orders the next missing information. Graph expansion determines which engineering requirements, branches, and parameter asks are active. The Planner reasons over knowledge but never performs execution or alone defines engineering truth.

## Law 6 — Execution is Deterministic

Given identical knowledge, Goals, and Facts, the execution engine must always produce the same execution path and results.

## Law 7 — Runtime State Lives in the Execution Context

Temporary values, user inputs, execution history, Goals, and Facts belong exclusively to the Execution Context and never modify the knowledge graph.

## Law 8 — Knowledge is Reusable

Knowledge nodes must be reusable across projects, standards, workflows, and engineering domains without duplication.

## Law 9 — Standards Reference Knowledge

Standards, paragraphs, equations, and workflows reference engineering concepts. They should not redefine concepts that already exist within the ontology.

## Law 10 — Dependencies Drive Execution

Execution proceeds by satisfying dependencies rather than following hard-coded procedures. Every dependency should be represented explicitly within the graph.
## Law 11 — Authority Governs Decisions

Engineering decisions must always be traceable to authoritative sources such as standards, regulations, or approved company practices.

## Law 12 — Explanation is a First-Class Output

The system must always be capable of explaining how a conclusion was reached by tracing the complete chain of evidence and reasoning.

## Law 13 — Goals Drive the System

Every execution begins with one or more engineering Goals. Goals determine which parts of the knowledge graph become relevant during execution.

## Law 14
Facts are append-only. Corrections create new Facts rather than modifying existing ones.
## Law 15 
Decision Separation Principle:
 ```
The Planner decides _what is needed 
The Kernel decides _what happens next
 ```

**Planner:**
```
- understands goals
- builds navigation plan and orders next missing information
- interacts with graph expansion output
- does not alone determine active engineering requirements
```


**Kernel:**

```
- schedules execution
- stores facts
- manages concurrency
- tracks state
```


## Law 16 
Documents bundle knowledge; graphs separate knowledge into its atomic concepts and reconnect them through explicit relationships.
## Law 17
Every engineering concept has one canonical identity. All contextual variations reference that identity rather than redefining it.
## Law 18 
Canonical definitions must remain stable; contextual meaning must never overwrite identity.

If meaning changes:

- create a new concept
- or create a contextual alias
- but never mutate the core identity

## Law 19 
Every node must justify its existence through at least one of:

- inference usage
- workflow participation
- reference relationships
- explanatory relevance

If not, it is a candidate for deprecation.
## Law 20 
High-centrality nodes must be decomposed into role-based contexts. 

## Law 21
The graph must remain stateless; all runtime data belongs exclusively to Execution Context.

## Law 22 - Inference Expands Possibility; Execution Produces Reality

This law separates two very different activities:

- Inference discovers what _could_ or _must_ happen.
- Execution creates Facts about what _did_ happen.

Keeping these separate prevents reasoning from becoming entangled with runtime state.

# Law 23 — Authority Determines Applicability

 ```
Engineering knowledge defines what is possible.
 
Authority determines what is permitted within a specific engineering context.
 ```




# Metrics of Graph Health

If we want Cursor to help maintain this system, we need measurable signals.

## 1. Concept Duplication Rate

“How many nodes represent the same idea?”

## 2. Reference Coverage

“What % of nodes are actually used?”

## 3. Centrality Distribution

“Are a few nodes dominating reasoning?”

## 4. Semantic Distance Consistency

“Do similar concepts behave consistently across standards?”

## 5. Execution Reachability

“Can every output be derived from a valid goal path?”