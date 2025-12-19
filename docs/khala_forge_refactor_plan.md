# Khala Agentmemory: Forge Refactoring Implementation Plan

## Goal
Transform the highly sophisticated but fragmented Khala documentation into a unified, **Forge Methodology** structure. This establishes a clear "Operating System" for AI agents while preserving 100% of the research and planning intelligence already present.

## Safeguard Strategy
> [!IMPORTANT]
> **No deletion before archival.** Every file targeted for modification or relocation will first be copied to `packages/khala-agentmemory/docs/_archive` to ensure historical continuity.

## Proposed Changes

### 1. Archival & Cleanup
- **Target**: All files in `packages/khala-agentmemory/docs/`, `packages/khala-agentmemory/rules/`, and `packages/khala-agentmemory/tasks/`.
- **Action**: Move existing versions to `docs/_archive` (categorized by source if necessary).

---

### 2. The Core Files (Root)

#### [MODIFY] [AGENTS.md](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/AGENTS.md)
- **Content**: Integrate `rules/00-prime-directives.md` into the current structure.
- **Rules**: Explicitly state the FORGE workflow and the "Hierarchy of Truth".

#### [MODIFY] [README.md](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/README.md)
- **Optimization**: Convert the 170+ strategy list into groups with `<details><summary>` tags.
- **Benefit**: Retains all 170 strategies while making the README scannable.

---

### 3. The Knowledge Warehouse (`docs/`)

#### [NEW] [01-plan.md](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/docs/01-plan.md)
- **Integration**: Unify content from:
    - `01-plans-memodb-harvest.md`
    - `01-plans-surrealist.md`
    - `01-plans-UI.md`
    - `khala_codebase_analysis.md`
- **Result**: A single source of truth for Khala's strategic direction.

#### [NEW] [02-tasks.md](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/docs/02-tasks.md)
- **Integration**: Merge all legacy tasklists and the `tasks/` folder specs into a unified backlog.

#### [MODIFY] [03-architecture.md](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/docs/03-architecture.md)
- **Integration**: Align legacy architecture rules with the Forge "Domain/Port" format.

#### [NEW] [06-rules.md](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/docs/06-rules.md)
- **Integration**: Consolidation of coding rules from `rules/03-coding.md` and the audit results.

## Verification Plan
1. **Link Integrity**: Check all internal markdown links to ensure they point to the new structure.
2. **Context Loading Test**: Perform a "Mock Session Start" where I (the agent) read `AGENTS.md` and verify I can find all critical information (Models, DB schema, Tasks) via the new paths.
3. **UI Review**: Verify `README.md` rendering (collapsible sections).
