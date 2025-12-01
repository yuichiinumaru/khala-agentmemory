import pytest
import asyncio
from typing import List
from pydantic import BaseModel
from unittest.mock import AsyncMock, MagicMock, patch
from khala.infrastructure.gemini.client import GeminiClient

class User(BaseModel):
    name: str
    age: int
    interests: List[str]

@pytest.mark.asyncio
async def test_generate_structured_success():
    # Mock the dependencies
    mock_genai_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"name": "Alice", "age": 30, "interests": ["coding", "ai"]}'

    # Setup the async generate_content mock
    async def async_generate(*args, **kwargs):
        return mock_response

    mock_genai_model.generate_content = AsyncMock(side_effect=async_generate)

    # Patch the GenerativeModel constructor to return our mock
    with patch("google.generativeai.GenerativeModel", return_value=mock_genai_model):
        client = GeminiClient(api_key="fake_key", enable_cascading=False)
        # Mock _setup_models to avoid actual API calls during init if called
        client._models["gemini-2.5-pro"] = mock_genai_model

        # We need to mock generate_text because generate_structured calls it
        # But generate_text calls generate_content on the model.
        # Let's mock generate_text directly to control the output more easily for this unit test
        # without worrying about the prompt formatting logic inside generate_structured.

        # Wait, we want to test that generate_structured parses the output of generate_text.
        # So we should mock generate_text to return the dict that generate_structured expects.

        with patch.object(client, 'generate_text', new_callable=AsyncMock) as mock_generate_text:
            mock_generate_text.return_value = {
                "content": '```json\n{"name": "Alice", "age": 30, "interests": ["coding", "ai"]}\n```',
                "model_id": "gemini-2.5-pro",
                "model_tier": "reasoning"
            }

            result = await client.generate_structured(
                prompt="Generate a user",
                response_model=User
            )

            assert isinstance(result, User)
            assert result.name == "Alice"
            assert result.age == 30
            assert result.interests == ["coding", "ai"]

            # Verify generate_text was called with a prompt containing schema
            call_args = mock_generate_text.call_args
            prompt_sent = call_args[1]['prompt']
            assert "output valid JSON" in prompt_sent
            assert "properties" in prompt_sent # Schema keywords

@pytest.mark.asyncio
async def test_generate_structured_validation_error():
    client = GeminiClient(api_key="fake_key", enable_cascading=False)

    with patch.object(client, 'generate_text', new_callable=AsyncMock) as mock_generate_text:
        # Return invalid JSON (missing required field 'age')
        mock_generate_text.return_value = {
            "content": '{"name": "Bob", "interests": []}',
            "model_id": "gemini-2.5-pro"
        }

        with pytest.raises(ValueError, match="Response validation failed"):
            await client.generate_structured(
                prompt="Generate invalid user",
                response_model=User
            )

@pytest.mark.asyncio
async def test_generate_structured_json_parse_error():
    client = GeminiClient(api_key="fake_key", enable_cascading=False)

    with patch.object(client, 'generate_text', new_callable=AsyncMock) as mock_generate_text:
        # Return broken JSON
        mock_generate_text.return_value = {
            "content": '{"name": "Bob", "age": 30, "interests": ...',
            "model_id": "gemini-2.5-pro"
        }

        with pytest.raises(ValueError, match="LLM failed to generate valid JSON"):
            await client.generate_structured(
                prompt="Generate broken json",
                response_model=User
            )
