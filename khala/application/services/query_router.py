from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.gemini.models import GEMINI_FAST
from khala.domain.prompt.utils import System, User

class QueryRouter:
    def __init__(self, client: GeminiClient):
        self.client = client

    async def route(self, query: str) -> str:
        prompt = (
            System("""You are a Query Router. Classify the query into one category:
            - FACT: Simple factual lookup.
            - CONCEPT: Semantic search for concepts/themes.
            - REASONING: Complex multi-step reasoning required.

            Output ONLY the category name.
            """) /
            User(query)
        )
        response = await self.client.generate_text(
            str(prompt),
            task_type="classification",
            model_id=GEMINI_FAST
        )
        return response.get("content", "").strip().upper()
