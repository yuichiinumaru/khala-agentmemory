# Warp-In: Getting Started with Khala

This guide will help you establish a connection to the Khala network.

## Prerequisities

- **Python 3.10+**
- **SurrealDB v2.0+** (Running locally or remotely)
- **Gemini API Key** (For embeddings and reasoning)

## 1. Installation

Khala is designed to be installed as an editable package within the VIVI OS monorepo.

```bash
cd packages/khala-agentmemory
pip install -e .
```

## 2. Configuration (`.env`)

Create a `.env` file in your project root or `packages/khala-agentmemory/.env`:

```env
# SurrealDB Configuration (The Brain)
KHALA_SURREAL_URL="ws://localhost:8000/rpc"
KHALA_SURREAL_USER="root"
KHALA_SURREAL_PASS="root"
KHALA_SURREAL_NS="khala"  # The Agentic Namespace
KHALA_SURREAL_DB="dev"

# Google Gemini (The Neuron)
GOOGLE_API_KEY="AIzaSy..."
```

## 3. Hello World (Your First Memory)

Here is how you initialize an agent and store a simple thought.

```python
import asyncio
from khala.interface.agno.khala_agent import KHALAAgent
from khala.domain.memory.schemas import MemoryInput

async def main():
    # 1. Initialize the Agent (Connects to SurrealDB automatically)
    agent = KHALAAgent(
        agent_id="agent-001",
        user_id="user-demo"
    )

    # 2. Form a Memory Input
    memory = MemoryInput(
        content="The user prefers dark mode for the UI.",
        source="user_preference",
        importance=0.8
    )

    # 3. Store in Khala
    await agent.memory.add(memory)
    print("Memory stored successfully!")

    # 4. Recall
    results = await agent.memory.search("What does the user like?")
    print(f"Recall: {results[0].content}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 4. Verification

Run the built-in connection check script:

```bash
python scripts/check_conn.py
```

If you see **"Connected to Khala [OK]"**, you are ready to proceed.
