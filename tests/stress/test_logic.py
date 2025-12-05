import pytest
from datetime import datetime, timezone, timedelta
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

def test_promotion_logic_strict():
    """Verify strictly the conditions for memory promotion."""

    # Working -> ShortTerm
    # Condition: Age > 0.5h AND Access > 5 AND Importance > 0.8

    # Case 1: All met
    mem = Memory(
        user_id="u", content="c",
        tier=MemoryTier.WORKING, importance=ImportanceScore(0.9),
        access_count=6,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=40)
    )
    assert mem.should_promote_to_next_tier() is True

    # Case 2: Age Fail
    mem.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    assert mem.should_promote_to_next_tier() is False

    # Case 3: Access Fail
    mem.created_at = datetime.now(timezone.utc) - timedelta(minutes=40)
    mem.access_count = 2
    assert mem.should_promote_to_next_tier() is False

    # Case 4: Importance Fail
    mem.access_count = 6
    mem.importance = ImportanceScore(0.5)
    assert mem.should_promote_to_next_tier() is False

def test_decay_calculation_accuracy():
    """Verify decay formula implementation."""
    # Formula: importance * exp(-age_days / half_life)
    # If age = half_life, score should be importance * 0.3678

    mem = Memory(
        user_id="u", content="c",
        tier=MemoryTier.LONG_TERM, importance=ImportanceScore(1.0),
        created_at=datetime.now(timezone.utc) - timedelta(days=30)
    )

    decay = mem.calculate_decay_score(half_life_days=30)

    # e^-1 approx 0.367879
    expected = 1.0 * 0.36787944117
    assert abs(decay.value - expected) < 1e-5
