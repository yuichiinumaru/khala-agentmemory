# 01-PLANS-SEMANTIC-ROUTER.md: Intent Classification & Routing Upgrade

**Status**: PROPOSED
**Driver**: Semantic Router Integration
**Target**: `khala/infrastructure/semantic_router`

## 1. Context & Problem
The current `IntentClassifier` relies on direct LLM calls (Gemini) for every query.
- **Latency**: High (~1-2s).
- **Cost**: Per-query generation cost.
- **Reliability**: Non-deterministic.

The `semantic-router` library (from Aurelio Labs) offers a vector-based routing layer that is orders of magnitude faster and deterministic. It matches user queries to "Routes" (collections of utterances) using embedding similarity.

## 2. Solution: Hybrid Route Layer
We will integrate `semantic-router` to handle:
1.  **Intent Classification**: Mapping user queries to `QueryIntent` (FACTUAL, SUMMARY, etc.).
2.  **Skill Routing (Future)**: Mapping queries to specific tool executions (Dynamic Routes).

## 3. Architecture

### A. Infrastructure Layer (`khala/infrastructure/semantic_router/`)
- `KhalaRouter`: A wrapper around `semantic_router.SemanticRouter`.
- `RouteFactory`: Creates standard routes from our `QueryIntent` definitions.
- **Constraint**: Must use our existing Embedding infrastructure (Gemini) where possible, or use `semantic-router`'s compatible encoders.

### B. Application Layer (`khala/application/services/`)
- `FastIntentClassifier`: A new implementation of the intent classifier using `KhalaRouter`.
- Falls back to LLM-based classifier if `KhalaRouter` returns `None` (Hybrid Approach).

### C. Domain Layer (`khala/domain/`)
- No changes required to core entities. `QueryIntent` enum remains the source of truth.

## 4. Harvested Modules
From `semantic-router` repo, we are adopting:
- **`RouteLayer` (SemanticRouter)**: The core logic for embedding-based classification.
- **`Route`**: The data structure for defining intents with utterances.
- **`HybridRouteLayer` (Concept)**: Combining keyword (sparse) and semantic (dense) search for better accuracy (optional but valuable).

## 5. Implementation Steps
1.  **Dependency**: Add `semantic-router` to `requirements.txt`.
2.  **Adapter**: Implement `KhalaRouter` in infrastructure.
3.  **Routes**: Define utterance sets for each `QueryIntent`.
4.  **Integration**: Wire `FastIntentClassifier` into `HybridSearchService`.
