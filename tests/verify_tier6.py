import asyncio
import sys
import os
from datetime import datetime
from decimal import Decimal

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from khala.domain.memory.entities import Memory
from khala.domain.memory.value_objects import (
    MemoryTier, ImportanceScore, MemorySource, Sentiment
)
from khala.infrastructure.gemini.cost_tracker import CostTracker
from khala.infrastructure.gemini.models import GeminiModel, ModelTier

async def verify_tier6_features():
    print("=== Verifying Tier 6 Features ===")
    
    # 1. Verify Traceability (Task 28)
    print("\n[1] Verifying Information Traceability...")
    try:
        source = MemorySource(
            source_type="user_input",
            source_id="msg_123",
            location="chat_window",
            timestamp=datetime.now(),
            confidence=0.95
        )
        
        memory = Memory(
            user_id="user_1",
            content="Test memory with source",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5),
            source=source
        )
        
        assert memory.source is not None
        assert memory.source.source_type == "user_input"
        assert memory.source.confidence == 0.95
        print("✅ MemorySource created and attached successfully")
        
    except Exception as e:
        print(f"❌ Traceability verification failed: {e}")
        
    # 2. Verify Emotion-Driven Memory (Task 37)
    print("\n[2] Verifying Emotion-Driven Memory...")
    try:
        sentiment = Sentiment(
            score=0.8,
            label="joy",
            emotions={"joy": 0.8, "excitement": 0.4}
        )
        
        memory_emotional = Memory(
            user_id="user_1",
            content="I am so happy today!",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.8),
            sentiment=sentiment
        )
        
        assert memory_emotional.sentiment is not None
        assert memory_emotional.sentiment.score == 0.8
        assert memory_emotional.sentiment.label == "joy"
        print("✅ Sentiment created and attached successfully")
        
    except Exception as e:
        print(f"❌ Emotion verification failed: {e}")

    # 3. Verify Cost Dashboard Persistence (Task 57)
    print("\n[3] Verifying Cost Dashboard Persistence...")
    try:
        # Create tracker and record some data
        tracker = CostTracker()
        
        # Mock model
        model = GeminiModel(
            model_id="gemini-2.5-flash",
            name="Gemini 2.5 Flash",
            tier=ModelTier.FAST,
            cost_per_million_tokens=Decimal("0.10"),
            max_tokens=8192
        )
        
        # Record a call
        tracker.record_call(
            model=model,
            input_tokens=100,
            output_tokens=50,
            response_time_ms=150.0,
            task_type="generation"
        )
        
        # Verify file was created
        costs_file = os.path.join(os.path.dirname(tracker.persistence_path), "costs.json")
        assert os.path.exists(costs_file)
        print(f"✅ Costs file created at {costs_file}")
        
        # Verify loading
        new_tracker = CostTracker()
        assert len(new_tracker.cost_records) > 0
        last_record = new_tracker.cost_records[-1]
        assert last_record.model_id == "gemini-2.5-flash"
        print("✅ Costs loaded successfully from file")
        
    except Exception as e:
        print(f"❌ Cost persistence verification failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_tier6_features())
