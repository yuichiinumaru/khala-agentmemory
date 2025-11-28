"""Integration tests for Module 04: Processing & Analysis (Intelligence)."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from khala.domain.memory.entities import Memory, MemoryTier, Entity, Relationship
from khala.domain.memory.value_objects import ImportanceScore, DecayScore
from khala.application.services.entity_extraction import EntityExtractionService, EntityType
from khala.application.services.temporal_analyzer import TemporalAnalysisService
from khala.infrastructure.background.jobs.job_processor import JobProcessor, JobPriority
from khala.infrastructure.background.scheduler import BackgroundScheduler

@pytest.fixture
def mock_db_client():
    client = AsyncMock()
    # Mock update_memory to return the memory passed to it
    client.update_memory = AsyncMock()
    return client

@pytest.fixture
def sample_memory():
    return Memory(
        id="mem_123",
        user_id="user_1",
        content="John Doe works at Acme Corp in New York.",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.8),
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
        updated_at=datetime.now(timezone.utc),
        accessed_at=datetime.now(timezone.utc),
        access_count=10
    )

@pytest.mark.asyncio
async def test_entity_extraction_service():
    """Test Entity Extraction Service (M04.DEV.001 & M04.DEV.002)."""
    # Mock Gemini client to avoid API calls
    with patch("khala.application.services.entity_extraction.genai") as mock_genai:
        service = EntityExtractionService(api_key="fake_key")

        # Override _extract_with_gemini to avoid actual calls but use the method structure
        # Or simpler: just use regex fallback which is built-in
        service.gemini_client = None

        # Test with text containing entities that regex can catch
        text = "Contact support@example.com or visit https://example.com"
        entities = await service.extract_entities_from_text(text)

        assert len(entities) >= 2
        assert any(e.entity_type == EntityType.EMAIL for e in entities)
        assert any(e.entity_type == EntityType.URL for e in entities)

        # Test relationship detection (heuristic based)
        entities_list = [
            MagicMock(text="John", entity_type=EntityType.PERSON),
            MagicMock(text="Acme", entity_type=EntityType.ORGANIZATION)
        ]
        text_rel = "John works at Acme"
        relationships = service.detect_entity_relationships(entities_list, text_rel)
        # Note: The heuristic regex in service might match specific patterns
        # Current service regex: r"(\w+)\s+(?:works?\s+at|is\s+at|employment\s+at)\s+(\w+)"

        # We need to construct ExtractedEntity objects properly for the matching to work
        from khala.application.services.entity_extraction import ExtractedEntity

        e1 = ExtractedEntity(text="John", entity_type=EntityType.PERSON, confidence=1.0, start_pos=0, end_pos=4)
        e2 = ExtractedEntity(text="Acme", entity_type=EntityType.ORGANIZATION, confidence=1.0, start_pos=14, end_pos=18)

        rels = service.detect_entity_relationships([e1, e2], text_rel)
        assert len(rels) > 0
        assert rels[0].relationship_type.value == "works_at"

@pytest.mark.asyncio
async def test_temporal_analysis_service(mock_db_client, sample_memory):
    """Test Temporal Analyzer (M04.DEV.003)."""
    service = TemporalAnalysisService(db_client=mock_db_client)

    # 1. Test Decay Calculation
    score = service.calculate_decay_score(sample_memory)
    assert isinstance(score, DecayScore)
    assert score.value < sample_memory.importance.value

    # 2. Test Promotion Logic
    # Working memory with high importance/access should be promoted
    assert service.should_promote(sample_memory) is True

    # 3. Test Archival Logic
    # High importance memory should not be archived
    # Note: sample_memory is 2 days old working memory.
    # should_archive says: if working and age > 1.0 day -> Archive.
    # But importance 0.8 is not "high enough" to prevent archive in Working tier logic?
    # Logic: if memory.importance.value > 0.9: return False
    # sample has 0.8. So it returns True.
    # Let's adjust sample importance to 0.95 to test the "High importance" check.
    high_imp_memory = Memory(
        id="mem_high",
        user_id="user_1",
        content="Important",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.95),
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
        updated_at=datetime.now(timezone.utc),
        accessed_at=datetime.now(timezone.utc),
        access_count=10
    )
    assert service.should_archive(high_imp_memory) is False

    # Old, low importance memory
    old_memory = Memory(
        id="mem_old",
        user_id="user_1",
        content="Old stuff",
        tier=MemoryTier.SHORT_TERM,
        importance=ImportanceScore(0.1),
        created_at=datetime.now(timezone.utc) - timedelta(days=40),
        updated_at=datetime.now(timezone.utc),
        accessed_at=datetime.now(timezone.utc),
        access_count=0
    )
    assert service.should_archive(old_memory) is True

@pytest.mark.asyncio
async def test_scheduler_and_job_processor(mock_db_client):
    """Test Scheduler and Job Processor (M04.DEV.004)."""
    # Setup
    processor = JobProcessor(redis_url="redis://fake", enable_metrics=False)
    # Mock redis to force memory queue
    processor.redis_client = None

    scheduler = BackgroundScheduler(processor)

    # Define a test task
    task_payload = {"test": "data"}
    scheduler.add_task(
        name="test_task",
        job_type="consistency_check", # Use a valid job type
        interval_seconds=1,
        payload=task_payload
    )

    # Start scheduler
    await scheduler.start()

    # Wait for task to trigger (it runs immediately/shortly)
    await asyncio.sleep(0.1)

    # Check if job was submitted to processor
    # Since we use memory queue, we can check it
    assert not processor._memory_queue.empty()
    job = processor._memory_queue.get_nowait()
    assert job.job_type == "consistency_check"
    assert job.payload == task_payload

    await scheduler.stop()

@pytest.mark.asyncio
async def test_skill_library_registration():
    """Test Skill Library (M04.DEV.005)."""
    from khala.domain.skills.services import SkillLibraryService
    from khala.domain.skills.entities import Skill
    from khala.domain.skills.value_objects import SkillType, SkillLanguage

    mock_repo = AsyncMock()
    service = SkillLibraryService(mock_repo)

    # Register from code
    code = """
def calculate_sum(a, b):
    '''Calculates sum of two numbers.'''
    return a + b
"""
    # Mock code analysis service response inside the service logic?
    # The service imports CodeAnalysisService internally.
    # To test this unit properly without dependencies, we'd need to mock sys.modules or refactor.
    # For now, let's test the direct register_skill method.

    skill = Skill(
        name="test_skill",
        description="Test description",
        code="print('hello')",
        language=SkillLanguage.PYTHON,
        skill_type=SkillType.ATOMIC,
        parameters=[],
        return_type="None"
    )

    mock_repo.get_by_name.return_value = None
    mock_repo.create.return_value = "skill_id_123"

    skill_id = await service.register_skill(skill)
    assert skill_id == "skill_id_123"
    mock_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_instruction_registry():
    """Test Instruction Registry (M04.DEV.006)."""
    from khala.domain.instruction.services import InstructionRegistry
    from khala.domain.instruction.entities import Instruction, InstructionType

    registry = InstructionRegistry()

    instr = Instruction(
        id="instr_1",
        name="test_instr",
        content="You are a helpful assistant named ${name}.",
        instruction_type=InstructionType.PERSONA
    )

    registry.register_instruction(instr)
    assert registry.get_instruction(instr.id) == instr

    # Create set
    iset = registry.create_instruction_set("set_1", "Test Set", [instr.id])
    assert len(iset.instructions) == 1

    # Compile
    prompt = registry.compile_prompt("set_1", {"name": "Khala"})
    assert "You are a helpful assistant named Khala." in prompt
