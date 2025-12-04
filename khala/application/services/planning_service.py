from typing import List, Dict, Any, Optional
import logging
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

@dataclass
class PlanStep:
    id: str
    description: str
    expected_outcome: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending" # pending, in_progress, completed, failed
    verification_method: Optional[str] = None

@dataclass
class ExecutionPlan:
    id: str
    goal: str
    steps: List[PlanStep]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "draft"
    metadata: Dict[str, Any] = field(default_factory=dict)

class PlanningService:
    """
    Service for multi-step planning and verification.
    Strategy 52: Multi-Step Planning.
    """
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    async def create_plan(self, goal: str, context: Optional[str] = None) -> ExecutionPlan:
        """
        Decompose a goal into a multi-step execution plan.
        """
        prompt = f"""
        You are an expert planner. Decompose the following goal into a sequence of logical, executable steps.

        Goal: "{goal}"

        Context:
        {context or "No additional context."}

        Output a JSON object with the following structure:
        {{
            "steps": [
                {{
                    "id": "step_1",
                    "description": "Description of the step",
                    "expected_outcome": "What success looks like",
                    "dependencies": [],
                    "verification_method": "How to verify success (e.g., 'check_output', 'user_confirmation')"
                }}
            ]
        }}
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="analysis",
                temperature=0.2
            )

            content = response.get("content", "").strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()

            data = json.loads(content)

            steps = []
            for s in data.get("steps", []):
                steps.append(PlanStep(
                    id=s.get("id", str(uuid.uuid4())),
                    description=s.get("description", ""),
                    expected_outcome=s.get("expected_outcome", ""),
                    dependencies=s.get("dependencies", []),
                    verification_method=s.get("verification_method")
                ))

            return ExecutionPlan(
                id=str(uuid.uuid4()),
                goal=goal,
                steps=steps,
                status="created"
            )

        except Exception as e:
            logger.error(f"Plan creation failed: {e}")
            raise

    async def verify_plan_logic(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Verify the logical soundness of a plan using the LLM.
        """
        plan_json = json.dumps({
            "goal": plan.goal,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "dependencies": s.dependencies,
                    "outcome": s.expected_outcome
                }
                for s in plan.steps
            ]
        }, indent=2)

        prompt = f"""
        Analyze the following execution plan for logical soundness, missing dependencies, or potential failures.

        Plan:
        {plan_json}

        Output a JSON object:
        {{
            "is_valid": boolean,
            "issues": ["list of issues found"],
            "suggestions": ["list of suggestions for improvement"],
            "confidence": 0.0 to 1.0
        }}
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="analysis",
                temperature=0.0
            )

            content = response.get("content", "").strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()

            return json.loads(content)

        except Exception as e:
            logger.error(f"Plan verification failed: {e}")
            return {"is_valid": False, "issues": [str(e)]}

    async def refine_plan(self, plan: ExecutionPlan, feedback: str) -> ExecutionPlan:
        """
        Refine a plan based on feedback or verification results.
        """
        # Logic to send plan + feedback to LLM and get updated steps
        plan_json = json.dumps({
            "goal": plan.goal,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "dependencies": s.dependencies,
                    "outcome": s.expected_outcome
                }
                for s in plan.steps
            ]
        }, indent=2)

        prompt = f"""
        Refine the following execution plan based on the provided feedback.

        Plan:
        {plan_json}

        Feedback:
        "{feedback}"

        Output the updated JSON object with the structure:
        {{
            "steps": [...]
        }}
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="analysis",
                temperature=0.2
            )

            content = response.get("content", "").strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()

            data = json.loads(content)

            new_steps = []
            for s in data.get("steps", []):
                new_steps.append(PlanStep(
                    id=s.get("id", str(uuid.uuid4())),
                    description=s.get("description", ""),
                    expected_outcome=s.get("expected_outcome", ""),
                    dependencies=s.get("dependencies", []),
                    verification_method=s.get("verification_method")
                ))

            # Return new plan object
            return ExecutionPlan(
                id=plan.id, # Keep same ID or generate new version ID? Keeping same for now.
                goal=plan.goal,
                steps=new_steps,
                status="refined",
                created_at=datetime.now(timezone.utc),
                metadata={"previous_version_feedback": feedback}
            )

        except Exception as e:
            logger.error(f"Plan refinement failed: {e}")
            raise
