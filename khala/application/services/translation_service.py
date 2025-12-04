"""Translation Service for Multilingual Search (Strategy 95).

This service handles language detection and translation using Gemini.
"""

import logging
from typing import Dict, Any, Optional
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class TranslationService:
    """Service for translating queries and content."""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    async def detect_and_translate(self, text: str, target_lang: str = "English") -> Dict[str, Any]:
        """
        Detect language of text and translate if different from target.

        Returns:
            {
                "original_text": str,
                "detected_language": str,
                "translated_text": str,
                "was_translated": bool
            }
        """
        prompt = f"""
        Analyze the following text:
        "{text}"

        1. Detect the language.
        2. If it is NOT {target_lang}, translate it to {target_lang}.
        3. If it IS {target_lang}, return the original text.

        Return JSON:
        {{
            "detected_language": "language_name",
            "translated_text": "text_in_{target_lang}",
            "confidence": 0.95
        }}
        """

        try:
            # We use a fast model for translation to keep latency low
            response = await self.gemini_client.generate_text(
                prompt,
                temperature=0.0,
                model_id="gemini-2.5-flash", # Use Flash for speed
                task_type="classification"
            )

            content = response.get('content', '')
            # Parse JSON
            import json
            import re

            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                detected = data.get("detected_language", "Unknown")
                translated = data.get("translated_text", text)

                was_translated = detected.lower() != target_lang.lower() and translated != text

                return {
                    "original_text": text,
                    "detected_language": detected,
                    "translated_text": translated,
                    "was_translated": was_translated
                }

            return {
                "original_text": text,
                "detected_language": "Unknown",
                "translated_text": text,
                "was_translated": False
            }

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {
                "original_text": text,
                "detected_language": "Error",
                "translated_text": text,
                "was_translated": False
            }
