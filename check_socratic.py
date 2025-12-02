"""Verification script for SocraticService."""
import asyncio
from unittest.mock import MagicMock, AsyncMock
from khala.application.services.socratic_service import SocraticService, SocraticEvaluation, FollowUpQuestions
from khala.infrastructure.gemini.client import GeminiClient

async def main():
    print("Verifying SocraticService...")

    # Mock Gemini Client
    mock_client = MagicMock(spec=GeminiClient)

    # Mock generate_object for evaluation
    async def mock_generate_evaluation(*args, **kwargs):
        if kwargs.get("response_schema") == SocraticEvaluation:
            return SocraticEvaluation(
                confidence_score=0.4,
                completeness_score=0.5,
                missing_information=["Specific details", "Examples"],
                reasoning="Answer is vague.",
                needs_follow_up=True
            )
        elif kwargs.get("response_schema") == FollowUpQuestions:
             return FollowUpQuestions(
                 questions=["Can you explain more?", "Do you have examples?"],
                 rationale="To get more info"
             )
        return None

    mock_client.generate_object = AsyncMock(side_effect=mock_generate_evaluation)

    service = SocraticService(mock_client)

    question = "How does the system work?"
    answer = "It works well."

    print("Testing process_interaction...")
    result = await service.process_interaction(question, answer)

    print(f"Result: {result}")

    assert result["evaluation"]["confidence_score"] == 0.4
    assert result["evaluation"]["needs_follow_up"] is True
    assert len(result["follow_up_questions"]) == 2
    assert result["follow_up_questions"][0] == "Can you explain more?"

    print("Verification passed!")

if __name__ == "__main__":
    asyncio.run(main())
