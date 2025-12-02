from typing import Dict, Any, List, Optional
import logging
import json
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class BiasDetectionService:
    """
    Service for detecting bias and analyzing sentiment distribution.
    Strategy 152: Bias Detection.
    """
    def __init__(self, gemini_client: GeminiClient, db_client: SurrealDBClient):
        self.gemini_client = gemini_client
        self.db_client = db_client

    async def analyze_memory_bias(self, memory_id: str) -> Dict[str, Any]:
        """
        Analyze a specific memory for potential bias using LLM.
        Updates the memory with bias_score and bias_analysis.
        """
        try:
            # 1. Fetch memory
            query = "SELECT * FROM memory WHERE id = $id;"
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, {"id": memory_id})

                memory = None
                if result:
                    if isinstance(result, list) and len(result) > 0:
                        if isinstance(result[0], list):
                             memory = result[0][0] if result[0] else None
                        else:
                             memory = result[0]

                if not memory:
                     return {"error": "Memory not found"}

            content = memory.get("content", "")

            # 2. Analyze with LLM
            prompt = f"""
            Analyze the following text for potential cognitive biases (e.g., confirmation bias, selection bias, political bias, emotional skew).

            Text:
            "{content}"

            Output a JSON object:
            {{
                "bias_score": float (0.0 = neutral/unbiased, 1.0 = highly biased),
                "bias_analysis": "Brief explanation of the detected bias, or 'None' if neutral.",
                "detected_biases": ["list", "of", "biases"]
            }}
            """

            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="analysis",
                temperature=0.0
            )

            # Parse JSON
            text_resp = response.get("content", "")
            if "```json" in text_resp:
                text_resp = text_resp.split("```json")[1].split("```")[0].strip()
            elif "```" in text_resp:
                text_resp = text_resp.split("```")[1].strip()

            try:
                analysis = json.loads(text_resp)
            except:
                analysis = {"bias_score": 0.0, "bias_analysis": "Failed to parse analysis", "detected_biases": []}

            # 3. Update Memory
            update_query = """
            UPDATE memory
            SET bias_score = $score,
                bias_analysis = $analysis
            WHERE id = $id;
            """

            async with self.db_client.get_connection() as conn:
                await conn.query(update_query, {
                    "id": memory_id,
                    "score": analysis.get("bias_score", 0.0),
                    "analysis": json.dumps(analysis)
                })

            return analysis

        except Exception as e:
            logger.error(f"Bias analysis failed: {e}")
            return {"error": str(e)}

    async def analyze_sentiment_distribution(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze the distribution of sentiment across user's memories.
        Returns statistics about positive, negative, neutral sentiments.
        """
        try:
            # Query to aggregate sentiment
            query = """
            SELECT
                count() as count,
                math::mean(sentiment.score) as avg_score,
                sentiment.label as label
            FROM memory
            WHERE user_id = $user_id AND sentiment IS NOT NONE
            GROUP BY label;
            """

            async with self.db_client.get_connection() as conn:
                results = await conn.query(query, {"user_id": user_id})

                # Process results
                data = results
                if isinstance(results, list) and len(results) > 0 and isinstance(results[0], list):
                     data = results[0]
                elif isinstance(results, list) and len(results) == 0:
                     data = []

                # Calculate distribution
                total = sum(item.get("count", 0) for item in data)
                distribution = {}
                for item in data:
                    label = item.get("label", "unknown")
                    count = item.get("count", 0)
                    percentage = (count / total) * 100 if total > 0 else 0
                    distribution[label] = {
                        "count": count,
                        "percentage": round(percentage, 2),
                        "avg_score": item.get("avg_score", 0.0)
                    }

                return {
                    "total_memories_with_sentiment": total,
                    "distribution": distribution
                }

        except Exception as e:
            logger.error(f"Sentiment distribution analysis failed: {e}")
            return {"error": str(e)}

    async def get_highly_biased_memories(self, user_id: str, threshold: float = 0.7, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve memories with high bias scores.
        """
        try:
            query = """
            SELECT id, content, bias_score, bias_analysis
            FROM memory
            WHERE user_id = $user_id AND bias_score >= $threshold
            ORDER BY bias_score DESC
            LIMIT $limit;
            """
            async with self.db_client.get_connection() as conn:
                results = await conn.query(query, {"user_id": user_id, "threshold": threshold, "limit": limit})

                data = results
                if isinstance(results, list) and len(results) > 0 and isinstance(results[0], list):
                     data = results[0]
                elif isinstance(results, list) and len(results) == 0:
                     data = []

                return data
        except Exception as e:
            logger.error(f"Failed to get biased memories: {e}")
            return []
