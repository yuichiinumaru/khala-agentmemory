"""
Test suite for Verification Gate (Module 7).
Verifies the self-verification loop and gate coordination.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

from khala.application.verification.verification_gate import VerificationGate, GateType, VerificationResult
from khala.application.verification.self_verification import SelfVerificationLoop
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.infrastructure.gemini.client import GeminiClient

class TestVerificationGate:
    """Test cases for verification gate."""

    @pytest.fixture
    def mock_gemini(self):
        """Mock Gemini client."""
        client = MagicMock(spec=GeminiClient)
        client.generate_text = AsyncMock()
        return client

    @pytest.fixture
    def mock_verification_loop(self):
        """Mock verification loop."""
        loop = MagicMock(spec=SelfVerificationLoop)
        loop.verify_memory = AsyncMock()
        return loop

    @pytest.fixture
    def gate(self, mock_gemini, mock_verification_loop):
        """Create verification gate with mocks."""
        gate = VerificationGate(mock_gemini)
        gate.verification_loop = mock_verification_loop
        # Mock database client inside _update_memory_verification
        # We can mock this by patching SurrealDBClient in the module where VerificationGate is defined
        return gate

    @pytest.mark.asyncio
    async def test_standard_verification(self, gate, mock_verification_loop):
        """Test standard verification flow."""
        memory = Memory(
            user_id="user1",
            content="Test content",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium()
        )

        # Mock successful verification
        mock_result = {
            "overall_score": 0.9,
            "result": "PASSED",
            "passed_checks": 6,
            "failed_checks": 0,
            "checks": []
        }
        mock_verification_loop.verify_memory.return_value = mock_result

        with patch('khala.infrastructure.surrealdb.client.SurrealDBClient') as MockDB:
             mock_db_instance = MockDB.return_value
             mock_db_instance.update_memory = AsyncMock()

             result = await gate.verify_memory(memory, GateType.STANDARD)

             assert result.final_status == "passed"
             assert result.final_score == 0.9
             assert result.self_verification_result is not None
             assert result.debate_result is None

             mock_verification_loop.verify_memory.assert_called_once_with(memory, None)
             mock_db_instance.update_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_comprehensive_verification_triggers_debate(self, gate, mock_verification_loop, mock_gemini):
        """Test comprehensive verification triggers debate for high importance."""
        memory = Memory(
            user_id="user1",
            content="Important content",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.very_high() # 0.9
        )

        # Mock verification result (passed but needs debate due to importance)
        mock_verification_loop.verify_memory.return_value = {
            "overall_score": 0.8,
            "result": "PASSED",
            "passed_checks": 6,
            "failed_checks": 0
        }

        # Mock debate session
        with patch('khala.application.verification.verification_gate.DebateSession') as MockDebateSession:
            mock_session = MockDebateSession.return_value
            mock_debate_result = MagicMock()
            mock_debate_result.final_score = 0.95
            mock_debate_result.confidence_level = 0.9
            # DebateResult is a dataclass, but MagicMock should be fine for simple property access if we are careful
            # Or we can create a real DebateResult object if available.

            mock_session.run_debate = AsyncMock(return_value=mock_debate_result)

            with patch('khala.infrastructure.surrealdb.client.SurrealDBClient'):
                 result = await gate.verify_memory(memory, GateType.COMPREHENSIVE)

                 assert result.debate_result is not None
                 assert result.self_verification_result is not None
                 mock_session.run_debate.assert_called_once()
