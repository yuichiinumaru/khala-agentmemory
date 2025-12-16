import logging
from typing import Dict, Any, Optional
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.gemini.models import GEMINI_REASONING
from khala.application.verification.verification_gate import VerificationGate, VerificationStatus
from khala.domain.prompt.utils import System, User
from khala.domain.memory.entities import Memory

logger = logging.getLogger(__name__)

class RefinementReasoningService:
    """Service implementing the SOAR (Sample, Verify, Refine) loop."""

    def __init__(self, client: GeminiClient, gate: VerificationGate):
        self.client = client
        self.gate = gate

    async def attempt_solve(self, problem: str, max_iterations: int = 3) -> Dict[str, Any]:
        """
        Attempt to solve a problem with iterative refinement.
        """
        current_solution = ""
        iteration_log = []

        for i in range(max_iterations):
            # 1. Generate / Refine
            if not current_solution:
                prompt = (
                    System("You are a Reasoning Engine. Solve the user problem.") /
                    User(problem)
                )
            else:
                prompt = (
                    System("You are a Reasoning Engine. Refine your previous solution based on feedback.") /
                    User(f"Problem: {problem}\nPrevious Solution: {current_solution}\n\nImprove the solution.")
                )

            response = await self.client.generate_text(
                str(prompt),
                model_id=GEMINI_REASONING
            )
            candidate = response.get("content", "")

            # 2. Verify
            # Create a transient memory object for verification
            mem = Memory(content=candidate)
            verification = await self.gate.verify_memory(mem)

            log_entry = {
                "iteration": i,
                "candidate": candidate,
                "score": verification.final_score,
                "status": verification.final_status,
                "errors": verification.errors
            }
            iteration_log.append(log_entry)

            if verification.final_status == VerificationStatus.PASSED.value:
                return {
                    "status": "solved",
                    "solution": candidate,
                    "iterations": i + 1,
                    "log": iteration_log
                }

            current_solution = candidate

        return {
            "status": "failed",
            "solution": current_solution, # Best effort
            "iterations": max_iterations,
            "log": iteration_log
        }
