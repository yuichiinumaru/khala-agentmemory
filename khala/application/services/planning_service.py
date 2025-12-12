from typing import List, Dict, Any, Optional
import logging
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import json
from khala.infrastructure.gemini.client import GeminiClient
from khala.application.utils import parse_json_safely
from khala.application.services.planning_utils import parse_step

logger = logging.getLogger(__name__)

# --- Legacy Types (Keeping for backward compatibility) ---
@dataclass
class PlanStep:
    id: str
    description: str
    expected_outcome: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    verification_method: Optional[str] = None

@dataclass
class ExecutionPlan:
    id: str
    goal: str
    steps: List[PlanStep]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "draft"
    metadata: Dict[str, Any] = field(default_factory=dict)

# --- New Worker Interface ---
class Worker:
    """Interface for workers (Agents/Tools) executed by the Planner."""
    async def hint(self) -> str:
        """Return description/hint of worker capabilities."""
        raise NotImplementedError

    async def handle(self, param: str, ctx: Dict[str, Any]) -> Any:
        """Execute task."""
        raise NotImplementedError

class PlanningService:
    """
    Service for multi-step planning and verification.
    Strategy 52: Multi-Step Planning.

    Refactored to support 'KhalaPlanner' iterative loop (Harvest Phase 3).
    """
    def __init__(self, gemini_client: GeminiClient, workers: List[Worker] = None):
        self.gemini_client = gemini_client
        self.workers = workers or []
        self.max_steps = 30
        self.max_tasks = 60

    async def run_iterative_plan(self, instruction: str) -> str:
        """
        Execute an iterative planning loop (KhalaPlanner logic).
        """
        global_ctx = {"results": {}}
        already_tasks = 0
        already_steps = 0

        # Prepare agent descriptions
        agent_maps = []
        for i, worker in enumerate(self.workers):
            desc = await worker.hint()
            agent_maps.append({"agent_id": f"agent_{i}", "description": desc})

        messages = [
            {
                "role": "system",
                "content": f"You are a Planner. Available agents: {json.dumps(agent_maps)}. Plan step-by-step using <tasks><subtask>result_x = subtask(agent_y, 'arg')</subtask></tasks> format."
            },
            {"role": "user", "content": instruction}
        ]

        final_goal_status = "Incomplete"

        while already_tasks < self.max_tasks and already_steps < self.max_steps:
            # 1. Generate next step plan
            # Note: Using generate_text for now as it returns dict with 'content'
            response = await self.gemini_client.generate_text(
                prompt=messages[-1]["content"] if len(messages) == 2 else str(messages), # Simplified prompt passing
                task_type="planning",
                temperature=0.1
            )

            content = response.get("content", "")
            messages.append({"role": "model", "content": content})

            # 2. Parse
            goal_text, subtasks = parse_step(content)

            if not subtasks:
                final_goal_status = "Finished or Stalled"
                break

            # 3. Execute Subtasks
            current_results = {}
            for st in subtasks:
                try:
                    agent_idx = int(st["agent_id"].split("_")[-1])
                    if agent_idx < 0 or agent_idx >= len(self.workers):
                        raise ValueError("Invalid agent index")

                    worker = self.workers[agent_idx]
                    result = await worker.handle(st["param"], global_ctx)

                    res_name = st["result_name"]
                    global_ctx["results"][res_name] = result
                    current_results[res_name] = result
                    already_tasks += 1
                except Exception as e:
                    logger.error(f"Task execution failed: {e}")
                    current_results[st.get("result_name", "error")] = f"Error: {str(e)}"

            # 4. Refine / Feedback
            feedback_str = "\n".join([f"{k}: {v}" for k,v in current_results.items()])
            messages.append({
                "role": "user",
                "content": f"Results from previous step:\n{feedback_str}\nProceed to next step or finish."
            })
            already_steps += 1

        return f"Plan Execution Ended. Status: {final_goal_status}"

    async def create_plan(self, goal: str, context: Optional[str] = None) -> ExecutionPlan:
        """
        Decompose a goal into a multi-step execution plan.
        Legacy one-shot method.
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

            data = parse_json_safely(response.get("content", ""))

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

            return parse_json_safely(response.get("content", ""))

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

            data = parse_json_safely(response.get("content", ""))

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
