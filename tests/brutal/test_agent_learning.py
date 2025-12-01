import pytest
import asyncio
from typing import Dict, Any, List
from agno.agent import Agent
from agno.models.openai import OpenAIChat
# We use a Mock tool for Web Search since we can't reliably use GoogleSearch in test environment without keys
from unittest.mock import MagicMock

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

# Mock Khala Knowledge Base Tool
class KhalaTool:
    def __init__(self, client: SurrealDBClient, user_id: str):
        self.client = client
        self.user_id = user_id

    async def save_memory(self, content: str):
        """Saves a learned fact to long-term memory."""
        mem = Memory(
            user_id=self.user_id,
            content=content,
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.9),
            tags=["learned_fact"]
        )
        await self.client.create_memory(mem)
        return "Memory saved."

    async def search_memory(self, query: str):
        """Searches long-term memory for an answer."""
        results = await self.client.search_memories_by_bm25(query, user_id=self.user_id, top_k=1)
        if results:
            return results[0]['content']
        return "No memory found."

# Mock Web Search Tool
class MockWebSearch:
    def __init__(self, knowledge_base: Dict[str, str]):
        self.kb = knowledge_base

    def search(self, query: str):
        """Simulated web search."""
        for q, a in self.kb.items():
            if q.lower() in query.lower() or query.lower() in q.lower():
                return a
        return "No results found."

@pytest.mark.asyncio
async def test_agent_learning_loop():
    """Run the Asker/Answerer cycle using Agno Agents."""

    # 1. Setup Infrastructure
    client = SurrealDBClient()
    await client.initialize()

    truth_db = {
        "airspeed velocity": "African or European?",
        "lead dev": "Jules",
        "ultimate answer": "42"
    }

    # 2. Setup Agents
    # Note: In a real run, we'd use OpenAIChat or similar.
    # Here, we mock the 'model' behavior to avoid API calls but keep the Agent structure.

    khala_tool = KhalaTool(client, "student_1")
    web_tool = MockWebSearch(truth_db)

    # We manually simulate the interaction loop because we can't make actual LLM calls
    # but we will use the Tool classes to verify the integration logic.

    print("\n--- AGENT SIMULATION START ---")

    # Cycle 1: Failure & Learning
    for topic, answer in truth_db.items():
        question = f"What is the {topic}?"
        print(f"\n[Asker]: {question}")

        # Student attempts to answer from memory (empty)
        memory_result = await khala_tool.search_memory(question)
        print(f"[Student Internal]: Searched memory -> '{memory_result}'")

        student_response = "I don't know."
        if memory_result == "No memory found.":
            student_response = "I don't know."

        print(f"[Student]: {student_response}")

        # Teacher checks (Web Search)
        truth = web_tool.search(topic)

        if student_response != truth:
            print(f"[Asker]: Wrong. The answer is '{truth}'. Save this.")
            # Student saves to memory
            await khala_tool.save_memory(f"Question: {question} Answer: {truth}")
            print(f"[Student]: Saved to memory.")

        await asyncio.sleep(0.01)

    # Cycle 2: Reinforcement
    print("\n--- REINFORCEMENT CYCLE ---")
    success_count = 0

    for topic, answer in truth_db.items():
        question = f"What is the {topic}?"
        print(f"\n[Asker]: {question}")

        # Student attempts to answer from memory (populated)
        memory_result = await khala_tool.search_memory(question)

        if answer in memory_result:
            print(f"[Student]: {memory_result}")
            print(f"[Asker]: Correct.")
            success_count += 1
        else:
            print(f"[Student]: {memory_result}")
            print(f"[Asker]: FAIL. Why didn't you consult memory?")

    await client.close()

    assert success_count == len(truth_db)
