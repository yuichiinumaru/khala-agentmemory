"""Unit tests for Privacy and Safety Service."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from khala.application.services.privacy_safety_service import (
    PrivacySafetyService,
    SanitizationResult,
    BiasResult
)
from khala.infrastructure.gemini.client import GeminiClient

@pytest.fixture
def mock_gemini_client():
    return Mock(spec=GeminiClient)

@pytest.fixture
def service(mock_gemini_client):
    return PrivacySafetyService(gemini_client=mock_gemini_client)

@pytest.mark.asyncio
async def test_sanitize_pii_regex(service):
    """Test regex-based sanitization."""
    text = "Contact me at user@example.com or 555-012-3456."
    result = await service.sanitize_content(text, use_llm=False)

    assert result.was_sanitized is True
    assert "<EMAIL>" in result.sanitized_text
    assert "<PHONE>" in result.sanitized_text
    assert "user@example.com" not in result.sanitized_text
    assert len(result.redacted_items) == 2

    # Ensure raw PII is not in redacted items
    for item in result.redacted_items:
        assert "text" not in item # Should not have raw text
        assert "user@example.com" not in str(item)

@pytest.mark.asyncio
async def test_sanitize_no_pii(service):
    """Test sanitization with no PII."""
    text = "Just a regular sentence with no secrets."
    result = await service.sanitize_content(text, use_llm=False)

    assert result.was_sanitized is False
    assert result.sanitized_text == text
    assert len(result.redacted_items) == 0

@pytest.mark.asyncio
async def test_detect_bias_mocked(service, mock_gemini_client):
    """Test bias detection with mocked LLM response."""
    mock_gemini_client.generate_text = AsyncMock(return_value={
        "content": '{"score": 0.8, "categories": ["political"], "analysis": "Biased statement"}'
    })

    result = await service.detect_bias("Some biased text")

    assert result.is_biased is True
    assert result.bias_score == 0.8
    assert "political" in result.categories
    assert result.analysis == "Biased statement"

@pytest.mark.asyncio
async def test_detect_bias_clean(service, mock_gemini_client):
    """Test bias detection on clean text."""
    mock_gemini_client.generate_text = AsyncMock(return_value={
        "content": '{"score": 0.1, "categories": [], "analysis": "Neutral statement"}'
    })

    result = await service.detect_bias("The sky is blue")

    assert result.is_biased is False
    assert result.bias_score == 0.1
    assert len(result.categories) == 0
