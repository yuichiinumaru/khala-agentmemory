import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from khala.domain.search.value_objects import Query, SearchIntent, SearchModality
from khala.domain.search.services import HybridSearchService, QueryExpander, SessionAnalyzer
from khala.domain.search.entities import SearchSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Tier 6 Search Enhancements Verification...")
    
    # 1. Verify Query Expansion
    logger.info("1. Verifying Query Expansion...")
    expander = QueryExpander()
    original_query = Query(
        text="how to build a react app",
        intent=SearchIntent.LEARNING,
        embedding=None,
        user_id="user123",
        modality=SearchModality.TEXT
    )
    
    variations = await expander.expand_query(original_query)
    logger.info(f"Original: {original_query.text}")
    for i, v in enumerate(variations):
        logger.info(f"Variation {i+1}: {v.text} (Filters: {v.filters})")
        
    assert len(variations) > 0
    assert any("examples of" in v.text for v in variations)
    
    # 2. Verify Session Analysis
    logger.info("2. Verifying Session Analysis...")
    mock_client = AsyncMock()
    # Mock past sessions
    mock_client.get_user_sessions.return_value = [
        {"query": {"text": "python async tutorial"}},
        {"query": {"text": "python async await"}},
        {"query": {"text": "python async patterns"}},
        {"query": {"text": "javascript basics"}}
    ]
    
    analyzer = SessionAnalyzer(mock_client)
    patterns = await analyzer.analyze_cross_session_patterns("user123")
    
    logger.info(f"Found {len(patterns)} patterns")
    for p in patterns:
        logger.info(f"Pattern: {p.pattern_type} - {p.pattern_data}")
        
    assert len(patterns) > 0
    # Check if "python" or "async" was detected as a topic
    topics = [p.pattern_data['topic'] for p in patterns]
    assert "python" in topics or "async" in topics
    
    # 3. Verify Modality Support
    logger.info("3. Verifying Modality Support...")
    image_query = Query(
        text="sunset",
        intent=SearchIntent.FACTUAL,
        embedding=None,
        user_id="user123",
        modality=SearchModality.IMAGE
    )
    assert image_query.modality == SearchModality.IMAGE
    logger.info(f"Created query with modality: {image_query.modality}")

    logger.info("Verification Complete!")

if __name__ == "__main__":
    asyncio.run(main())
