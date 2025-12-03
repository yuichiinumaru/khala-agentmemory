# KHALA: Knowledge Hierarchical Adaptive Long-term Agent

**Status**: Active Development (Phase 3: Optimization & Novelty) - Audit 2025-12-03
**Version**: 2.0.1
**Documentation**: [docs/](docs/)

Khala is an advanced, memory-centric AI agent architecture powered by **SurrealDB** and **Agno** (formerly Phidata). It implements a comprehensive set of 170 memory, reasoning, and coordination strategies to create a truly long-term, adaptive, and intelligent system.

## 🚀 Features

-   **Hybrid Memory System**: Combines Vector (Semantic), Graph (Associative), and Document (Structured) memory.
-   **Advanced Search**: Hybrid search (Vector + Keyword), Multi-hop Graph traversal, and Temporal queries.
-   **Cognitive Architecture**: Includes Reflection, Planning, Socratic Questioning, and Hypothesis Testing.
-   **SurrealDB Native**: leverages SurrealDB v2.0 features (HNSW, Live Queries, Computed Fields).
-   **Multi-Agent Coordination**: Supports Hierarchical Teams, Debates, and Latent Collaboration.

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/khala.git
cd khala

# Install dependencies (Editable mode)
pip install -e .

# Verify connection to SurrealDB
python scripts/check_conn.py
```

## 🧪 Testing

```bash
# Run all tests
python scripts/run_all_tests.py
```

## 📋 Strategy Implementation Checklist

Based on the latest audit (2025-12-03).

### 1. Core Strategies (Foundation)
- [x] 01. Vector Storage (HNSW)
- [x] 02. Graph Relationships
- [x] 03. Document Model
- [ ] 04. RBAC Multi-Tenancy (Partial)
- [x] 05. LIVE Real-time Subscriptions
- [x] 06. Hybrid Search
- [ ] 07. L1/L2/L3 Cache System (Partial)
- [x] 08. Context Assembly
- [x] 09. 3-Tier Memory Hierarchy
- [x] 10. Auto-Promotion Logic
- [x] 11. Consolidation System
- [ ] 12. Deduplication (Partial)
- [x] 13. Background Job Processing
- [x] 14. Temporal Analysis
- [x] 15. Entity Extraction (NER)
- [x] 16. Metadata & Tags System
- [x] 17. Natural Memory Triggers
- [x] 18. MCP Interface
- [x] 19. Multi-Agent Coordination
- [x] 20. Monitoring & Health Checks
- [x] 21. Decay Scoring
- [x] 22. Agent-to-Agent Communication

### 2. Advanced Strategies (Intelligence)
- [x] 23. LLM Cascading
- [x] 24. Consistency Signals
- [x] 25. Mixture of Thought (MoT)
- [x] 26. Self-Verification Loop
- [x] 27. Multi-Agent Debate
- [x] 28. Information Traceability
- [x] 29. BM25 Full-Text Search
- [x] 30. Query Intent Classification
- [x] 31. Significance Scoring
- [x] 32. Multi-Perspective Questions
- [x] 33. Topic Change Detection
- [x] 34. Cross-Session Pattern Recognition
- [x] 35. Skill Library System
- [x] 36. Instruction Registry
- [ ] 37. Emotion-Driven Memory (Partial)
- [x] 38. Advanced Multi-Index Strategy
- [x] 39. Audit Logging System
- [x] 40. Execution-Based Evaluation
- [x] 41. Bi-temporal Graph Edges
- [x] 42. Hyperedges
- [x] 43. Relationship Inheritance
- [x] 44. Distributed Consolidation
- [x] 45. Modular Component Architecture
- [x] 46. Standard Operating Procedures (SOPs)
- [x] 47. Von Neumann Pattern
- [ ] 48. Dynamic Context Window (Partial)
- [x] 49. Multimodal Support
- [x] 50. Cross-Modal Retrieval
- [x] 51. AST Code Representation
- [x] 52. Multi-Step Planning
- [x] 53. Hierarchical Task Decomposition
- [x] 54. Hypothesis Testing Framework
- [x] 55. Context-Aware Tool Selection
- [ ] 56. Graph Visualization
- [x] 57. LLM Cost Dashboard

### 3. SurrealDB Optimization
- [x] 58. Hierarchical Nested Documents
- [x] 59. Polymorphic Memory Documents
- [x] 60. Document Versioning
- [x] 61. Array-Based Accumulation
- [x] 62. Computed Properties
- [ ] 63. Conditional Content Fields (Partial)
- [x] 64. Schema-Flexible Metadata
- [ ] 65. Document-Level Transactions (Partial)
- [x] 66. Hyperedge Emulation
- [x] 67. Temporal Graph (Bi-temporal)
- [x] 68. Weighted Directed Multigraph
- [x] 69. Hierarchical Graph
- [x] 70. Bidirectional Relationship Tracking
- [x] 71. Recursive Graph Patterns
- [ ] 72. Agent-Centric Partitioning
- [ ] 73. Consensus Graph (Partial)
- [x] 74. Pattern Discovery
- [ ] 75. Temporal Graph Evolution
- [x] 76. Explainability Graph
- [ ] 77. Graph-as-Query
- [x] 78. Multi-Vector Representations
- [x] 79. Vector Quantization
- [x] 80. Vector Drift Detection
- [x] 81. Vector Clustering & Centroids
- [x] 82. Adaptive Vector Dimensions
- [x] 83. Vector-Space Anomaly Detection
- [x] 84. Vector Interpolation
- [x] 85. Vector Provenance
- [ ] 86. Vector-Based Conflict Resolution
- [x] 87. Vector Search with Filters
- [ ] 88. Feedback-Loop Vectors
- [ ] 89. Vector Ensemble
- [ ] 90. Vector Deduplication (Partial)
- [x] 91. Vector-Based Forgetting
- [ ] 92. Vector Attention
- [x] 93. Phrase Search with Ranking
- [x] 94. Linguistic Analysis
- [x] 95. Multilingual Search
- [x] 96. Typo Tolerance
- [x] 97. Contextual Search
- [ ] 98. Faceted Search (Partial)
- [ ] 99. Advanced Text Analytics
- [x] 100. Query Expansion
- [x] 101. Search History Suggestions
- [x] 102. Semantic-FTS Hybrid
- [x] 103. Memory Decay Time-Series
- [x] 104. Agent Activity Timeline
- [x] 105. System Metrics Time-Series
- [x] 106. Consolidation Schedule
- [ ] 107. Debate Outcome Trends
- [ ] 108. Learning Curve Tracking (Partial)
- [ ] 109. Importance Distribution
- [ ] 110. Graph Evolution Metrics
- [x] 111. Geospatial Optimization (111-115)

### 4. Novel & Experimental
- [ ] 116. Flows vs Crews Pattern (Partial)
- [x] 117. Hierarchical Agent Delegation
- [x] 118. Episodic Data Model
- [x] 119. Temporal Edge Invalidation
- [x] 120. Custom Pydantic Entity Types
- [x] 121. Graph Distance Reranking
- [ ] 122. Path Lookup Acceleration
- [x] 123. Parallel Search Execution
- [x] 124. Multi-Hop Constraints
- [ ] 125. Human-in-the-Loop Checkpoints
- [x] 126. Semaphore Concurrency Limiting
- [x] 127. Structured LLM Output
- [x] 128. AgentTool Wrappers
- [x] 129. Dream-Inspired Consolidation
- [x] 130. Counterfactual Simulation
- [x] 131. Socratic Questioning
- [x] 132. Privacy-Preserving Sanitization
- [ ] 133. Surprise-Based Learning
- [ ] 134. Curiosity-Driven Exploration
- [x] 135. Metacognitive Indexing
- [x] 136. Source Reliability Scoring
- [x] 137. Conflict Resolution Protocols
- [ ] 138. Narrative Threading (Partial)
- [ ] 139. Contextual Bandits
- [x] 140. Temporal Heatmaps
- [x] 141. Keyword Extraction Tagging
- [ ] 142. Entity Disambiguation (Partial)
- [x] 143. Community Detection
- [x] 144. Centrality Analysis
- [x] 145. Pathfinding Algorithms
- [x] 146. Subgraph Isomorphism
- [x] 147. Negative Constraints
- [ ] 148. Scoped Memories (Partial)
- [ ] 149. Transient Scratchpads
- [ ] 150. Recursive Summarization (Partial)
- [ ] 151. Anchor Point Navigation
- [x] 152. Bias Detection
- [x] 153. Intent-Based Prefetching
- [x] 154. User Modeling
- [x] 155. Dependency Mapping
- [ ] 156. Version Control (Partial)
- [ ] 157. Forking Capabilities
- [ ] 158. Merge Conflict Resolution
- [x] 159. Self-Healing Index

### 5. Advanced Research Integration
- [x] 160. Automated Prompt Optimization (PromptWizard)
- [x] 161. Homogeneous Reasoning Modules (ARM)
- [x] 162. Knowledge Graph Reasoning (LGKGR)
- [x] 163. Knowledge Injection (GraphToken)
- [x] 164. Latent State Collaboration (LatentMAS)
- [x] 165. Hierarchical RL Teams (FULORA)
- [x] 166. Multi-Agent RL Optimization (MarsRL)
- [x] 167. Network Topology Validation (AgentsNet)
- [x] 168. Meta-Reasoning (Dr. MAMR)
- [x] 169. Reasoning Trace Storage
- [x] 170. Prompt Genealogy Tracking
