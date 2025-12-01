import pytest
from unittest.mock import Mock, AsyncMock, patch
from khala.application.services.hybrid_search_service import HybridSearchService
from khala.domain.memory.entities import Memory
from khala.domain.memory.value_objects import EmbeddingVector

@pytest.mark.asyncio
class TestMultilingualSearch:
    async def test_search_translates_query(self):
        mock_repo = Mock()
        mock_embedding_service = Mock()
        mock_qe_service = Mock()
        mock_gemini = Mock()

        # Setup mocks
        mock_qe_service.gemini_client = mock_gemini
        mock_gemini.translate_text = AsyncMock(return_value="Translated Query")
        # expand_query returns list
        mock_qe_service.expand_query = AsyncMock(return_value=["Expanded Translated Query"])

        mock_embedding_service.get_embedding = AsyncMock(return_value=[0.1, 0.2])
        mock_repo.search_by_vector = AsyncMock(return_value=[])
        mock_repo.search_by_text = AsyncMock(return_value=[])

        service = HybridSearchService(
            memory_repository=mock_repo,
            embedding_service=mock_embedding_service,
            query_expansion_service=mock_qe_service
        )

        # IMPORTANT: set expand_query=True so that query expansion service is called
        await service.search(
            query="Hola Mundo",
            user_id="user1",
            language="es",
            expand_query=True
        )

        # Verify translation was called
        mock_gemini.translate_text.assert_called_once_with("Hola Mundo", target_language="English")

        # Verify vector search used translated query (or its expansion)
        # expand_query should be called with "Translated Query"
        mock_qe_service.expand_query.assert_called()
        call_args = mock_qe_service.expand_query.call_args
        # The first argument to expand_query should be the translated text
        assert "Translated Query" in call_args[0][0]

    async def test_search_no_translation_for_english(self):
        mock_repo = Mock()
        mock_embedding_service = Mock()
        mock_qe_service = Mock()
        mock_gemini = Mock()

        mock_qe_service.gemini_client = mock_gemini
        mock_qe_service.expand_query = AsyncMock(return_value=["Expanded Query"])

        mock_embedding_service.get_embedding = AsyncMock(return_value=[0.1, 0.2])
        mock_repo.search_by_vector = AsyncMock(return_value=[])
        mock_repo.search_by_text = AsyncMock(return_value=[])

        service = HybridSearchService(
            memory_repository=mock_repo,
            embedding_service=mock_embedding_service,
            query_expansion_service=mock_qe_service
        )

        await service.search(
            query="Hello World",
            user_id="user1",
            language="en"
        )

        mock_gemini.translate_text.assert_not_called()
