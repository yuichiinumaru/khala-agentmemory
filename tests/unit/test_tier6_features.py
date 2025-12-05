import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
from decimal import Decimal
import os

from khala.domain.memory.entities import Memory
from khala.domain.memory.value_objects import MemoryTier, ImportanceScore, MemorySource, Sentiment
from khala.infrastructure.gemini.cost_tracker import CostTracker
from khala.infrastructure.gemini.models import GeminiModel, ModelTier

def test_traceability_attachment():
    # 1. Arrange
    source = MemorySource(
        source_type="user_input",
        source_id="msg_123",
        confidence=0.95
    )

    # 2. Act
    memory = Memory(
        user_id="user_1",
        content="Test",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        source=source
    )

    # 3. Assert
    assert memory.source is not None
    assert memory.source.source_type == "user_input"
    assert memory.source.confidence == 0.95

def test_sentiment_attachment():
    # 1. Arrange
    sentiment = Sentiment(score=0.8, label="joy")

    # 2. Act
    memory = Memory(
        user_id="u1",
        content="Happy",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        sentiment=sentiment
    )

    # 3. Assert
    assert memory.sentiment.label == "joy"

def test_cost_tracker_persistence(tmp_path):
    # 1. Arrange
    # Use pytest's tmp_path to avoid global pollution
    fake_path = tmp_path / "costs.json"

    # Patch load_from_file to avoid reading real file during init
    with patch("khala.infrastructure.gemini.cost_tracker.CostTracker.load_from_file"):
        tracker = CostTracker()
        tracker.persistence_path = str(fake_path) # Inject isolated path

        model = GeminiModel(
            model_id="test-model",
            name="Test",
            tier=ModelTier.FAST,
            cost_per_million_tokens=1.0,
            max_tokens=100
        )

        # 2. Act
        tracker.record_call(model, 100, 50, 100.0)

        # 3. Assert
        assert fake_path.exists()
        content = fake_path.read_text()
        assert "test-model" in content
