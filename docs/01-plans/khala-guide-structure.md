# Khala User & Developer Guide Structure (Plan)

Following the VIVI-OS standard, we will establish `packages/khala-agentmemory/guide/` as the primary entry point for **Users** (Agents/Developers consuming the lib), while `docs/` remains the **Internal** engine room.

## Directory Structure: `packages/khala-agentmemory/guide/`

### `00-index.md` (The Manifesto)
- **Goal**: High-level introduction. "What is Khala?"
- **Content**: The "Shared Consciousness" vision, quick links, and "How to read this guide".

### `01-getting-started.md` (Warp-In)
- **Goal**: Zero to Hero in 5 minutes.
- **Content**:
    - Installation (`pip install -e .`).
    - Basic Config (`.env` setup).
    - "Hello World" (Initializing an Agent and storing a memory).

### `02-architecture-overview.md` (The Map)
- **Goal**: The "Big Picture" for consumers.
- **Content**:
    - Simplified diagram of providing/consuming memories.
    - Explanation of the 3 Tiers (Hot/Warm/Cold) from a *usage* perspective.
    - The "Graph" concept explained simply.
    - **Namespace Distinction**: `khala` (Agent Brain) vs `infra` (Operational).

### `03-core-concepts.md` (The Glossary)
- **Goal**: Terminology alignment.
- **Content**:
    - "Entity" vs "Memory" vs "Episode".
    - "Consolidation" (Dreaming).
    - "Entropy" (Decay).
    - "Flows" (Deterministic actions).

### `04-features-and-capabilities.md` (The Menu)
- **Goal**: What can I do with this?
- **Content**:
    - List of the 170 strategies (grouped high-level).
    - **Capability Matrix**: Production Ready vs Experimental status.
    - Highlights: Hybrid Search, Graph Traversal, Intent Classification.

### `05-configuration-reference.md` (The Knobs)
- **Goal**: Fine-tuning.
- **Content**:
    - All environment variables (`KHALA_SURREAL_URL`, `GEMINI_API_KEY`).
    - Model selection (`MODELS_MAPPING`).
    - Cache settings.

### `06-developer-guide.md` (The API)
- **Goal**: How to integrate Khala into other Agents.
- **Content**:
    - `KHALAAgent` public methods.
    - `KHALAMemoryProvider` interface.
    - MCP Server usage.
    - **Advanced**: How to extend the SurrealDB Schema.
    - **Note**: This links to `docs/06-rules.md` for *internal* contributors, but focuses on *integration* for external devs.

### `07-troubleshooting.md` (The Medic)
- **Goal**: Fix common issues.
- **Content**:
    - "SurrealDB connection refused".
    - "Gemini API Quota Exceeded".
    - "Memory not persisting".

## Relationship with `docs/`
- `guide/` = **USER FACING** (How to drive the car).
- `docs/` = **MAINTAINER FACING** (How to build the engine).
- `README.md` = **Marketing Landing Page** (Links to `guide/00-index.md`).
