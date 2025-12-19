# The Map: Architecture Overview

Khala is not a flat database; it is a **3-Dimensional Graph**. Understanding its geography is key to mastering it.

## 1. The 3-Tier Hierarchy

Khala organizes memories based on their "Freshness" and "Access Pattern".

| Tier | Name | Storage Engine | Usage |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **Hot / Working** | Redis / In-Memory | Active thoughts, scratchpads, immediate context. Cleared effectively. |
| **Tier 2** | **Warm / Episodic** | SurrealDB (Graph) | Recent conversations, key facts, active user preferences. The "Main Memory". |
| **Tier 3** | **Cold / Semantic** | SurrealDB (Vector) | Consolidated wisdom, archived logs, deep history. Retrieved via search. |

*Automated Promotion*: A background process moves memories from T1 -> T2 -> T3 based on `importance` and `decay` scores.

## 2. The Namespace Split (`khala` vs `infra`)

To keep the "Agentic Brain" pure, we split the database namespaces:

- **`khala` Namespace**: Contains the *subjective* reality of the agents.
    - Tables: `memory`, `entity`, `relationship`, `dream`.
    - This is where agents "live".

- **`infra` Namespace**: Contains the *objective* reality of the system.
    - Tables: `audit_logs`, `metrics`, `system_health`.
    - This is for monitoring and debugging.

## 3. The Graph Structure

Everything in Khala is a node (`Entity` or `Memory`) connected by edges (`Relationship`).

```mermaid
graph TD
    M1[Memory: "User likes Pizza"] -->|MENTIONS| E1(Entity: "Pizza")
    E1 -->|IS_A| E2(Entity: "Food")
    M1 -->|CREATED_BY| A1(Agent: "ChefBot")
    M1 -->|RELATED_TO| M2[Memory: "User ordered Napolitana"]
```

- **Memories** are the raw data (text, image).
- **Entities** are the extracted concepts (Person, Place, Object).
- **Relationships** define the context ("is a", "located at", "prefers").

## 4. The Flow
1. **Ingestion**: Input -> Entity Extraction (NER) -> Vectorization -> Storage.
2. **Consolidation**: Idle Time -> DreamService -> Pattern Recognition -> New Knowledge.
3. **Retrieval**: Query -> Hybrid Search (Vector + Graph) -> Reranking -> Output.
