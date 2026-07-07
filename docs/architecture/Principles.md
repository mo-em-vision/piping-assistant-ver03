
## Lecture 1 — Knowledge vs Documents

1. Engineering standards are documents, not knowledge models.
2. Documents bundle concepts together for human reading.
3. Knowledge graphs separate those concepts into reusable nodes.
4. Paragraphs become authoritative references rather than containers of all engineering logic.
5. The graph models engineering meaning rather than document structure.

## Lecture 2 — State Machines

1. Engineering execution progresses through states.
2. Nodes themselves remain stateless.
3. Runtime objects move through well-defined state transitions.
4. Explicit state machines improve traceability and deterministic execution.
5. State belongs to execution, not knowledge.


## Lecture 3 — Runtime vs Knowledge

1. Separate immutable engineering knowledge from mutable runtime information.
2. Knowledge can exist without users or projects.
3. Runtime state exists only while solving engineering problems.
4. Knowledge should never depend on previous executions.
5. Execution consumes knowledge without modifying it.

## Lecture 4 — The Ontology

1. The ontology defines engineering concepts.
2. Concepts are independent of standards.
3. Standards reference ontology concepts.
4. Engineering meaning belongs to ontology nodes.
5. The ontology provides semantic consistency across the entire graph.


## Lecture 5 — Parameters

1. Parameters define engineering concepts rather than values.
2. Parameters contain definitions, dimensions, compatible units, and semantic identity.
3. Parameter values are never stored inside Parameter nodes.
4. Aliases belong to contexts rather than creating new Parameters.
5. Parameter nodes remain reusable across every engineering domain.

## Lecture 6 — Facts

1. Facts are runtime instances of Parameters.
2. Facts combine concepts with values.
3. Facts record provenance.
4. Facts belong to the Execution Context.
5. Facts may be persisted within Projects while remaining separate from knowledge.
6. Parameters remain immutable while Facts evolve.

## Lecture 7 — The Graph as a Compiler

1. User requests are transformed into engineering execution plans.
2. The planner translates user intent into goals and orders the next missing information.
3. Graph expansion determines active engineering requirements, branches, and parameter asks.
4. Execution plans resemble compiler execution plans.
5. Knowledge representation and execution remain separate.
6. Optimization occurs by minimizing unnecessary reasoning and user interaction.

## Lecture 8 — The Life of a Parameter

1. Parameters exist before projects.
2. Projects create Facts about Parameters.
3. Equations consume Facts rather than Parameters directly.
4. Derived values become new Facts.
5. Reports present Facts rather than graph nodes.
6. Parameter identity never changes throughout execution.
7. Engineering reasoning operates over Facts while preserving immutable concepts.


# Lecture 9  

1. **Facts are runtime evidence**, not engineering concepts.
2. **Parameters define concepts; Facts assign values to those concepts.**
3. **Facts are append-only.** Corrections create new Facts; old Facts are superseded, never deleted.
4. Every Fact must have provenance:
    - Concept (Parameter)
    - Value
    - Unit
    - Source
    - Timestamp
    - Execution
    - Workflow
    - Justification
    - Superseded status
5. Derived Facts record exactly which Facts and rules produced them.
6. The knowledge graph remains immutable; Facts belong to the Execution Context and optionally persist into Projects.
7. Engineering results should always be explainable by tracing the chain of evidence back to its origins.
# Lecture 10  

1. Goals are runtime objects, not strings.
2. Goals belong to the Execution Context, not the knowledge graph.
3. Every engineering request begins with one or more top-level Goals.
4. Goals expand into child Goals through dependency resolution.
5. Goals form a tree that the planner satisfies recursively.
6. Workflows do not define Goals; they constrain how Goals may be achieved.
7. A Goal is complete when its required outputs exist as valid Facts.
8. Multiple Goals may share the same Facts, avoiding duplicate work.
9. The planner is goal-driven rather than graph-driven.
10. The LLM identifies Goals; the deterministic engine satisfies them.
# Lecture 11   

