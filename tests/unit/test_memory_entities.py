"""Unit tests for memory domain entities.

Following TDD principles, these tests verify the business logic
and domain rules for memory entities.
"""

import pytest
from datetime import datetime, timezone, timedelta

from khala.domain.memory.entities import Memory, Entity, Relationship, EntityType
from khala.domain.memory.value_objects import EmbeddingVector, ImportanceScore, MemoryTier


class TestMemory:
    """Test cases for Memory entity."""
    
    def test_memory_creation_minimal(self):
        """Test creating a memory with minimal attributes."""
        memory = Memory(
            user_id="user123",
            content="Test memory content",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium()
        )
        
        assert memory.user_id == "user123"
        assert memory.content == "Test memory content"
        assert memory.tier == MemoryTier.WORKING
        assert memory.importance.value == 0.5
        assert memory.access_count == 0
        assert not memory.is_archived
        assert memory.id is not None
        assert isinstance(memory.created_at, datetime)
    
    def test_memory_creation_full_attributes(self):
        """Test creating a memory with all attributes."""
        embedding = EmbeddingVector([0.1] * 768)
        memory = Memory(
            user_id="user123",
            content="Full test memory",
            tier=MemoryTier.LONG_TERM,
            importance=ImportanceScore.high(),
            embedding=embedding,
            tags=["test", "example"],
            category="general",
            metadata={"source": "manual"}
        )
        
        assert memory.embedding == embedding
        assert memory.tags == ["test", "example"]
        assert memory.category == "general"
        assert memory.metadata["source"] == "manual"
    
    def test_memory_invalid_content(self):
        """Test memory with empty content."""
        with pytest.raises(ValueError, match="Memory content cannot be empty"):
            Memory(
                user_id="user123",
                content="",
                tier=MemoryTier.WORKING,
                importance=ImportanceScore.medium()
            )
    
    def test_memory_invalid_user_id(self):
        """Test memory with empty user ID."""
        with pytest.raises(ValueError, match="User ID cannot be empty"):
            Memory(
                user_id="",
                content="Test content",
                tier=MemoryTier.WORKING,
                importance=ImportanceScore.medium()
            )
    
    def test_memory_promotion_working_to_short_term(self):
        """Test promotion from working to short term tier."""
        memory = Memory(
            user_id="user123",
            content="Important memory",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.very_high()  # 0.9
        )
        
        # Should not promote initially
        assert not memory.should_promote_to_next_tier()
        
        # Add enough accesses and wait
        for _ in range(6):
            memory.record_access()
        
        # Wait 1 hour
        memory.created_at = datetime.now(timezone.utc) - timedelta(hours=1, minutes=1)
        
        # Should now promote
        assert memory.should_promote_to_next_tier()
        
        # Promote and verify
        memory.promote()
        assert memory.tier == MemoryTier.SHORT_TERM
    
    def test_memory_promotion_short_term_to_long_term(self):
        """Test promotion from short term to long term tier."""
        # Create old enough memory
        old_time = datetime.now(timezone.utc) - timedelta(days=16)
        memory = Memory(
            user_id="user123",
            content="Very old memory",
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore.medium()
        )
        memory.created_at = old_time
        memory.updated_at = old_time
        
        # Should promote due to age
        assert memory.should_promote_to_next_tier()
        
        memory.promote()
        assert memory.tier == MemoryTier.LONG_TERM
    
    def test_memory_promotion_high_importance(self):
        """Test promotion due to high importance."""
        memory = Memory(
            user_id="user123",
            content="Super important",
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore(0.95)  # Very high
        )
        
        # Should promote due to high importance regardless of age
        assert memory.should_promote_to_next_tier()
        
        memory.promote()
        assert memory.tier == MemoryTier.LONG_TERM
    
    def test_memory_promotion_from_long_term_fails(self):
        """Test that long term memories cannot be promoted."""
        memory = Memory(
            user_id="user123",
            content="Long term memory",
            tier=MemoryTier.LONG_TERM,
            importance=ImportanceScore.high()
        )
        
        # Long term has no next tier
        assert memory.tier.next_tier() is None
        assert not memory.should_promote_to_next_tier()
        
        with pytest.raises(ValueError, match="Cannot promote from long_term"):
            memory.promote()
    
    def test_memory_archival_criteria(self):
        """Test memory archival criteria."""
        # Create old, unused, low-importance memory
        old_time = datetime.now(timezone.utc) - timedelta(days=91)
        memory = Memory(
            user_id="user123",
            content="Old forgotten memory",
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore.low()  # 0.25
        )
        memory.created_at = old_time
        memory.updated_at = old_time
        memory.accessed_at = old_time
        
        # Should meet archival criteria
        assert memory.should_archive()
        
        memory.archive()
        assert memory.is_archived
    
    def test_memory_should_not_archive(self):
        """Test memories that should not be archived."""
        memory = Memory(
            user_id="user123",
            content="Active memory",
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore.high()
        )
        
        # Should not archive (accessed, important, recent)
        assert not memory.should_archive()
        
        with pytest.raises(ValueError, match="does not meet archival criteria"):
            memory.archive()
    
    def test_memory_access_tracking(self):
        """Test memory access tracking."""
        memory = Memory(
            user_id="user123",
            content="Popular memory",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium()
        )
        
        initial_accessed = memory.accessed_at
        initial_count = memory.access_count
        
        # Record access
        memory.record_access()
        
        assert memory.access_count == initial_count + 1
        assert memory.accessed_at > initial_accessed
    
    def test_memory_decay_score_calculation(self):
        """Test decay score calculation."""
        memory = Memory(
            user_id="user123",
            content="Aging memory",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.8)
        )
        
        # Make memory 30 days old
        memory.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        
        decay = memory.calculate_decay_score(half_life_days=30)
        
        # After one half-life, score should be ~30% of original
        assert 0.25 < decay.value < 0.35
        assert memory.decay_score == decay
    
    def test_memory_verification_score(self):
        """Test verification score updates."""
        memory = Memory(
            user_id="user123",
            content="Memory to verify",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium()
        )
        
        # Update verification score
        memory.update_verification_score(0.85, ["minor_issue"])
        
        assert memory.verification_score == 0.85
        assert memory.verification_issues == ["minor_issue"]
        
        # Clear issues
        memory.update_verification_score(0.95)
        assert memory.verification_issues == []
    
    def test_memory_tag_management(self):
        """Test adding tags to memory."""
        memory = Memory(
            user_id="user123",
            content="Tagged memory",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium()
        )
        
        # Add tag
        memory.add_keyword_tag("python")
        assert "python" in memory.tags
        
        # Add duplicate tag (should not duplicate)
        memory.add_keyword_tag("python")
        assert memory.tags.count("python") == 1
        
        # Add another tag
        memory.add_keyword_tag("testing")
        assert set(memory.tags) == {"python", "testing"}


