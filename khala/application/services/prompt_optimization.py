"""Prompt Optimization Service (Module 13.1.1 - PromptWizard).

Implements Genetic Algorithm for prompt optimization using LLM feedback.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import random

from khala.domain.prompt.entities import PromptCandidate, PromptEvaluation
from khala.domain.prompt.utils import System, User, Assistant, PromptString
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class PromptOptimizationService:
    """Service for optimizing prompts using evolutionary algorithms."""

    def __init__(
        self,
        db_client: SurrealDBClient,
        gemini_client: GeminiClient
    ):
        self.db_client = db_client
        self.gemini_client = gemini_client
        self.population_size = 10
        self.mutation_rate = 0.3
        self.elite_size = 2

    async def initialize_population(
        self,
        task_id: str,
        initial_prompts: List[str],
        base_instructions: str
    ) -> List[PromptCandidate]:
        """Create initial population of prompt candidates."""
        candidates = []
        for i, prompt in enumerate(initial_prompts):
            candidate = PromptCandidate.create(
                task_id=task_id,
                prompt_text=prompt,
                instructions=base_instructions,
                generation=0,
                mutations_applied=["initialization"]
            )
            candidates.append(candidate)

            # Persist
            await self._save_candidate(candidate)

        return candidates

    async def evolve_prompts(
        self,
        task_id: str,
        num_generations: int = 5,
        evaluation_callback: Optional[callable] = None
    ) -> List[PromptCandidate]:
        """Run the genetic algorithm loop to evolve prompts."""

        # 1. Fetch current generation (or latest)
        population = await self._get_latest_population(task_id)
        if not population:
            logger.warning(f"No population found for task {task_id}")
            return []

        current_gen = population[0].generation

        for gen in range(current_gen + 1, current_gen + num_generations + 1):
            logger.info(f"Starting generation {gen} for task {task_id}")

            # 2. Evaluate fitness (if not already evaluated)
            # In a real scenario, this involves running the agent with the prompt against a benchmark.
            # Here we assume evaluation_callback returns a score or we simulate it.
            scores = []
            for candidate in population:
                if evaluation_callback:
                    score = await evaluation_callback(candidate)
                else:
                    # Simulation/Placeholder
                    score = await self._simulate_evaluation(candidate)

                candidate.fitness_score = score
                scores.append(score)

                # Save evaluation record
                await self._save_evaluation(candidate, score)

            # Sort by fitness
            sorted_population = [x for _, x in sorted(zip(scores, population), key=lambda pair: pair[0], reverse=True)]

            # 3. Selection (Elitism + Tournament/Roulette)
            next_gen = sorted_population[:self.elite_size] # Keep best

            # Fill rest
            while len(next_gen) < self.population_size:
                parent1 = self._tournament_select(sorted_population)
                parent2 = self._tournament_select(sorted_population)

                # 4. Crossover & Mutation
                child_prompt, mutations = await self._mutate_and_crossover(parent1, parent2)

                child = PromptCandidate.create(
                    task_id=task_id,
                    prompt_text=child_prompt,
                    instructions=parent1.instructions, # Inherit base instructions
                    generation=gen,
                    parent_id=parent1.id, # Primary parent
                    mutations_applied=mutations
                )
                next_gen.append(child)

            # 5. Save next generation
            for candidate in next_gen:
                await self._save_candidate(candidate)

            population = next_gen

        return population

    async def _mutate_and_crossover(
        self,
        parent1: PromptCandidate,
        parent2: PromptCandidate
    ) -> tuple[str, List[str]]:
        """Use LLM to generate a mutated prompt from two parents."""

        # Construct prompt using PromptString
        sys_msg = System("You are an expert Prompt Engineer optimizing prompts for an AI agent.")

        user_content = PromptString("""
        Parent Prompt 1 (Score: {score1}):
        "{prompt1}"

        Parent Prompt 2 (Score: {score2}):
        "{prompt2}"

        Task: Create a new, improved prompt that combines the strengths of both parents and introduces a variation (mutation) to potentially improve performance.
        The new prompt should be clear, concise, and directive.

        Output ONLY the new prompt text.
        """).format(
            score1=parent1.fitness_score,
            prompt1=parent1.prompt_text,
            score2=parent2.fitness_score,
            prompt2=parent2.prompt_text
        )

        full_prompt = (sys_msg / User(user_content)).messages()

        try:
            # We use FAST model for this internal optimization loop
            # Note: generate_content usually takes string, need to check if it accepts messages or we convert back to string
            # GeminiClient.generate_content signature: (prompt: str | list[str], ...)
            # We will use string representation for now as the client expects it.
            # In future, GeminiClient should support message lists directly or we use generate_text which might.

            # For now, converting back to string format compatible with current client
            prompt_str = f"{sys_msg}\n\n{user_content}"

            response = await self.gemini_client.generate_content(
                prompt_str,
                model_tier="FAST"
            )
            new_prompt = response.text.strip()
            mutations = ["crossover", "llm_mutation"]
            return new_prompt, mutations
        except Exception as e:
            logger.error(f"Mutation failed: {e}")
            return parent1.prompt_text, ["clone_fallback"]

    def _tournament_select(self, population: List[PromptCandidate], k=3) -> PromptCandidate:
        """Select best individual from random k individuals."""
        tournament = random.sample(population, min(k, len(population)))
        return max(tournament, key=lambda p: p.fitness_score)

    async def _get_latest_population(self, task_id: str) -> List[PromptCandidate]:
        """Fetch the latest generation of prompts for a task."""
        # Query SurrealDB
        query = """
        SELECT * FROM prompt_candidates
        WHERE task_id = $task_id
        ORDER BY generation DESC, fitness_score DESC
        LIMIT $limit;
        """
        params = {"task_id": task_id, "limit": self.population_size}

        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list) and response:
                # Handle nested result
                items = response
                if isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']

                # Check generation consistency - we might get mixed generations if we just limit
                # Ideally we query for max generation first.
                if not items:
                    return []

                latest_gen = items[0]['generation']
                current_gen_items = [i for i in items if i['generation'] == latest_gen]

                return [self._deserialize_candidate(item) for item in current_gen_items]
        return []

    async def _save_candidate(self, candidate: PromptCandidate) -> None:
        """Save a prompt candidate to DB."""
        query = """
        CREATE prompt_candidates CONTENT {
            id: $id,
            task_id: $task_id,
            prompt_text: $prompt_text,
            instructions: $instructions,
            generation: $generation,
            fitness_score: $fitness_score,
            examples: $examples,
            parent_id: $parent_id,
            mutations_applied: $mutations_applied,
            created_at: $created_at,
            metadata: $metadata
        };
        """
        params = {
            "id": candidate.id,
            "task_id": candidate.task_id,
            "prompt_text": candidate.prompt_text,
            "instructions": candidate.instructions,
            "generation": candidate.generation,
            "fitness_score": candidate.fitness_score,
            "examples": candidate.examples,
            "parent_id": candidate.parent_id,
            "mutations_applied": candidate.mutations_applied,
            "created_at": candidate.created_at.isoformat(),
            "metadata": candidate.metadata
        }

        async with self.db_client.get_connection() as conn:
            await conn.query(query, params)

    async def _save_evaluation(self, candidate: PromptCandidate, score: float) -> None:
        """Save evaluation result."""
        eval_obj = PromptEvaluation.create(
            prompt_id=candidate.id,
            task_id=candidate.task_id,
            accuracy=score,
            efficiency=0.0 # Placeholder
        )

        query = """
        CREATE prompt_evaluations CONTENT {
            id: $id,
            prompt_id: $prompt_id,
            task_id: $task_id,
            accuracy: $accuracy,
            efficiency: $efficiency,
            human_preference: $human_preference,
            feedback_rules_triggered: $feedback_rules_triggered,
            created_at: $created_at
        };
        """
        params = {
            "id": eval_obj.id,
            "prompt_id": eval_obj.prompt_id,
            "task_id": eval_obj.task_id,
            "accuracy": eval_obj.accuracy,
            "efficiency": eval_obj.efficiency,
            "human_preference": eval_obj.human_preference,
            "feedback_rules_triggered": eval_obj.feedback_rules_triggered,
            "created_at": eval_obj.created_at.isoformat()
        }

        async with self.db_client.get_connection() as conn:
            await conn.query(query, params)

    async def get_prompt_lineage(self, prompt_id: str) -> List[PromptCandidate]:
        """
        Retrieve the ancestral lineage of a prompt.
        Returns a list of PromptCandidates starting from the given prompt back to the root.
        """
        lineage = []
        current_id = prompt_id

        # Loop until we reach a prompt with no parent or run out of iterations (safety)
        for _ in range(50):  # Safety limit for depth
            if not current_id:
                break

            # If ID format is prompt_candidates:uuid, strip prefix if needed by query,
            # but usually SurrealDB handles records.
            # We'll use a direct fetch.

            query = "SELECT * FROM prompt_candidates WHERE id = $id"
            # Ensure ID format if needed, but assuming simple fetch works with record ID or string

            async with self.db_client.get_connection() as conn:
                # Need to handle potential prefix issue if passed string doesn't have it but DB does
                if ":" not in current_id:
                     # Attempt to format it if it looks like a UUID but missing table
                     pass

                response = await conn.query(query, {"id": current_id})

                if not response:
                    break

                items = response
                if isinstance(response, list) and response and isinstance(response[0], dict) and 'result' in response[0]:
                     items = response[0]['result']

                if not items:
                    break

                data = items[0]
                candidate = self._deserialize_candidate(data)
                lineage.append(candidate)

                current_id = candidate.parent_id

        return lineage

    async def get_evolution_tree(self, task_id: str) -> Dict[str, Any]:
        """
        Retrieve the full evolutionary tree for a task.
        Returns a nested dictionary structure representing the tree.
        """
        query = """
        SELECT * FROM prompt_candidates
        WHERE task_id = $task_id
        ORDER BY generation ASC
        """

        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, {"task_id": task_id})

            items = []
            if isinstance(response, list) and response:
                if isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']
                else:
                    items = response

            if not items:
                return {}

            candidates = [self._deserialize_candidate(item) for item in items]

            # Build tree
            # Map by ID
            node_map = {c.id: {"data": c, "children": []} for c in candidates}
            roots = []

            for c in candidates:
                node = node_map[c.id]
                parent_id = c.parent_id

                # SurrealDB might store parent_id as Record(prompt_candidates:uuid) or just uuid string
                # Normalize lookup if needed. Assuming string match for now.

                if parent_id and parent_id in node_map:
                    node_map[parent_id]["children"].append(node)
                else:
                    roots.append(node)

            return {"roots": roots, "total_candidates": len(candidates)}

    def _deserialize_candidate(self, data: Dict[str, Any]) -> PromptCandidate:
        """Deserialize dict to PromptCandidate."""
        return PromptCandidate(
            id=data['id'].replace("prompt_candidates:", "") if "prompt_candidates:" in str(data['id']) else data['id'],
            task_id=data['task_id'],
            prompt_text=data['prompt_text'],
            instructions=data['instructions'],
            generation=data['generation'],
            fitness_score=data.get('fitness_score', 0.0),
            examples=data.get('examples', []),
            parent_id=data.get('parent_id'),
            mutations_applied=data.get('mutations_applied', []),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            metadata=data.get('metadata', {})
        )

    async def _simulate_evaluation(self, candidate: PromptCandidate) -> float:
        """Simulate an evaluation score (0.0 to 1.0) for testing."""
        # Simple heuristic: length + random noise
        # This is just a placeholder.
        base = 0.5
        noise = random.uniform(-0.1, 0.1)
        # Maybe length > 50 is better?
        length_bonus = 0.1 if len(candidate.prompt_text) > 50 else 0.0
        return min(1.0, max(0.0, base + noise + length_bonus))
