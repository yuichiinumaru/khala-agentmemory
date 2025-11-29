
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.gemini.models import ModelTier, GeminiModel

@pytest.mark.asyncio
async def test_generate_mixture_of_thought():
    # Mock dependencies
    with patch('khala.infrastructure.gemini.client.genai') as mock_genai:
        # Setup mock client
        client = GeminiClient(api_key="test_key", enable_cascading=True)

        # Mock generate_text to return dummy responses
        async def mock_generate_text(prompt, **kwargs):
            if prompt.startswith("Perspective"):
                return {"content": f"Perspective content for {prompt}", "model_id": "gemini-2.0-flash"}
            else:
                return {"content": "Synthesized content", "model_id": "gemini-2.5-pro"}

        client.generate_text = AsyncMock(side_effect=mock_generate_text)

        # Run MoT
        result = await client.generate_mixture_of_thought("Test prompt", num_perspectives=3)

        # Verify
        assert "final_response" in result
        assert result["final_response"]["content"] == "Synthesized content"
        assert len(result["perspectives"]) == 3
        assert client.generate_text.call_count == 4 # 3 perspectives + 1 synthesis

@pytest.mark.asyncio
async def test_detect_conflicts():
    # Mock dependencies
    client = GeminiClient(api_key="test_key", enable_cascading=False)

    # Create dummy memories
    memory1 = MagicMock()
    memory1.id = "m1"
    memory1.content = "The sky is blue and true."

    memory2 = MagicMock()
    memory2.id = "m2"
    memory2.content = "The sky is false."

    memory3 = MagicMock()
    memory3.id = "m3"
    memory3.content = "Grass is green."

    # Run conflict detection
    # Note: _detect_conflicts calls _detect_contradiction which is synchronous and simple string matching
    # We don't need to mock _detect_contradiction as we can test the logic directly

    report = await client._detect_conflicts([memory1, memory2, memory3])

    assert report["conflict_detected"] is True
    assert len(report["conflicting_memories"]) > 0
    # "true" and "false" are in opposite_pairs

    # Check specific conflict
    conflict = report["conflicting_memories"][0]
    assert conflict["memory1_id"] == "m1"
    assert conflict["memory2_id"] == "m2"
    assert conflict["conflict_type"] == "contradiction"

@pytest.mark.asyncio
async def test_client_initialization_and_methods():
    with patch('khala.infrastructure.gemini.client.genai'):
        client = GeminiClient(api_key="test_key")

        # Check methods exist
        assert hasattr(client, "classify_task_complexity")
        assert hasattr(client, "select_model")
        assert hasattr(client, "generate_mixture_of_thought")
        assert hasattr(client, "_detect_conflicts")
        assert hasattr(client, "_run_debate_round")
