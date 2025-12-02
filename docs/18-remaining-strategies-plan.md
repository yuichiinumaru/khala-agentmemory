# Implementation Plan for Remaining Strategies

This document outlines the roadmap for implementing the remaining strategies for the KHALA memory system.

## Summary of Status
*   **Total Strategies:** 170
*   **Implemented:** ~60-70 (Core, Infrastructure, Basic Logic)
*   **Remaining:** ~100-110 (Advanced Logic, Optimizations, Research)

## Phase 1: Quick Wins & Schema Refinements (Low Complexity)
*Focus: Maximizing feature count with minimal architectural changes.*

### 1.1 Metadata & Schema Enhancements
- [ ] **17. Natural Memory Triggers**: Add heuristic checks in `MemoryLifecycleService.ingest` (e.g., "remember that...").
- [ ] **20. Monitoring & Health Checks**: Expand health checks to include queue depth and cache hit rates.
- [ ] **31. Significance Scoring**: Implement `SignificanceScorer` service to rate memory importance (0.0-1.0) on ingestion.
- [ ] **37. Emotion-Driven Memory**: Add `sentiment` analysis via Gemini and store in `metadata.sentiment`.
- [ ] **59. Polymorphic Memory Documents**: Formalize types for Fact vs Code vs Decision.
- [ ] **63. Conditional Content Fields**: Add logic to store `summary` vs `full_content` based on length > 1000 chars.
- [ ] **64. Schema-Flexible Metadata**: Utility to validate arbitrary metadata against JSON schema.
- [ ] **65. Document-Level Transactions**: Helper to wrap update+history+event in one transaction.
- [ ] **68. Weighted Directed Multigraph**: Add `weight` field to `relationship` table and API methods to update it.
- [ ] **70. Bidirectional Relationship Tracking**: Ensure `create_relationship` automatically creates the inverse edge or marks as bidirectional.
- [ ] **120. Custom Pydantic Entity Types**: Enforce strict typing on entity metadata.
- [ ] **141. Keyword Extraction Tagging**: Integrate a simple keyword extractor (YAKE/Rake) or LLM call to auto-populate `tags`.
- [ ] **147. Negative Constraints**: Add a `negative_constraints` list to `AgentProfile`.

### 1.2 Basic Search & Retrieval Tweaks
- [ ] **30. Query Intent Classification**: Add `IntentClassifier` to `HybridSearchService` (Fact vs. Summary vs. Analysis).
- [ ] **32. Multi-Perspective Questions**: Generate 3 variations of user query in `QueryExpansionService`.
- [ ] **94. Linguistic Analysis**: Store POS tags to improve keyword matching.
- [ ] **96. Typo Tolerance**: Enable `FUZZY` matching in SurrealDB BM25 queries.
- [ ] **101. Search History Suggestions**: Store successful queries in `search_session` and expose autocomplete API.
- [ ] **153. Intent-Based Prefetching**: Heuristic to pre-load related memories based on current intent.

## Phase 2: Intelligence & Logic Expansion (Medium Complexity)
*Focus: Adding new services and logic flows without major infra overhaul.*

