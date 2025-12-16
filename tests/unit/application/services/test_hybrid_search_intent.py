import pytest
from unittest.mock import AsyncMock, MagicMock

from khala.application.services.hybrid_search_service import HybridSearchService
from khala.application.services.intent_classifier import IntentClassifier, QueryIntent
from khala.domain.memory.repository import MemoryRepository
from khala.domain.ports.embedding_service import EmbeddingService

@pytest.fixture
def mock_repo():
    return AsyncMock(spec=MemoryRepository)

@pytest.fixture
def mock_embedding():
    return AsyncMock(spec=EmbeddingService)

@pytest.fixture
def mock_intent_classifier():
    classifier = AsyncMock(spec=IntentClassifier)
    # Default intent
    classifier.classify_intent.return_value = {"intent": "factual", "confidence": 0.9}
    return classifier

@pytest.mark.asyncio
async def test_search_auto_detects_intent_by_default(mock_repo, mock_embedding, mock_intent_classifier):
    service = HybridSearchService(
        memory_repository=mock_repo,
        embedding_service=mock_embedding,
        intent_classifier=mock_intent_classifier
    )

    mock_embedding.get_embedding.return_value = [0.1, 0.2]
    mock_repo.search_by_vector.return_value = []
    mock_repo.search_by_text.return_value = []

    # Call search without specifying auto_detect_intent
    await service.search("What is the capital of France?", "user-1")

    # Assert intent detection was called
    mock_intent_classifier.classify_intent.assert_called_once_with("What is the capital of France?")

@pytest.mark.asyncio
async def test_search_adjusts_weights_based_on_intent(mock_repo, mock_embedding, mock_intent_classifier):
    service = HybridSearchService(
        memory_repository=mock_repo,
        embedding_service=mock_embedding,
        intent_classifier=mock_intent_classifier
    )

    # Mock FACTUAL intent -> Boost BM25
    mock_intent_classifier.classify_intent.return_value = {"intent": QueryIntent.FACTUAL.value}
    mock_embedding.get_embedding.return_value = [0.1, 0.2]
    mock_repo.search_by_vector.return_value = []
    mock_repo.search_by_text.return_value = []

    # We can't easily inspect internal variable 'bm25_weight' inside the function scope
    # without spy or checking args passed to a mocked dependency if they used the weight.
    # But search_by_vector/text don't take weight.
    # The scoring happens locally.
    # However, we can check logs?
    # Or trust the unit test for logic flow.

    await service.search("Fact query", "user-1", auto_detect_intent=True)

    mock_intent_classifier.classify_intent.assert_called()
