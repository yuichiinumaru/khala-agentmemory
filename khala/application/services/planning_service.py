"""Application service for multi-step planning with verification."""

import logging
from typing import Dict, Any, Optional

from khala.domain.planning.planner import Planner, Plan
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class PlanningService:
    """Service to orchestrate planning, verification, and execution."""

    def __init__(self, gemini_client: GeminiClient):
        self.planner = Planner(gemini_client)

    async def generate_verified_plan(self, goal: str, context: str = "", max_retries: int = 3) -> Plan:
        """
        Generate a plan, verify it, and refine it if necessary.

        Args:
            goal: The objective of the plan.
            context: Additional context for planning.
            max_retries: Maximum number of refinement loops.

        Returns:
            A verified Plan object.
        """
        logger.info(f"Generating plan for goal: {goal}")

        # 1. Initial Plan Generation
        plan = await self.planner.create_plan(goal, context)

        # 2. Verification Loop
        for attempt in range(max_retries):
            logger.info(f"Verification attempt {attempt + 1}/{max_retries}")

            verification = await self.planner.verify_plan(plan, context)

            if verification.is_valid:
                logger.info("Plan verified successfully.")
                plan.status = "verified"
                return plan

            logger.warning(f"Plan verification failed: {verification.issues}")

            # 3. Refinement
            if attempt < max_retries - 1:
                logger.info("Refining plan...")
                plan = await self.planner.refine_plan(plan, verification)
            else:
                logger.error("Max retries reached. Returning best effort plan.")
                plan.status = "verification_failed"

        return plan

    async def decompose_plan_steps(self, plan: Plan, context: str = "") -> Plan:
        """
        Decompose all steps in the plan into sub-steps.
        """
        for step in plan.steps:
            await self.planner.decompose_step(step, context)
        return plan