### 2.1 Agent Cognition
- [ ] **33. Topic Change Detection**: Service to detect semantic shift in conversation to trigger consolidation.
- [ ] **34. Cross-Session Pattern Recognition**: Background job to find commonalities across user sessions.
- [ ] **36. Instruction Registry**: Create `InstructionRepository` to version and retrieve system prompts.
- [ ] **40. Execution-Based Evaluation**: Sandbox to run code snippets found in memory to verify they work.
- [ ] **45. Modular Component Architecture**: Refactor services to be more plugin-based.
- [ ] **46. Standard Operating Procedures (SOPs)**: Implement `SOPService` to ingest and execute structured JSON workflows.
- [ ] **47. Von Neumann Pattern**: Strict separation of Instructions and Data in the Agent loop.
- [ ] **52. Multi-Step Planning with Verification**: Planning service that generates steps and verifies them before execution.
- [ ] **53. Hierarchical Task Decomposition**: Break high-level goals into sub-tasks stored as linked memories.
- [ ] **54. Hypothesis Testing Framework**: Create `HypothesisService` where agents formulate and verify theories.
- [ ] **55. Context-Aware Tool Selection**: Dynamic loading of MCP tools based on current memory context.
- [ ] **127. Structured LLM Output**: Enforce strict JSON schemas (Pydantic) for all LLM extractions.
- [ ] **128. AgentTool Wrappers**: Standardized interface to call other agents as tools.
- [ ] **131. Socratic Questioning**: Logic to detect low-confidence answers and generate follow-up questions.
- [ ] **154. User Modeling**: Create `UserProfileService` to explicitly build and update user preferences.
- [ ] **155. Dependency Mapping**: Track which memories depend on others (e.g., Code dependencies).

### 2.2 Advanced Search & Graph
- [ ] **50. Cross-Modal Retrieval**: Implement text-to-image search using existing Multi-Modal embeddings.
- [ ] **76. Explainability Graph**: Store reasoning traces as graph paths.
- [ ] **95. Multilingual Search**: Translation layer before vector embedding.
- [ ] **97. Contextual Search**: Implement proximity search (terms appearing within N words).
- [ ] **98. Faceted Search**: Aggregation queries to count memories by Tier, Type, Agent.
- [ ] **99. Advanced Text Analytics**: Complexity scoring for text content.
- [ ] **102. Semantic-FTS Hybrid**: Tunable weighting for Vector vs Keyword scores.
- [ ] **122. Path Lookup Acceleration**: Cache common graph paths in Redis.
- [ ] **123. Parallel Search Execution**: Asyncio.gather for all search types.
- [ ] **124. Multi-Hop Constraints**: Enforce a `max_depth=3` limit on graph traversal.
- [ ] **142. Entity Disambiguation**: Logic to merge entities with same name but different context.

### 2.3 Time & Forensics
- [ ] **38. Advanced Multi-Index Strategy**: Composite indexes for Time+Tag queries.
- [ ] **41. Bi-temporal Graph Edges**: Fully expose `valid_time` vs `transaction_time` in the Graph API.
- [ ] **75. Temporal Graph Evolution**: Snapshots of graph metrics over time.
- [ ] **104. Agent Activity Timeline**: Logging all agent-memory interactions.
- [ ] **105. System Metrics Time-Series**: Tracking latency/cost over time.
- [ ] **106. Consolidation Schedule**: Intelligent scheduling based on system load.
- [ ] **107. Debate Outcome Trends**: Tracking how often agents disagree.
- [ ] **108. Learning Curve Tracking**: Measure and plot `verification_score` trends.
- [ ] **109. Importance Distribution**: Analytics on memory importance spread.
- [ ] **110. Graph Evolution Metrics**: Tracking node/edge growth.
- [ ] **119. Temporal Edge Invalidation**: Soft-delete logic for edges.
- [ ] **140. Temporal Heatmaps**: Visualizing bursty memory creation.

## Phase 3: Advanced Optimization & Infrastructure (High Complexity)
*Focus: Performance, Scale, and Specialized Math.*

### 3.1 Vector Optimization
- [ ] **79. Vector Quantization**: Implement logic to compress vectors.
- [ ] **80. Vector Drift Detection**: Background job to compare old vs. new embedding model outputs.
- [ ] **81. Vector Clustering & Centroids**: Pre-calculate centroids for fast search.
- [ ] **82. Adaptive Vector Dimensions**: Use smaller vectors for less important memories.
- [ ] **83. Vector-Space Anomaly Detection**: Identify memories that are outliers.
- [ ] **84. Vector Interpolation**: Logic to generate "bridge" concepts.
- [ ] **85. Vector Provenance**: Metadata tracking for embedding models.
- [ ] **86. Vector-Based Conflict Resolution**: Geometric conflict detection.
- [ ] **88. Feedback-Loop Vectors**: Reinforcement learning for vector ranking.
- [ ] **89. Vector Ensemble**: Average embeddings from multiple models.
- [ ] **90. Vector Deduplication**: Aggressive semantic deduplication.
- [ ] **92. Vector Attention**: Weighted vector segments.
- [ ] **159. Self-Healing Index**: Background job to re-index low-performing vectors.

