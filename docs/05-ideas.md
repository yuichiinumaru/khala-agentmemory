# 05-IDEAS.md: The Parking Lot & Research Lab

**Topic**: Titans & MIRAS Integration (Cognitive Memory Evolution)
**Status**: Research / Roadmap
**Source**: Google Research (Titans: Learning to Memorize at Test Time)

---

## 1. Core Concepts (Titans + MIRAS)

**Titans** is an architecture combining a local attention core (short-term) with a deep neural long-term memory module, updated at runtime via a "surprise metric".
**MIRAS** is the framework: Memory architecture, Attentional bias, Retention gate, Algorithm.

### Key Insights for Khala
Khala (Agno + SurrealDB) already implements a "Macro-MIRAS":
- **Architecture**: SurrealDB (Multi-model).
- **Attentional Bias**: Importance/Relevance scoring.
- **Retention Gate**: Decay/Consolidation logic.
- **Algorithm**: Background jobs.

### The Upgrade Path (SurrealDB Implementation)

#### 1. Surprise-Driven Storage
Instead of just importance, track **Surprise**.
- **Metrics**: Logprob/Perplexity from LLM + Vector Distance from centroid.
- **Logic**: High surprise = Immediate promotion to Long-Term.
- **Schema**:
    ```sql
    DEFINE FIELD surprise_score ON TABLE memory TYPE float DEFAULT 0.0;
    DEFINE FIELD surprise_momentum ON TABLE memory TYPE float DEFAULT 0.0;
    ```

#### 2. Surprise Momentum (Context Boosting)
Events surrounding a "Surprise" are also important.
- **Mechanism**: If `surprise_score > Threshold`, boost neighbors (±N steps) via `surprise_context_boost`.
- **Goal**: Capture the "Episode" leading to the anomaly.

#### 3. Explicit Retention Gates
Formalize forgetting as regularization.
- **Formula**: $Retention_{t+1} = \lambda \cdot Retention_{t} + \alpha \cdot f(Surprise, Usage)$
- **Schema**:
    ```sql
    DEFINE FIELD retention_weight ON TABLE memory TYPE float DEFAULT 1.0;
    ```
- **Action**: When `retention_weight < threshold`, archive or compress.

#### 4. Deep Memory Layers (Derivation)
Formalize abstraction layers.
- **Hierarchy**: `Raw Event` -> `Episode` -> `Pattern` -> `Skill`.
- **Graph**: `RELATE memory:A -> derives_into -> memory:B`.
- **Retrieval**: Prefer deep summaries for long-context queries.

#### 5. Robust Merging (Loss Functions)
Use non-Euclidean metrics for consolidation.
- **Huber Loss**: Soften penalty for small differences, linear for outliers.
- **Probabilistic Beliefs**: Store `belief_mean` / `belief_variance` for facts.

#### 6. Test-Time Adaptation
Update routing policies based on runtime performance.
- **Dynamic Skills**: Reorder agent tools based on success rate timeseries.
- **Prompt Caching**: Store successful "Solution Patterns" for novel (high surprise) problems.

---

## 2. Implementation Strategy (Phase 4)

We will not replace Agno/SurrealDB but enhance the *policies* governing them.

1.  **Schema Upgrade**: Add fields to `Memory` entity and SurrealDB tables.
2.  **Pipeline Update**: Calculate `surprise_score` during ingestion.
3.  **Job Upgrade**: Implement `retention_weight` decay in background jobs.
4.  **Graph Logic**: Implement `derives_into` relationships for summarization.
