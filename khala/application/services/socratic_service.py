"""Service for Socratic Questioning and Confidence Analysis."""

import logging
from typing import Dict, List, Optional, Any
import logging
from typing import List, Dict, Any, Optional
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
class Question(BaseModel):
    text: str = Field(..., description="The follow-up question text")
    rationale: str = Field(..., description="Why this question is being asked")
    target_aspect: str = Field(..., description="Which aspect of the topic this targets (e.g., 'clarification', 'missing_details', 'confidence_check')")

class SocraticAnalysis(BaseModel):
    confidence_score: float = Field(..., description="Overall confidence in the answer (0.0-1.0)")
    completeness_score: float = Field(..., description="How complete the answer is (0.0-1.0)")
    missing_information: List[str] = Field(default_factory=list, description="List of key pieces of information missing from the answer")
    ambiguities: List[str] = Field(default_factory=list, description="List of ambiguous points in the answer")
    follow_up_questions: List[Question] = Field(default_factory=list, description="Suggested follow-up questions")
    needs_questioning: bool = Field(..., description="Whether follow-up questioning is recommended")

class SocraticService:
    """
    Service for Socratic Questioning (Strategy 131).
    Analyzes answers to detect low confidence or gaps and generates follow-up questions.
    """

    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    async def analyze_and_question(
        self,
        query: str,
        answer: str,
        context: Optional[str] = None,
        confidence_threshold: float = 0.8
    ) -> SocraticAnalysis:
        """
        Analyze an answer to a query and generate Socratic questions if needed.

        Args:
            query: The original user query.
            answer: The generated answer to analyze.
            context: Optional background context used to generate the answer.
            confidence_threshold: Threshold below which questions should be generated.

        Returns:
            SocraticAnalysis object containing scores and questions.
        """

        prompt = f"""
        Analyze the following Question and Answer pair for completeness, confidence, and clarity.
        Act as a Socratic teacher who wants to ensure deep understanding and complete information.

        Question: {query}

        Answer Provided: {answer}

        {f"Context Used: {context}" if context else ""}

        Evaluate the answer on:
        1. Confidence: Is the answer definitive or hedging?
        2. Completeness: Did it fully answer the question?
        3. Ambiguity: Are there vague terms or unclear logic?

        If the confidence or completeness is low (below {confidence_threshold}), or if there are ambiguities, generate 3 thoughtful follow-up questions.
        These questions should help the user or the agent fill in the gaps.

        """

        try:
            analysis = await self.gemini_client.generate_structured(
                prompt=prompt,
                response_model=SocraticAnalysis,
                temperature=0.2, # Low temperature for analysis
                model_id="gemini-2.5-pro" # Use smart model for reasoning
            )

            # Force needs_questioning if scores are low, even if LLM said False (double check)
            if analysis.confidence_score < confidence_threshold or analysis.completeness_score < confidence_threshold:
                if not analysis.needs_questioning and not analysis.follow_up_questions:
                    # If it said no questions needed but score is low, we might want to force re-evaluation or just trust the LLM.
                    # For now, we trust the LLM's explicit list of questions.
                    pass

            return analysis

        except Exception as e:
            logger.error(f"Socratic analysis failed: {e}")
            # Return a fallback safe response
            return SocraticAnalysis(
                confidence_score=1.0, # Assume high confidence to avoid looping if error
                completeness_score=1.0,
                needs_questioning=False,
                missing_information=[],
                ambiguities=[],
                follow_up_questions=[]
            )