### 3.2 Geospatial & Graph Theory
- [ ] **42. Hyperedges**: Implementation of N-ary relationships in SurrealDB.
- [ ] **66. Hyperedge Emulation**: Intermediate node pattern for hyperedges.
- [ ] **69. Hierarchical Graph**: Abstraction layers for graph nodes.
- [ ] **72. Agent-Centric Partitioning**: Sharding data by Agent ID.
- [ ] **73. Consensus Graph**: Special edge types for agreements.
- [ ] **74. Pattern Discovery**: Algorithmic detection of graph motifs.
- [ ] **111. Agent Location Context**: Tagging memories with `(lat, long)`.
- [ ] **113. Concept Cartography**: 2D projection of vector space.
- [ ] **114. Migration Path Tracking**: Tracking concept movement between agents.
- [ ] **115. Geospatial Similarity**: Distance-aware search.
- [ ] **143. Community Detection**: Graph clustering algorithms.
- [ ] **144. Centrality Analysis**: Identifying key influencers in the graph.
- [ ] **145. Pathfinding Algorithms**: Shortest path and A*.
- [ ] **146. Subgraph Isomorphism**: Structural pattern matching.

### 3.3 System Resilience & Architecture
- [ ] **48. Dynamic Context Window**: Token counting and resizing logic.
- [ ] **116. Flows vs Crews Pattern**: Architecture separation.
- [ ] **117. Hierarchical Agent Delegation**: Parent/Child agent logic.
- [ ] **125. Human-in-the-Loop Checkpoints**: Approval workflows for critical actions.
- [ ] **126. Semaphore Concurrency Limiting**: Global rate limiter.
- [ ] **132. Privacy-Preserving Sanitization**: PII Redaction service.
- [ ] **137. Conflict Resolution Protocols**: Automated negotiation logic.
- [ ] **148. Scoped Memories**: Project/Tenant isolation logic.
- [ ] **150. Recursive Summarization**: Hierarchical summary generation.
- [ ] **151. Anchor Point Navigation**: Keyframe memory identification.
- [ ] **152. Bias Detection**: Analysis of memory sentiment distribution.
- [ ] **156. Version Control**: Branching/Forking logic for memory sets.
- [ ] **157. Forking Capabilities**: Copy-on-write for memory branches.
- [x] **158. Merge Conflict Resolution**: UI/Logic for merging branches.

## Phase 4: Deep Research & Experimental (Very High Complexity)
*Focus: Novel implementations requiring significant R&D.*

- [x] **129. Dream-Inspired Consolidation**: Generative replay during downtime.
- [ ] **130. Counterfactual Simulation**: "What if" scenario generation.
- [ ] **133. Surprise-Based Learning**: Boosting weights for unexpected data.
- [ ] **134. Curiosity-Driven Exploration**: Active learning queries.
- [ ] **138. Narrative Threading**: Story generation from episodic memory.
- [ ] **139. Contextual Bandits**: RL-tuned retrieval.
- [ ] **149. Transient Scratchpads**: Redis-backed working memory.
- [ ] **167. Network Topology Validation**: AgentsNet benchmarking.
- [ ] **168. Meta-Reasoning (Dr. MAMR)**: Cognitive architecture implementation.
- [ ] **169. Reasoning Trace Storage**: Storing full Chain-of-Thought.
- [ ] **170. Prompt Genealogy Tracking**: Evolution history of prompts.
