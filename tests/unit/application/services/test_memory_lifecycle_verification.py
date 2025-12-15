import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from khala.application.services.memory_lifecycle import MemoryLifecycleService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.application.verification.verification_gate import VerificationGate, VerificationResult, VerificationStatus

@pytest.fixture
def mock_repo():
    return AsyncMock()

@pytest.fixture
def mock_gemini():
    return AsyncMock()

@pytest.fixture
def mock_verification_gate():
    gate = AsyncMock(spec=VerificationGate)
    # Default behavior: Return a passed result
    result = VerificationResult("mem-1", "standard")
    result.final_status = VerificationStatus.PASSED.value
    result.final_score = 0.9
    gate.verify_memory.return_value = result
    return gate

@pytest.fixture
def lifecycle_service(mock_repo, mock_gemini, mock_verification_gate):
    scorer = AsyncMock()
    scorer.calculate_significance.return_value = ImportanceScore(0.5)

    privacy = AsyncMock()
    sanitization_result = MagicMock()
    sanitization_result.was_sanitized = False
    sanitization_result.sanitized_text = "clean"
    privacy.sanitize_content.return_value = sanitization_result

    bias_result = MagicMock()
    bias_result.is_biased = False
    privacy.detect_bias.return_value = bias_result

    return MemoryLifecycleService(
        repository=mock_repo,
        gemini_client=mock_gemini,
        verification_gate=mock_verification_gate,
        significance_scorer=scorer,
        privacy_safety_service=privacy,
        conflict_resolution_service=AsyncMock()
    )

@pytest.mark.asyncio
async def test_ingest_memory_calls_verification_gate(lifecycle_service, mock_repo, mock_verification_gate):
    memory = Memory(
        user_id="user-1",
        content="The sky is blue.",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5)
    )

    mock_repo.create.return_value = "mem-1"

    await lifecycle_service.ingest_memory(memory, check_quality=True)

    # Assert verification gate was called
    mock_verification_gate.verify_memory.assert_called_once_with(memory)

    # Assert metadata was updated
    assert memory.metadata.get("verification_status") == "passed"
    assert memory.metadata.get("verification_score") == 0.9

@pytest.mark.asyncio
async def test_ingest_memory_skips_verification_if_disabled(lifecycle_service, mock_repo, mock_verification_gate):
    memory = Memory(
        user_id="user-1",
        content="Skip check.",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5)
    )

    await lifecycle_service.ingest_memory(memory, check_quality=False)

    mock_verification_gate.verify_memory.assert_not_called()

@pytest.mark.asyncio
async def test_ingest_memory_handles_failed_verification(lifecycle_service, mock_repo, mock_verification_gate):
    # Setup failure result
    fail_result = VerificationResult("mem-fail", "standard")
    fail_result.final_status = VerificationStatus.FAILED.value
    fail_result.final_score = 0.2
    fail_result.errors = ["Fact check failed"]
    mock_verification_gate.verify_memory.return_value = fail_result

    memory = Memory(
        user_id="user-1",
        content="The moon is made of cheese.",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5)
    )

    # We expect it to still ingest but tag it as FAILED (soft rejection)

    await lifecycle_service.ingest_memory(memory, check_quality=True)

    assert memory.metadata.get("verification_status") == "failed"
    assert memory.metadata.get("verification_score") == 0.2
    assert "Fact check failed" in str(memory.metadata.get("verification_errors"))
