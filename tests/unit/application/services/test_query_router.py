import pytest
from unittest.mock import AsyncMock
from khala.application.services.query_router import QueryRouter

@pytest.mark.asyncio
async def test_route_fact():
    client = AsyncMock()
    client.generate_text.return_value = {"content": "FACT"}
    router = QueryRouter(client)
    route = await router.route("What is the capital of France?")
    assert route == "FACT"

@pytest.mark.asyncio
async def test_route_reasoning():
    client = AsyncMock()
    client.generate_text.return_value = {"content": "REASONING"}
    router = QueryRouter(client)
    route = await router.route("How does memory consolidation affect long-term planning?")
    assert route == "REASONING"
