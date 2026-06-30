
## Objective

Refactor only the **physical folder structure** of the Standards knowledge graph.

The internal structure of the node files has already been standardized and **must not be modified** unless absolutely necessary to preserve functionality.

This task is **not** a node schema refactor.

It is purely an organizational refactor to improve maintainability, discoverability, and long-term scalability.

---

# Primary Goals

The new folder structure should:

- Minimize folder traversal.
    
- Reduce the number of nested directories.
    
- Make locating any node nearly instantaneous.
    
- Improve maintainability for both developers and AI agents.
    
- Support future standards (API 570, API 650, API 653, ASME B31.3, etc.).
    
- Preserve all existing application functionality.
    

---

# Flatten the Directory Structure

Avoid deeply nested folder hierarchies such as:

```text
api570/
    chapter/
        section/
            subsection/
                paragraph/
                    node.yaml
```

Instead, organize nodes into a much flatter structure:

```text
standards/
    api570/
        nodes/
            api570_1_1.yaml
            api570_1_2.yaml
            api570_1_3.yaml
            ...
```

The exact naming convention may differ if a better one already exists, but every node should be searchable directly by filename.

A developer should be able to locate a node simply by using the editor's file search (Ctrl+P) without navigating multiple folder levels.

---

# Preserve Existing Node Files

Do **not** edit:

- node metadata
    
- equations
    
- assumptions
    
- parameters
    
- references
    
- datasets
    
- planner information
    
- workflow logic
    

Only relocate files and update any paths or imports required by the application.

---

# Organize Supporting Assets

If standards contain supporting resources such as:

- figures
    
- images
    
- PDFs
    
- annexes
    
- report templates
    

keep these in dedicated folders near the standard root, for example:

```text
standards/
    api570/
        nodes/
        figures/
        annexes/
        reports/
        assets/
```

Do not create unnecessary nesting inside these folders unless there is a clear organizational benefit.

---

# Keep Reusable Resources Centralized

If reusable resources already exist (datasets, shared figures, shared tables, etc.), preserve their centralized location.

Do not duplicate resources simply to match the new folder layout.

---

# Maintain Stable References

After moving files:

- update imports
    
- update relative paths
    
- update loaders
    
- update graph indexing if required
    

No functionality should change.

Existing workflows, planners, graph traversal, and report generation should continue to operate exactly as before.

---

# Remove Unnecessary Nesting

Where possible, eliminate directory structures that only contain a single child folder.

For example, replace:

```text
chapter/
    section/
        subsection/
            paragraph/
```

with a flatter organization that achieves the same result with fewer directory levels.

---

# Optimize for Human Navigation

The folder structure should allow a developer to understand the organization at a glance.

Avoid organizational depth unless it provides meaningful separation.

Favor:

- fewer folders
    
- clear names
    
- predictable locations
    
- consistent naming conventions
    

---

# Verify the Refactor

After completing the reorganization:

1. Verify that every node can still be loaded.
    
2. Verify graph traversal still functions.
    
3. Verify planners still resolve nodes correctly.
    
4. Verify reports still generate.
    
5. Verify no broken file references remain.
    

---

# Deliverables

1. Analyze the current Standards directory.
    
2. Identify unnecessary folder depth.
    
3. Propose a flatter directory layout before making changes.
    
4. Perform the refactor incrementally.
    
5. Update all affected paths.
    
6. Remove obsolete directories.
    
7. Verify that the application behaves exactly as before.
    
8. Produce a summary describing:
    
    - the old structure,
        
    - the new structure,
        
    - files moved,
        
    - references updated,
        
    - any architectural decisions made.
        

## Important Constraint

The goal is **not** to redesign the knowledge graph or modify node content.

The goal is to create a clean, shallow, scalable folder structure that minimizes navigation while preserving all existing functionality and making future maintenance easier.