class TestEntity:
    """Test cases for Entity entity."""
    
    def test_entity_creation(self):
        """Test creating a valid entity."""
        entity = Entity(
            text="Python",
            entity_type=EntityType.CONCEPT,
            confidence=0.9
        )
        
        assert entity.text == "Python"
        assert entity.entity_type == EntityType.CONCEPT
        assert entity.confidence == 0.9
        assert entity.is_high_confidence()
    
    def test_entity_empty_text(self):
        """Test entity with empty text."""
        with pytest.raises(ValueError, match="Entity text cannot be empty"):
            Entity(
                text="",
                entity_type=EntityType.CONCEPT,
                confidence=0.9
            )
    
    def test_entity_invalid_confidence(self):
        """Test entity with invalid confidence."""
        # Too high
        with pytest.raises(ValueError, match="Confidence must be in"):
            Entity(
                text="Python",
                entity_type=EntityType.CONCEPT,
                confidence=1.1
            )
        
        # Too low
        with pytest.raises(ValueError, match="Confidence must be in"):
            Entity(
                text="Python",
                entity_type=EntityType.CONCEPT,
                confidence=-0.1
            )
    
    def test_entity_confidence_threshold(self):
        """Test entity confidence thresholds."""
        high_conf_entity = Entity(
            text="Important",
            entity_type=EntityType.CONCEPT,
            confidence=0.85
        )
        assert high_conf_entity.is_high_confidence()
        
        low_conf_entity = Entity(
            text="Uncertain",
            entity_type=EntityType.CONCEPT,
            confidence=0.75
        )
        assert not low_conf_entity.is_high_confidence()
        
        # Custom threshold
        assert low_conf_entity.is_high_confidence(threshold=0.7)


class TestRelationship:
    """Test cases for Relationship entity."""
    
    def test_relationship_creation(self):
        """Test creating a valid relationship."""
        from_id = "entity1"
        to_id = "entity2"
        
        relationship = Relationship(
            from_entity_id=from_id,
            to_entity_id=to_id,
            relation_type="relates_to",
            strength=0.8
        )
        
        assert relationship.from_entity_id == from_id
        assert relationship.to_entity_id == to_id
        assert relationship.relation_type == "relates_to"
        assert relationship.strength == 0.8
        assert relationship.is_active()
    
    def test_relationship_empty_relation_type(self):
        """Test relationship with empty relation type."""
        with pytest.raises(ValueError, match="Relation type cannot be empty"):
            Relationship(
                from_entity_id="entity1",
                to_entity_id="entity2",
                relation_type="",
                strength=0.8
            )
    
    def test_relationship_invalid_strength(self):
        """Test relationship with invalid strength."""
        with pytest.raises(ValueError, match="Strength must be in"):
            Relationship(
                from_entity_id="entity1",
                to_entity_id="entity2",
                relation_type="relates_to",
                strength=1.5
            )
    
    def test_relationship_expiration(self):
        """Test relationship expiration."""
        relationship = Relationship(
            from_entity_id="entity1",
            to_entity_id="entity2",
            relation_type="relates_to",
            strength=0.8
        )
        
        # Should be active initially
        assert relationship.is_active()
        
        # Expire the relationship
        relationship.expire()
        
        # Should not be active after expiration
        assert not relationship.is_active()
    
    def test_relationship_invalid_dates(self):
        """Test relationship with invalid date range."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        future = datetime.now(timezone.utc) + timedelta(days=1)
        
        with pytest.raises(ValueError, match="valid_to must be after valid_from"):
            Relationship(
                from_entity_id="entity1",
                to_entity_id="entity2",
                relation_type="relates_to",
                strength=0.8,
                valid_from=future,  # Future start
                valid_to=past       # Past end
            )

    def test_memory_agent_id(self):
        """Test memory creation with agent_id."""
        memory = Memory(
            user_id="user123",
            content="Agent memory",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium(),
            agent_id="agent_007"
        )
        assert memory.agent_id == "agent_007"

    def test_relationship_consensus_fields(self):
        """Test relationship with consensus fields."""
        relationship = Relationship(
            from_entity_id="e1",
            to_entity_id="e2",
            relation_type="KNOWS",
            strength=0.5,
            agent_id="agent_007",
            is_consensus=True,
            consensus_data={"agreement_score": 0.9}
        )
        assert relationship.agent_id == "agent_007"
        assert relationship.is_consensus
        assert relationship.consensus_data == {"agreement_score": 0.9}
