import unittest
import pytest
from unittest.mock import MagicMock, AsyncMock
import os
import sys

# Ensure khala is in path
sys.path.append(os.getcwd())

from khala.application.services.significance_scorer import SignificanceScorer
from khala.application.services.entity_extraction import EntityExtractionService
from khala.domain.agent.entities import AgentProfile, AgentRole
from khala.domain.memory.entities import Relationship
from khala.infrastructure.monitoring.health import HealthMonitor

class TestQuickWins(unittest.IsolatedAsyncioTestCase):
    async def test_significance_scorer(self):
        mock_gemini = AsyncMock()
        mock_gemini.generate_text.return_value = {"content": "0.8"}
        scorer = SignificanceScorer(mock_gemini)
        score = await scorer.calculate_significance("important: test")
        self.assertGreaterEqual(score.value, 0.9) # Heuristic

    async def test_entity_extraction_keywords(self):
        extractor = EntityExtractionService()
        extractor.gemini_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.text = '["key"]'
        extractor.gemini_client.generate_content_async.return_value = mock_resp
        keywords = await extractor.extract_keywords("text")
        self.assertIn("key", keywords)

    def test_agent_profile_negative_constraints(self):
        profile = AgentProfile(id="1", name="test", role=AgentRole.WORKER, capabilities=[])
        self.assertEqual(profile.negative_constraints, [])

    def test_relationship_weight(self):
        rel = Relationship("a", "b", "type", 0.5)
        self.assertEqual(rel.weight, 1.0)
