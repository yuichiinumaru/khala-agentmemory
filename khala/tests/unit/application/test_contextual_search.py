import pytest
from unittest.mock import Mock, AsyncMock, patch
from khala.application.services.hybrid_search_service import HybridSearchService
from khala.domain.memory.entities import Memory

@pytest.mark.asyncio
class TestContextualSearch:
    async def test_proximity_search_filtering(self):
        mock_repo = Mock()
        mock_embedding_service = Mock()

        # Mock results
        # Memory 1: "Vector Database" (adjacent) -> Match
        # Memory 2: "Vector store is a Database" (distance 3) -> Match if window >= 3
        # Memory 3: "Vector ... 100 words ... Database" -> No Match

        m1 = Mock(spec=Memory)
        m1.id = "m1"
        m1.content = "This is a Vector Database system."

        m2 = Mock(spec=Memory)
        m2.id = "m2"
        m2.content = "Vector store is a type of Database."

        m3 = Mock(spec=Memory)
        m3.id = "m3"
        m3.content = "Vector " + "word " * 20 + "Database"

        mock_repo.search_by_vector = AsyncMock(return_value=[m1, m2, m3])
        mock_repo.search_by_text = AsyncMock(return_value=[])
        mock_embedding_service.get_embedding = AsyncMock(return_value=[0.1])

        service = HybridSearchService(
            memory_repository=mock_repo,
            embedding_service=mock_embedding_service
        )

        # Test 1: Tight window (2) - should match m1 only ("Vector Database" has distance 1)
        # "Vector" is index 3, "Database" is index 4. Diff = 1.
        results = await service.search(
            query="test",
            user_id="u1",
            proximity_search={"terms": ["Vector", "Database"], "window": 2}
        )

        # RRF might sort them, but we check presence
        ids = [m.id for m in results]
        assert "m1" in ids
        assert "m2" not in ids # distance is 4 (Vector=0, store=1, is=2, a=3, type=4, of=5, Database=6) - Wait "Vector store is a type of Database"
        # "Vector"(0) ... "Database"(6). Diff = 6.
        # Wait, simple split: ['Vector', 'store', 'is', 'a', 'type', 'of', 'Database.']
        # Distance = 6. Window 2 excludes it.

        # Test 2: Wider window (10) - should match m1 and m2
        results_wide = await service.search(
            query="test",
            user_id="u1",
            proximity_search={"terms": ["Vector", "Database"], "window": 10}
        )
        ids_wide = [m.id for m in results_wide]
        assert "m1" in ids_wide
        assert "m2" in ids_wide
        assert "m3" not in ids_wide # Distance is > 20
