import logging
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.gemini.models import GEMINI_FAST
from khala.domain.memory.entities import Memory
from khala.domain.prompt.utils import System, User

logger = logging.getLogger(__name__)

class SelfChallengingService:
    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    async def challenge_memory(self, query: str, memory: Memory) -> bool:
        """
        Challenge a retrieved memory against the query.
        Returns True if the memory survives the challenge.
        """
        prompt = (
            System("You are a Skeptic Verifier. Your job is to check if a Memory actually helps answer a Query.") /
            User(f"""
            Query: {query}
            Memory: {memory.content}

            Task: Does this memory provide relevant, non-contradictory information for the query?
            If the memory is irrelevant, misleading, or a hallucination relative to the query context, answer REJECTED.
            Otherwise, answer VERIFIED.
            """)
        )

        try:
            response = await self.client.generate_text(
                str(prompt),
                task_type="classification",
                model_id=GEMINI_FAST
            )
            content = response.get("content", "").strip().upper()

            if "REJECTED" in content:
                logger.info(f"Memory {memory.id} rejected by challenge against query '{query}'")
                return False

            return True

        except Exception as e:
            logger.warning(f"Challenge failed: {e}")
            return True # Fail open (allow memory if verify fails)
