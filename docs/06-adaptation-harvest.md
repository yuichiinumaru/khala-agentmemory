# 06-ADAPTATION-HARVEST.md: Agentic Adaptation Strategies

**Source**: `github.com/pat-jj/Awesome-Adaptation-of-Agentic-AI`
**Harvest Date**: May 2025
**Scope**: Adaptive capabilities for Khala (Memory, Retrieval, Reasoning).

---

## 1. Landscape Analysis

The field of "Agentic Adaptation" is categorized into two main signals:
1.  **Tool Execution Signaled (A1)**: Agents adapt based on the success/failure of tool use (e.g., retrieving memory, searching web).
2.  **Agent Output Signaled (A2)**: Agents adapt based on self-reflection or external verification of their outputs.

Khala, being a Memory & Reasoning Engine, acts as both a **Tool** (for agents) and an **Agent** (managing its own memory graph). Therefore, we harvest strategies for both roles.

---

## 2. Harvested Strategies

### Strategy 171: Adaptive Graph Evolution (AutoGraph)
*Based on `AutoGraph-R1` (2025.10)*

**Concept**: The Knowledge Graph (KG) should not be static. When Retrieval-Augmented Generation (RAG) fails to answer a query despite having the data, it indicates a structural gap in the graph.
**Mechanism**:
1.  **Detection**: Monitor RAG failures (e.g., "I don't know" or low confidence answers).
2.  **Diagnosis**: An "Architect Agent" analyzes the retrieval path and the raw documents.
3.  **Repair**: The agent creates new hyperedges or summary nodes to bridge the gap (e.g., explicitly linking "Project X" to "Concept Y" if the connection was too implicit).
4.  **Implementation**: Extension of `IndexRepairService` and `KnowledgeGraphReasoningService`.

### Strategy 172: Adaptive Query Routing (Router)
*Based on `Router-R1` (2025.06)*

**Concept**: Not all queries require the full power of "Deep Research" or "Graph Traversal".
**Mechanism**:
1.  **Router Agent**: A lightweight model (Gemini Flash) predicts the difficulty and domain of a query.
2.  **Routing Table**:
    *   *Simple Fact*: -> `BM25 Search` (Direct lookup).
    *   *Semantic Query*: -> `Vector Search`.
    *   *Complex Relation*: -> `Graph Traversal`.
    *   *Novel Problem*: -> `Deep Reasoning (Dr. MAMR)`.
3.  **Adaptation**: The router learns from feedback. If a "Simple Fact" route returns low confidence, update the routing policy for similar queries.

### Strategy 173: Self-Challenging Memory Retrieval
*Based on `ReZero` / `Self-Challenging` (2025.03)*

**Concept**: Blindly trusting retrieved memories leads to hallucinations. The system must "challenge" its own retrieval before returning it to the user agent.
**Mechanism**:
1.  **Retrieval**: Fetch Top-K memories.
2.  **Challenge Loop**: A "Skeptic" model generates counter-arguments or verification questions against the retrieved memories relative to the query.
    *   *Query*: "What is the capital of France?"
    *   *Memory*: "Paris is a city in Texas." (Hypothetical bad memory)
    *   *Challenge*: "Is this the 'France' implied by the user context? Check for country vs city."
3.  **Filter**: Discard or flag memories that fail the challenge.

### Strategy 174: Feedback-Driven Search Tuning (T2)
*Based on `LeReT` / Agent-Supervised Tool Adaptation*

**Concept**: Static hyperparameters (Alpha=0.5, TopK=10) are suboptimal.
**Mechanism**:
1.  **Feedback Loop**: Record the "Success" of a search session (did the user accept the answer?).
2.  **Tuning**: Use a lightweight optimizer (or simple heuristic) to adjust `alpha` (Lexical vs Semantic weight) per Agent or per Domain.
    *   *Code Agent*: Might prefer `alpha=0.8` (Keyword heavy).
    *   *Chat Agent*: Might prefer `alpha=0.2` (Semantic heavy).
3.  **Persistence**: Store preferences in `AgentProfile`.

---

## 3. Implementation Roadmap

These strategies will be integrated as **Module 14: Adaptive Intelligence**.

- [ ] **M14.1**: `SelfChallengingService` (Strategy 173) - *High Impact, Low Risk*.
- [ ] **M14.2**: `AdaptiveSearchTuner` (Strategy 174) - *Data-driven optimization*.
- [ ] **M14.3**: `QueryRouter` (Strategy 172) - *Efficiency optimization*.
- [ ] **M14.4**: `GraphArchitect` (Strategy 171) - *Long-term maintenance*.
