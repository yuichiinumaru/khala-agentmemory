# Implementation Plan for Remaining Strategies

This document outlines the roadmap for implementing the remaining ~79 strategies for the KHALA memory system.

## Summary of Status
*   **Total Strategies:** 170
*   **Implemented:** ~91 (Core, Infrastructure, Basic Logic)
*   **Remaining:** ~79 (Advanced Logic, Optimizations, Research)

## Phase 1: Quick Wins & Schema Refinements (Low Complexity)
*Focus: Maximizing feature count with minimal architectural changes.*

### 1.1 Metadata & Schema Enhancements
- [ ] **17. Natural Memory Triggers**: Add heuristic checks in `MemoryLifecycleService.ingest` (e.g., "remember that...").
- [ ] **31. Significance Scoring**: Implement `SignificanceScorer` service to rate memory importance (0.0-1.0) on ingestion.
- [ ] **37. Emotion-Driven Memory**: Add `sentiment` analysis via Gemini and store in `metadata.sentiment`.
- [ ] **63. Conditional Content Fields**: Add logic to store `summary` vs `full_content` based on length > 1000 chars.
- [ ] **68. Weighted Directed Multigraph**: Add `weight` field to `relationship` table and API methods to update it.
- [ ] **70. Bidirectional Relationship Tracking**: Ensure `create_relationship` automatically creates the inverse edge or marks as bidirectional.
- [ ] **141. Keyword Extraction Tagging**: Integrate a simple keyword extractor (YAKE/Rake) or LLM call to auto-populate `tags`.
- [ ] **147. Negative Constraints**: Add a `negative_constraints` list to `AgentProfile` to filter out specific topics/memories.

### 1.2 Basic Search & Retrieval Tweaks
- [ ] **30. Query Intent Classification**: Add `IntentClassifier` to `HybridSearchService` (Fact vs. Summary vs. Analysis).
- [ ] **32. Multi-Perspective Questions**: Generate 3 variations of user query in `QueryExpansionService`.
- [ ] **96. Typo Tolerance**: Enable `FUZZY` matching in SurrealDB BM25 queries.
- [ ] **101. Search History Suggestions**: Store successful queries in `search_session` and expose autocomplete API.

## Phase 2: Intelligence & Logic Expansion (Medium Complexity)
*Focus: Adding new services and logic flows without major infra overhaul.*

### 2.1 Agent Cognition
- [ ] **36. Instruction Registry**: Create `InstructionRepository` to version and retrieve system prompts.
- [ ] **46. Standard Operating Procedures (SOPs)**: Implement `SOPService` to ingest and execute structured JSON workflows.
- [ ] **54. Hypothesis Testing Framework**: Create `HypothesisService` where agents formulate and verify theories against memory.
- [ ] **55. Context-Aware Tool Selection**: Dynamic loading of MCP tools based on current memory context (tags/vectors).
- [ ] **127. Structured LLM Output**: Enforce strict JSON schemas (Pydantic) for all LLM extractions.
- [ ] **131. Socratic Questioning**: Implement logic to detect low-confidence answers and generate follow-up questions to the user.
- [ ] **154. User Modeling**: Create `UserProfileService` to explicitly build and update user preferences/traits.

### 2.2 Advanced Search & Graph
- [ ] **50. Cross-Modal Retrieval**: Implement text-to-image search using existing Multi-Modal embeddings.
- [ ] **76. Explainability Graph**: Store reasoning traces as graph paths (nodes=steps, edges=logic).
- [ ] **97. Contextual Search**: Implement proximity search (terms appearing within N words).
- [ ] **98. Faceted Search**: Aggregation queries to count memories by Tier, Type, Agent.
- [ ] **124. Multi-Hop Constraints**: Enforce a `max_depth=3` limit on graph traversal to prevent hallucinations.
- [ ] **142. Entity Disambiguation**: Logic to merge entities with same name but different context (via Vector distance).

### 2.3 Time & Forensics
- [ ] **41. Bi-temporal Graph Edges**: Fully expose `valid_time` vs `transaction_time` in the Graph API.
- [ ] **104. Agent Activity Timeline**: Logging all agent-memory interactions to a time-series table.
- [ ] **108. Learning Curve Tracking**: Measure and plot `verification_score` trends over time.

## Phase 3: Advanced Optimization & Infrastructure (High Complexity)
*Focus: Performance, Scale, and Specialized Math.*

### 3.1 Vector Optimization
- [ ] **79. Vector Quantization**: Implement logic to compress vectors (float32 -> int8) for storage efficiency.
- [ ] **80. Vector Drift Detection**: Background job to compare old vs. new embedding model outputs.
- [ ] **81. Vector Clustering & Centroids**: Pre-calculate centroids for fast coarse-grained search.
- [ ] **83. Vector-Space Anomaly Detection**: Identify memories that are outliers (high distance from centroids).
- [ ] **84. Vector Interpolation**: Logic to generate "bridge" concepts between two distant memories.
- [ ] **89. Vector Ensemble**: Average embeddings from multiple models (e.g., Gemini + OpenAI) for robustness.
- [ ] **159. Self-Healing Index**: Background job to re-index or re-embed memories with low retrieval rates.

### 3.2 Geospatial & Graph Theory
- [ ] **111. Agent Location Context**: Schema update and logic to tag memories with `(lat, long)`.
- [ ] **113. Concept Cartography**: Project high-dim vectors to 2D (UMAP/t-SNE) for UI visualization.
- [ ] **143. Community Detection**: Implement Louvain or Label Propagation in SurrealDB (or python-side) to find clusters.
- [ ] **145. Pathfinding Algorithms**: A* or Dijkstra implementation for finding connections between concepts.
- [ ] **146. Subgraph Isomorphism**: Search for specific structural patterns (e.g., "Problem -> Solution").

### 3.3 System Resilience
- [ ] **44. Distributed Consolidation**: Use Redis/Celery to shard the consolidation job across multiple workers.
- [ ] **126. Semaphore Concurrency Limiting**: Global rate limiter for LLM calls.
- [ ] **132. Privacy-Preserving Sanitization**: PII Redaction service (regex + LLM) before storage.
- [ ] **156. Version Control**: Git-like branching/forking for memory states (complex schema change).

## Phase 4: Deep Research & Experimental (Very High Complexity)
*Focus: Novel implementations requiring significant R&D.*

- [ ] **129. Dream-Inspired Consolidation**: Generative replay of daily memories to form loose associations.
- [ ] **130. Counterfactual Simulation**: Generating and storing "What if" scenarios for decision support.
- [ ] **139. Contextual Bandits**: RL agent to tune retrieval parameters (k, alpha) based on user feedback.
- [ ] **149. Transient Scratchpads**: In-memory (Redis) ephemeral storage for complex multi-turn reasoning.
- [ ] **167. Network Topology Validation**: Benchmarking tool for agent network efficiency (AgentsNet).
- [ ] **168. Meta-Reasoning (Dr. MAMR)**: Implementing the full Manager-Agent-Manager-Reflector loop.

## Metrics for Completion
*   **Progress Tracking**: Update `docs/02-tasks-implementation.md` weekly.
*   **Definition of Done**: Code implemented + Unit Test + Integration Test + Documentation.
