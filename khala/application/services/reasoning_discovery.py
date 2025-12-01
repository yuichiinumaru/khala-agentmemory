"""Reasoning Discovery Service (Module 13.1.2 - ARM).

Implements discovery of specialized reasoning modules via tree search on code space.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from khala.domain.reasoning.entities import ReasoningModule
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class ReasoningDiscoveryService:
    """Service for discovering and optimizing reasoning modules."""

    def __init__(
        self,
        db_client: SurrealDBClient,
        gemini_client: GeminiClient
    ):
        self.db_client = db_client
        self.gemini_client = gemini_client

    async def discover_modules(
        self,
        task_description: str,
        iterations: int = 3
    ) -> List[ReasoningModule]:
        """Run the module discovery loop."""

        # 1. Generate initial module candidates
        initial_candidates = await self._generate_initial_candidates(task_description)

        discovered_modules = []
        for candidate in initial_candidates:
            await self._save_module(candidate)
            discovered_modules.append(candidate)

        # 2. Iterate and refine
        # (Simplified implementation: Just one pass of refinement for now)
        # Real implementation would use Monte Carlo Tree Search or similar.

        return discovered_modules

    async def _generate_initial_candidates(self, task_description: str) -> List[ReasoningModule]:
        """Generate initial Python code modules for the task."""

        prompt = f"""
        You are an expert AI Architect designing specialized reasoning modules.

        Task: {task_description}

        Generate a Python class that implements a specific reasoning strategy for this task.
        The class should have a method `solve(self, input_data: dict) -> dict`.

        Output valid Python code only.
        """

        try:
            response = await self.gemini_client.generate_content(prompt, model_tier="SMART")
            code = response.text
            # Basic cleanup
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                 code = code.split("```")[1].strip()

            # Create module entity
            module = ReasoningModule.create(
                module_code=code,
                description=f"Generated module for: {task_description[:50]}...",
                input_schema={"type": "dict", "description": "Input data"},
                output_schema={"type": "dict", "description": "Reasoning result"},
                discovery_iteration=0,
                tags=["generated", "arm"]
            )
            return [module]

        except Exception as e:
            logger.error(f"Failed to generate module: {e}")
            return []

    async def _save_module(self, module: ReasoningModule) -> None:
        """Save reasoning module to DB."""
        query = """
        CREATE reasoning_modules CONTENT {
            id: $id,
            module_code: $module_code,
            description: $description,
            input_schema: $input_schema,
            output_schema: $output_schema,
            performance_metrics: $performance_metrics,
            discovery_iteration: $discovery_iteration,
            created_at: $created_at,
            parent_module_id: $parent_module_id,
            tags: $tags
        };
        """
        params = {
            "id": module.id,
            "module_code": module.module_code,
            "description": module.description,
            "input_schema": module.input_schema,
            "output_schema": module.output_schema,
            "performance_metrics": module.performance_metrics,
            "discovery_iteration": module.discovery_iteration,
            "created_at": module.created_at.isoformat(),
            "parent_module_id": module.parent_module_id,
            "tags": module.tags
        }

        async with self.db_client.get_connection() as conn:
            await conn.query(query, params)
