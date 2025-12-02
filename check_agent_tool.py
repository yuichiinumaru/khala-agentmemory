"""Verification script for AgentToolWrapper."""
import asyncio
from unittest.mock import MagicMock
from khala.interface.agno.tools.agent_wrapper import AgentToolWrapper
from khala.interface.agno.khala_agent import KHALAAgent

# Mock KHALA Agent
class MockKHALAAgent(KHALAAgent):
    def __init__(self, name="MockAgent"):
        self.name = name
        self.description = "A mock agent"
        # Skip super().__init__ to avoid side effects

    async def process_message(self, message, user_id, context=None):
        return {
            "response": f"Processed: {message}",
            "confidence": 1.0
        }

async def main():
    print("Verifying AgentToolWrapper...")

    mock_agent = MockKHALAAgent()
    wrapper = AgentToolWrapper(mock_agent)

    # Test async execution
    print("Testing async execution...")
    result = await wrapper.arun("Hello World")
    print(f"Result: {result}")
    assert result == "Processed: Hello World"

    print("Verification passed!")

if __name__ == "__main__":
    asyncio.run(main())