1. The Execution Kernel is the runtime engine of the system.
2. The kernel is responsible for execution, not reasoning.
3. The graph defines knowledge; the kernel enforces execution.
4. Multiple independent Goal Trees can run concurrently.
5. Goal Trees share Facts across Execution Context.
6. The kernel schedules Goal execution but does not determine engineering logic.
7. Facts are globally deduplicated within an Execution Context where provenance matches.
8. Conflicting Facts are preserved, not overwritten.
9. Conflict resolution is handled by authority/workflow rules, not the kernel.
10. The kernel ensures deterministic execution order given the same inputs.

# Lecture 12   

1. Planner and Kernel must be strictly separated.
2. Planner operates in logical space (what should happen).
3. Kernel operates in physical space (what does happen).
4. Graph defines knowledge; it must not execute or schedule.
5. Planner expands Goals and defines dependencies.
6. Kernel schedules execution and manages runtime state.
7. Planner cannot modify Facts directly.
8. Kernel cannot interpret engineering meaning or standards.
9. Communication occurs only via Execution Requests.
10. Kernel responses are state-based: Executed, Blocked, Deferred, Conflict.
11. Planner explores possibilities; Kernel actualizes outcomes.
12. System scalability depends on maintaining this separation.
# Lecture 14  

1. Identity is independent of a node's name.
2. Every reusable engineering concept should have one canonical node.
3. Aliases describe different names for the same identity; they do not create new concepts.
4. Context (for example, "Internal" in "Internal Pressure") belongs to the referencing node, not the canonical Parameter.
5. Before creating a node, the system should check whether the concept already exists.
6. Paragraphs and standards reference canonical concepts; they do not own or duplicate them.
7. IDs should be stable and independent of filenames or display names.
8. Identity persists across revisions; revisions update content without changing identity.
9. A semantic registry should govern node creation to prevent duplicate concepts.
10. Canonical identities are the foundation of deterministic reasoning and long-term graph consistency.
# Lesson 15

1. The knowledge graph behaves as a living ecosystem, not a static structure.
2. Graph health is defined by semantic clarity, consistency, and navigability.
3. Semantic drift occurs when node meaning changes over time without identity separation.
4. Orphan nodes are unused concepts that must be detected and reviewed.
5. Over-connected nodes reduce clarity and must be decomposed into contextual roles.
6. Semantic clusters should remain internally dense but externally minimal.
7. The graph must remain stateless; all runtime data belongs to Execution Context.
8. Execution state must never contaminate knowledge nodes.
9. A Graph Immune System should detect structural and semantic degradation.
10. The system should flag issues rather than silently correcting them.
11. Graph health metrics are necessary for long-term scalability and trust.


# Lecture 16

1. Search, inference, and reasoning are distinct operations.
2. The graph stores engineering possibilities, not finished answers.
3. Inference expands Goals into dependencies without creating Facts.
4. Backward inference starts from desired outputs and discovers required inputs.
5. Forward inference propagates new Facts through dependent calculations.
6. Applicability conditions are evaluated during inference.
7. The planner performs deterministic navigation using the graph; it does not guess engineering truth.
8. Graph expansion determines which requirements are active on the current path.
9. The LLM interprets user intent but does not perform engineering reasoning.
10. The Inference Frontier identifies the next missing Fact required for progress.
11. User interaction should request only the minimum information needed to advance inference.
12. **Law 22 — Inference expands possibility; execution produces reality.**

# Lecture 17

1. Knowledge and authority are separate but interconnected domains.
2. Mathematical validity does not imply engineering applicability.
3. The graph contains both a Knowledge Graph and an Authority Graph.
4. Authority determines which engineering knowledge is applicable in a given context.
5. Authority forms a layered hierarchy (regulations, standards, company policies, project specifications, etc.).
6. Workflows execute within the constraints established by authority.
7. User assumptions must be validated against the active Authority Context.
8. Company standards often refine, rather than conflict with, higher-level standards.
9. Conflicts between authorities should be resolved by explicit authority hierarchy rules.
10. An Authority Context defines the active governing sources for a project.
11. Engineering explanations should include both the reasoning chain and the authority chain.
12. **Law 23 — Authority determines applicability. Knowledge determines possibility.**