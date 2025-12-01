# KHALA Memory System v2.0

Khala is a high-performance, graph-based memory system for AI agents, built on SurrealDB. It provides long-term memory, semantic search, and advanced reasoning capabilities.

## Features

- **Vector Storage**: HNSW-based similarity search.
- **Graph Memory**: Entity-relationship modeling with graph traversal.
- **3-Tier Hierarchy**: Working, Short-term, and Long-term memory with auto-promotion.
- **Hybrid Search**: Vector + Keyword (BM25) + Metadata + Graph Reranking.
- **Advanced Reasoning**: Mixture of Thought, Multi-Perspective Questions, and Hypothesis Testing.
- **Skill Library**: Storage and execution of executable skills.
- **Module 13**: PromptWizard, ARM, LatentMAS, and MarsRL support.

## Prerequisites

- Python 3.11+
- SurrealDB (v1.0.0+)
- Google Gemini API Key (for LLM features)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/void-ecosystem/khala.git
    cd khala
    ```

2.  **Install the package:**
    You can install the package in editable mode:
    ```bash
    pip install -e .
    ```
    Or install dependencies directly:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    Create a `.env` file in the root directory:
    ```env
    SURREALDB_URL=ws://localhost:8000/rpc
    SURREALDB_USER=root
    SURREALDB_PASS=root
    SURREALDB_NAMESPACE=khala
    SURREALDB_DATABASE=memories
    GOOGLE_API_KEY=your_gemini_api_key
    ```

## Usage Example

```python
import asyncio
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

async def main():
    # Initialize Client
    client = SurrealDBClient()
    await client.initialize()
    
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

## Directory Structure

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

## License

MIT License.
