# Khala Agentmemory Guide Status Report

## Current Documentation State
The VIVI OS guide provides a high-level overview of Khala but fails to capture the technical depth and the "Cognitive Protocols" that make the library unique.

## Coverage Gaps

### 1. Advanced Services Documentation
- **Missing**: Detailed guides for `DreamService`, `HypothesisService`, and `FlowOrchestrator`.
- **Recommendation**: Create a "Cognitive Protocols" section in the guide explaining how to trigger dreams, simulate counterfactuals, and test hypotheses.

### 2. 170-Protocol Transparency
- **Missing**: A clear mapping between the 170 strategies mentioned in `README.md` and their implementation files/classes.
- **Recommendation**: Add a "Capability Matrix" to the guide for developers to know which strategies are ready for production versus experimental.

### 3. Developer Onboarding (Khala-specific)
- **Issue**: The `06-developer-guide.md` is too generic for Khala.
- **Missing**:
    - How to define a new `MemoryTier`.
    - How to extend the SurrealDB schema for new research fields.
    - Example of a "Consolidation Loop" configuration.

### 4. SurrealDB Deep-Dive
- **Missing**: Explanation of the `khala` namespace vs the `infra` namespace in SurrealDB.
- **Recommendation**: Clarify that `khala` contains the "Agentic Brain" while `infra` contains the "Operational Library".

## Technical Depth Alignment
- **Architecture**: The "Dual-Layer" philosophy needs to be tied directly to the code (Khala as the Kernel's memory).
- **Security**: The `Aboyeur` protocol role in "Sanitizing" memories before they enter Khala is not explained in the developer guide.

## Suggested Improvements
1. **New Guide Chapter**: `08-khala-deep-dive.md` covering the memory hierarchy, search strategies (Hybrid/Graph), and cognitive services.
2. **Visual Traces**: Add "Trace of a Memory" - from creation via `create_khala_agent`, through extraction/verification, to long-term consolidation.
3. **Reference API**: Generate Pydantic/Dataclass references for the `Memory` and `Flow` entities to use as a cheat sheet.
