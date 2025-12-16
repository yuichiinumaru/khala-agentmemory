from typing import List, Dict, Any, Optional
import json
import re
import logging
from dataclasses import dataclass

from khala.infrastructure.gemini.client import GeminiClient
from khala.domain.prompt.utils import System, User, Assistant

logger = logging.getLogger(__name__)

@dataclass
class PlanStep:
    thought: str
    action: str
    args: Dict[str, Any]
    status: str = "pending"
    result: Any = None

class KhalaPlanner:
    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def parse_step(self, text: str) -> PlanStep:
        # Regex for Thought/Action/Args (Robust parsing)
        # Allow whitespace indentation before keys
        thought_match = re.search(r"Thought:\s*(.*?)(?=\n\s*Action:|$)", text, re.DOTALL | re.IGNORECASE)
        action_match = re.search(r"Action:\s*(.*?)(?=\n\s*Args:|$)", text, re.DOTALL | re.IGNORECASE)
        args_match = re.search(r"Args:\s*(.*)", text, re.DOTALL | re.IGNORECASE)

        thought = thought_match.group(1).strip() if thought_match else ""
        action = action_match.group(1).strip() if action_match else "None"
        args_str = args_match.group(1).strip() if args_match else "{}"

        # Try to clean json code blocks if present
        if "```json" in args_str:
            args_str = args_str.split("```json")[1].split("```")[0].strip()
        elif "```" in args_str:
            args_str = args_str.split("```")[1].split("```")[0].strip()

        try:
            args = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            # Fallback for simple args or parsing error
            # If args_str is empty or just whitespace, {} is fine.
            # If it has content but fails JSON, store as raw.
            args = {"raw": args_str}

        return PlanStep(thought, action, args)

    async def execute_task(self, goal: str, worker: Any, max_steps: int = 5) -> List[PlanStep]:
        steps = []

        for _ in range(max_steps):
            history = self._format_history(steps)
            prompt = (
                System("You are an autonomous agent. Use Thought/Action/Args format.") /
                User(f"Goal: {goal}\nHistory:\n{history}")
            )

            response = await self.client.generate_text(str(prompt), task_type="generation")
            content = response.get("content", "")

            step = self.parse_step(content)

            if step.action == "Finish":
                break

            if step.action == "None":
                # Failed to parse or thinking only?
                # Continue loop? Or abort?
                # If thought exists but no action, maybe it's just thinking.
                if step.thought:
                    steps.append(step)
                    continue
                else:
                    break

            # Execute
            try:
                result = await worker.execute(step.action, step.args)
                step.result = result
                step.status = "success"
            except Exception as e:
                step.result = f"Error: {e}"
                step.status = "error"

            steps.append(step)

        return steps

    def _format_history(self, steps: List[PlanStep]) -> str:
        return "\n".join([f"Step {i}: {s.action} -> {s.result}" for i, s in enumerate(steps)])
