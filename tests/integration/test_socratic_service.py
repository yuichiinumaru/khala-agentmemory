import pytest
from unittest.mock import AsyncMock, MagicMock
from khala.application.services.socratic_service import SocraticService, SocraticAnalysis, Question

@pytest.mark.asyncio
async def test_socratic_service_questioning_needed():
    mock_client = MagicMock()
    mock_client.generate_structured = AsyncMock(return_value=SocraticAnalysis(
        confidence_score=0.5,
        completeness_score=0.6,
        needs_questioning=True,
        missing_information=["context"],
        ambiguities=["vague terms"],
        follow_up_questions=[
            Question(text="Why?", rationale="Clarify", target_aspect="reasoning")
        ]
    ))

    service = SocraticService(mock_client)

    result = await service.analyze_and_question("What is X?", "X is Y")

    assert result.needs_questioning is True
    assert len(result.follow_up_questions) == 1
    assert result.confidence_score == 0.5

    # Check prompt contained query and answer
    call_args = mock_client.generate_structured.call_args
    prompt = call_args[1]['prompt']
    assert "What is X?" in prompt
    assert "X is Y" in prompt

@pytest.mark.asyncio
async def test_socratic_service_no_questions():
    mock_client = MagicMock()
    mock_client.generate_structured = AsyncMock(return_value=SocraticAnalysis(
        confidence_score=0.95,
        completeness_score=0.95,
        needs_questioning=False,
        missing_information=[],
        ambiguities=[],
        follow_up_questions=[]
    ))

    service = SocraticService(mock_client)

    result = await service.analyze_and_question("Simple?", "Simple.", confidence_threshold=0.8)

    assert result.needs_questioning is False
    assert len(result.follow_up_questions) == 0
