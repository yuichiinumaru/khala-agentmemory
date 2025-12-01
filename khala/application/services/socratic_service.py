"""Service for Socratic Questioning and Confidence Analysis."""

import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from ...infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class SocraticEvaluation(BaseModel):
    """Evaluation result of an answer."""
    confidence_score: float = Field(..., description="Confidence score between 0.0 and 1.0")
    completeness_score: float = Field(..., description="Completeness score between 0.0 and 1.0")
    missing_information: List[str] = Field(default_factory=list, description="List of missing information points")
    reasoning: str = Field(..., description="Reasoning for the evaluation")
    needs_follow_up: bool = Field(..., description="Whether follow-up questions are needed")

class FollowUpQuestions(BaseModel):
    """Generated follow-up questions."""
    questions: List[str] = Field(..., description="List of follow-up questions")
    rationale: str = Field(..., description="Why these questions are being asked")

class SocraticService:
    """Service to detect low-confidence answers and generate socratic follow-up questions."""

    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        context: Optional[str] = None
    ) -> SocraticEvaluation:
        """Evaluate an answer for confidence and completeness."""

        prompt = f"""
        Analyze the following Question and Answer for confidence and completeness.

        Question: {question}
        Answer: {answer}
        Context: {context or "No additional context"}

        Evaluate:
        1. Confidence: How confident does the answer sound? Is it hedging?
        2. Completeness: Does it fully answer the question?
        3. Missing Info: What is missing?

        Return a structured evaluation.
        """

        try:
            return await self.client.generate_object(
                prompt=prompt,
                response_schema=SocraticEvaluation,
                model_id="gemini-2.5-pro",
                temperature=0.1
            )
        except Exception as e:
            logger.error(f"Failed to evaluate answer: {e}")
            # Fallback
            return SocraticEvaluation(
                confidence_score=0.5,
                completeness_score=0.5,
                missing_information=["Error during evaluation"],
                reasoning=f"Evaluation failed: {str(e)}",
                needs_follow_up=True
            )

    async def generate_follow_up(
        self,
        question: str,
        answer: str,
        evaluation: Optional[SocraticEvaluation] = None
    ) -> List[str]:
        """Generate follow-up questions to fill knowledge gaps."""

        if not evaluation:
            evaluation = await self.evaluate_answer(question, answer)

        if not evaluation.needs_follow_up and evaluation.confidence_score > 0.8:
            return []

        prompt = f"""
        Based on the following Q&A and evaluation, generate 3 Socratic follow-up questions
        to help fill the knowledge gaps or clarify the answer.

        Question: {question}
        Answer: {answer}
        Missing Info: {evaluation.missing_information}

        The questions should be polite, constructive, and aimed at eliciting the missing information.
        """

        try:
            result = await self.client.generate_object(
                prompt=prompt,
                response_schema=FollowUpQuestions,
                model_id="gemini-2.5-pro",
                temperature=0.7
            )
            return result.questions
        except Exception as e:
            logger.error(f"Failed to generate follow-up questions: {e}")
            return ["Could you please provide more details?"]

    async def process_interaction(self, question: str, answer: str) -> Dict[str, Any]:
        """Process a full interaction and return evaluation + questions if needed."""
        evaluation = await self.evaluate_answer(question, answer)

        result = {
            "evaluation": evaluation.model_dump(),
            "follow_up_questions": []
        }

        if evaluation.needs_follow_up:
            questions = await self.generate_follow_up(question, answer, evaluation)
            result["follow_up_questions"] = questions

        return result
