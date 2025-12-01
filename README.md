# KHALA Memory System v2.0

> *"The Khala is fully integrated. Our thoughts are one."*

**Khala** is the ultimate psionic link for your AI agents—a high-performance, graph-based memory system forged in the fires of **SurrealDB**. It transcends simple vector storage, weaving a complex web of **Long-term Memory**, **Semantic Search**, and **Hierarchical Reasoning**.

Just as the Protoss share a unified consciousness, your agents will share a boundless, structured memory, allowing them to recall, reason, and evolve.
- **Vector Storage**: HNSW-based similarity search.
- **Graph Memory**: Entity-relationship modeling with graph traversal.
- **3-Tier Hierarchy**: Working, Short-term, and Long-term memory with auto-promotion.
- **Hybrid Search**: Vector + Keyword (BM25) + Metadata + Graph Reranking.
- **Advanced Reasoning**: Mixture of Thought, Multi-Perspective Questions, and Hypothesis Testing.
- **Skill Library**: Storage and execution of executable skills.
- **Module 13**: PromptWizard, ARM, LatentMAS, and MarsRL support.

---

III## 🌌 System Status (The Psionic Matrix)
- Python 3.11+
- SurrealDB (v1.0.0+)
- Google Gemini API Key (for LLM features)

The grid is active. Construction of the memory core is **86% Complete**.

| **Module Sector** | **Status** | **Completion** |
| :--- | :--- | :--- |
| **Phase 1: Foundation** (Modules 1-10) | **ONLINE** | **100%** |
| **Phase 2: Optimization** (Module 11) | **WARPING IN** | **Partial** |
| **Phase 3: Novelty & Research** (Modules 12-13) | **RESEARCHING** | **Partial** |

**Total Strategic Protocols Implemented**: **71 / 82**
**Psionic Link Stability**: **Stable**

---

## 🔮 Capabilities (Tech Tree)

### **Core Nexus (Modules 1-10)**
-   **Vector Storage (HNSW)**: Instant retrieval of semantic concepts.
-   **Graph Memory**: Entity-relationship modeling. *We do not just store data; we understand connections.*
-   **3-Tier Hierarchy**: Working, Short-term, and Long-term memory with auto-promotion logic.
-   **Hybrid Search**: Reciprocal Rank Fusion of Vector + Keyword (BM25) + Metadata + Graph Reranking.
-   **Skill Library**: Executable skills stored as memories.

### **Advanced Upgrades (Modules 11-13)**
-   **Multi-Vector Support** (Strategy 78): Agents now possess separate embeddings for **Visual** and **Code** data.
-   **MarsRL Support** (Strategy 166): The `training_curves` table is laid, paving the way for Reinforcement Learning optimization.
-   **Experimental**: Episodic Memory and Metacognitive Indexing.

---

## ⚡ Deployment (Warp In)

### Prerequisites
-   Python 3.11+
-   SurrealDB v1.0.0+ (The Core)
-   Google Gemini API Key (The Oracle)

### Installation

1.  **Clone the Repository:**
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/void-ecosystem/khala.git
    cd khala
    ```

2.  **Initialize the Link:**
2.  **Install the package:**
    You can install the package in editable mode:
    ```bash
    pip install -e .
    ```
    Or install dependencies directly:
    ```bash
    pip install -e .
    ```

3.  **Configure the Matrix:**
    Create a `.env` file in the root directory:
    ```env
    SURREALDB_URL=ws://localhost:8000/rpc
    SURREALDB_USER=root
    SURREALDB_PASS=root
    SURREALDB_NAMESPACE=khala
    SURREALDB_DATABASE=memories
    GOOGLE_API_KEY=your_gemini_api_key
    ```

---

## ⚔️ Usage (Commanding the Fleet)

```python
import asyncio
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

async def main():
    # Establish connection to the Khala
    client = SurrealDBClient()
    await client.initialize()
    
    # Forge a new memory
    mem = Memory(
        user_id="executor_001",
        content="We must construct additional pylons.",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(1.0),
        tags=["strategy", "economy"]
    )
    
    memory_id = await client.create_memory(mem)
    print(f"Memory forged: {memory_id}")

    # Recall knowledge
    results = await client.search_memories_by_bm25("pylons", user_id="executor_001")
    for r in results:
        print(f"Recalled: {r['content']}")
    # Create a Memory
    mem = Memory(
        user_id="user_123",
        content="The user prefers dark mode.",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.8),
        tags=["preference", "ui"]
    )
    
    memory_id = await client.create_memory(mem)
    print(f"Created memory: {memory_id}")

    # Search (assuming embeddings are generated)
    # results = await client.search_memories_by_vector(...)
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📜 Documentation (The Archives)

Consult the archives for deeper knowledge:
-   [Implementation Tasks](docs/02-tasks-implementation.md) - The active build order.
-   [Master Strategy List](docs/06-strategies-master.md) - The complete tech tree.
-   [SurrealDB Optimization](docs/11-surrealdb-optimization.md) - Database tuning specifications.
- `khala/domain`: Core business logic and entities.
- `khala/infrastructure`: Database clients, external APIs, and repositories.
- `khala/application`: Use cases and orchestration services.
- `tests`: Unit and integration tests.
- `docs`: Comprehensive documentation.

## Documentation

See the `docs/` directory for detailed documentation:
- [Implementation Tasks](docs/02-tasks-implementation.md)
- [Master Strategy List](docs/06-strategies-master.md)
- [SurrealDB Optimization](docs/11-surrealdb-optimization.md)

---

> *En Taro Adun, Executor.*
MIT License.
