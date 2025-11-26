# Khala Memory System v2.0

Khala is a high-performance, graph-based memory system for AI agents, built on SurrealDB. It provides long-term memory, semantic search, and advanced reasoning capabilities.

## Features

- **Vector Storage**: HNSW-based similarity search.
- **Graph Memory**: Entity-relationship modeling with graph traversal.
- **3-Tier Hierarchy**: Working, Short-term, and Long-term memory with auto-promotion.
- **Hybrid Search**: Vector + Keyword (BM25) + Metadata.
- **Advanced Reasoning**: Mixture of Thought, Multi-Perspective Questions, and Hypothesis Testing.
- **Skill Library**: Storage and execution of executable skills.

## Prerequisites

- Python 3.10+
- SurrealDB (latest version)
- Google Gemini API Key (for LLM features)

## Installation

1.  **Clone or copy this repository.**
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: You may need to create a `requirements.txt` based on the imports if not provided. Key dependencies: `surrealdb`, `google-generativeai`, `pydantic`, `numpy`)*

3.  **Configure Environment:**
    Create a `.env` file in the root directory:
    ```env
    SURREALDB_URL=ws://localhost:8000/rpc
    SURREALDB_USER=root
    SURREALDB_PASS=root
    SURREALDB_NAMESPACE=khala
    SURREALDB_DATABASE=memory
    GOOGLE_API_KEY=your_gemini_api_key
    ```

## Usage Example

```python
import asyncio
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory

async def main():
    # Initialize Client
    client = SurrealDBClient()
    await client.connect()
    
    # Create a Memory
    memory = await client.create_memory(
        content="The user prefers dark mode.",
        user_id="user_123",
        tags=["preference", "ui"]
    )
    print(f"Created memory: {memory['id']}")
    
    # Search
    results = await client.search_memories_by_vector(
        embedding=..., # Generate embedding first
        user_id="user_123"
    )
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Directory Structure

- `khala/domain`: Core business logic and entities.
- `khala/infrastructure`: Database clients, external APIs, and repositories.
- `khala/application`: Use cases and orchestration services.
- `tests`: Unit and integration tests.

## License

Proprietary - VOID Ecosystem.
