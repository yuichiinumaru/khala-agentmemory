"""Service for handling privacy (sanitization) and safety (bias) checks."""

import re
import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from khala.infrastructure.gemini.client import GeminiClient
from khala.application.utils import parse_json_safely

logger = logging.getLogger(__name__)

@dataclass
class SanitizationResult:
    """Result of a sanitization operation."""
    original_text: str
    sanitized_text: str
    redacted_items: List[Dict[str, str]]
    was_sanitized: bool

@dataclass
class BiasResult:
    """Result of a bias detection operation."""
    bias_score: float  # 0.0 to 1.0 (1.0 = highly biased)
    categories: List[str]
    analysis: str
    is_biased: bool

class PrivacySafetyService:
    """Service for handling privacy (sanitization) and safety (bias) checks."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client or GeminiClient()

        # Regex patterns for common PII
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            "ipv4": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            "api_key_google": r'AIza[0-9A-Za-z-_]{35}',
            "api_key_generic": r'(?:api_key|access_token|secret)[\s=:]+([a-zA-Z0-9_\-]{20,})'
        }

    async def sanitize_content(
        self,
        text: str,
        use_llm: bool = False
    ) -> SanitizationResult:
        """Sanitize text by removing PII.

        Args:
            text: Text to sanitize
            use_llm: Whether to use LLM for advanced sanitization

        Returns:
            SanitizationResult object
        """
        sanitized_text = text
        redacted_items = []

        # 1. Regex Sanitization
        for pii_type, pattern in self.pii_patterns.items():
            def replace_callback(match):
                redacted_items.append({
                    "type": pii_type,
                    "masked_text": f"<{pii_type.upper()}>"
                })
                return f"<{pii_type.upper()}>"

            sanitized_text = re.sub(pattern, replace_callback, sanitized_text)

        # 2. LLM Sanitization
        if use_llm and self.gemini_client:
            try:
                # FIX: Do NOT ask for the PII text back. Only types.
                prompt = f"""
                Analyze the following text for Personally Identifiable Information (PII)
                or sensitive secrets that standard regex might miss.

                If found, replace them with <REDACTED:TYPE>.
                Return valid JSON:
                {{
                    "sanitized_text": "text with redactions",
                    "redacted_types": ["NAME", "ADDRESS"]
                }}

                Text to sanitize:
                {sanitized_text}
                """

                response = await self.gemini_client.generate_text(
                    prompt=prompt,
                    task_type="generation",
                    model_id="gemini-2.0-flash",
                    temperature=0.0
                )

                data = parse_json_safely(response.get("content", ""))

                if "sanitized_text" in data:
                    sanitized_text = data["sanitized_text"]

                # We only record the TYPES of what was redacted by LLM to avoid leaking content
                if "redacted_types" in data and isinstance(data["redacted_types"], list):
                    for r_type in data["redacted_types"]:
                        redacted_items.append({
                            "type": str(r_type),
                            "masked_text": f"<{r_type}>"
                        })

            except Exception as e:
                logger.warning(f"LLM sanitization failed: {e}")

        return SanitizationResult(
            original_text=text,
            sanitized_text=sanitized_text,
            redacted_items=redacted_items,
            was_sanitized=len(redacted_items) > 0
        )

    async def detect_bias(self, text: str) -> BiasResult:
        """Detect bias in text."""
        try:
            prompt = f"""
            Analyze the following text for bias.
            Return ONLY JSON:
            {{
                "score": 0.0,
                "categories": ["political", "gender"],
                "analysis": "Brief analysis"
            }}

            Text:
            {text}
            """

            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="classification",
                model_id="gemini-2.0-flash",
                temperature=0.0
            )

            data = parse_json_safely(response.get("content", ""))

            score = float(data.get("score", 0.0))
            categories = data.get("categories", [])
            analysis = data.get("analysis", "")

            return BiasResult(
                bias_score=score,
                categories=categories,
                analysis=analysis,
                is_biased=score > 0.3
            )

        except Exception as e:
            logger.error(f"Bias detection failed: {e}")
            return BiasResult(
                bias_score=0.0,
                categories=[],
                analysis="Error during detection",
                is_biased=False
            )
