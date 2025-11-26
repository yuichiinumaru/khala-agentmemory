"""Mixture of Thought (MoT) reasoning engine."""

import logging
import asyncio
from dataclasses import dataclass
from typing import List, Dict
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

@dataclass
class ReasoningPath:
    """A single reasoning path."""
    perspective: str
    content: str
    confidence: float

class MixtureOfThought:
    """
    Implements Mixture of Thought reasoning by generating multiple 
    reasoning paths and synthesizing them.
    """
    
    PERSPECTIVES = [
        "Analytical (Step-by-step logic)",
        "Creative (Out-of-the-box thinking)",
        "Critical (Devil's advocate)",
        "Historical (Past precedents)",
        "Systems Thinking (Interconnectedness)"
    ]
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client
        
    async def reason(self, problem: str, perspectives: List[str] = None) -> str:
        """
        Solve a problem using Mixture of Thought.
        """
        if not perspectives:
            perspectives = self.PERSPECTIVES[:3] # Default to first 3
            
        # Generate paths in parallel
        tasks = [self._generate_path(problem, p) for p in perspectives]
        paths = await asyncio.gather(*tasks)
        
        # Synthesize
        return await self._synthesize(problem, paths)
        
    async def _generate_path(self, problem: str, perspective: str) -> ReasoningPath:
        """Generate a single reasoning path."""
        prompt = f"""
        Problem: {problem}
        
        Adopt the following perspective: {perspective}
        
        Analyze the problem and propose a solution or insight.
        Be concise.
        """
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                model_id="gemini-2.0-flash",
                temperature=0.7
            )
            return ReasoningPath(perspective, response["content"], 0.8)
        except Exception as e:
            logger.error(f"Error in MoT path {perspective}: {e}")
            return ReasoningPath(perspective, "Error generating path", 0.0)
            
    async def _synthesize(self, problem: str, paths: List[ReasoningPath]) -> str:
        """Synthesize multiple reasoning paths into a final answer."""
        paths_text = "\n\n".join([f"--- {p.perspective} ---\n{p.content}" for p in paths])
        
        prompt = f"""
        Problem: {problem}
        
        I have analyzed this problem from multiple perspectives:
        
        {paths_text}
        
        Synthesize these insights into a single, comprehensive, and robust answer.
        Resolve any contradictions and highlight the strongest points.
        """
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                model_id="gemini-2.5-flash", # Use smarter model for synthesis
                temperature=0.2
            )
            return response["content"]
        except Exception as e:
            logger.error(f"Error in MoT synthesis: {e}")
            return "Error synthesizing results."
