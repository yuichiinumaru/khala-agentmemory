"""Service for Privacy and Safety checks (Module 12).

This service implements strategies for Sanitization (Strategy 132) and
Bias Detection (Strategy 152).
"""

import re
import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass

from khala.infrastructure.gemini.client import GeminiClient

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
            # Simple API key heuristics
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
            matches = re.finditer(pattern, sanitized_text)
            # Process in reverse to avoid index shifting issues if we were doing it differently,
            # but here we just replace string matches.
            # However, if we replace with something of different length, subsequent matches might be off?
            # Regex replacement is safe if done carefully.

            # Simple replace
            def replace_callback(match):
                redacted_items.append({
                    "type": pii_type,
                    "masked_text": f"<{pii_type.upper()}>"
                })
                return f"<{pii_type.upper()}>"

            sanitized_text = re.sub(pattern, replace_callback, sanitized_text)

        # 2. LLM Sanitization (Optional - Strategy 132 Advanced)
        if use_llm and self.gemini_client:
            try:
                prompt = f"""
                Analyze the following text for Personally Identifiable Information (PII)
                or sensitive secrets that standard regex might miss (like names in context,
                addresses, specific medical info).

                If found, replace them with <REDACTED:TYPE>.
                Return the result as JSON:
                {{
                    "sanitized_text": "text with redactions",
                    "found_pii": [
                        {{"type": "NAME", "text": "John Doe"}}
                    ]
                }}

                Text to sanitize:
                {sanitized_text}
                """

                response = await self.gemini_client.generate_text(
                    prompt=prompt,
                    task_type="generation", # or extraction
                    model_id="gemini-2.0-flash", # Fast model
                    temperature=0.0
                )

                # Parse JSON safely
                content = response.get("content", "").strip()
                # Extract JSON block if needed
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[0].strip() # Handle raw block

                try:
                    data = json.loads(content)
                    if "sanitized_text" in data:
                        sanitized_text = data["sanitized_text"]
                    if "found_pii" in data and isinstance(data["found_pii"], list):
                        for item in data["found_pii"]:
                             redacted_items.append({
                                 "type": item.get("type", "UNKNOWN"),
                                 "masked_text": f"<{item.get('type', 'UNKNOWN')}>"
                             })
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM sanitization response")

            except Exception as e:
                logger.warning(f"LLM sanitization failed: {e}")

        return SanitizationResult(
            original_text=text,
            sanitized_text=sanitized_text,
            redacted_items=redacted_items,
            was_sanitized=len(redacted_items) > 0
        )

    async def detect_bias(self, text: str) -> BiasResult:
        """Detect bias in text (Strategy 152).

        Args:
            text: Text to analyze

        Returns:
            BiasResult object
        """
        try:
            prompt = f"""
            Analyze the following text for various types of bias (gender, racial, political,
            religious, socioeconomic, etc.).

            Provide a bias score from 0.0 (Neutral) to 1.0 (Highly Biased).
            Identify categories of bias present.
            Provide a brief analysis.

            Return ONLY JSON:
            {{
                "score": 0.0,
                "categories": ["political", "gender"],
                "analysis": "The text assumes..."
            }}

            Text:
            {text}
            """

            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="classification",
                model_id="gemini-2.0-flash", # Fast model is usually sufficient
                temperature=0.0
            )

            content = response.get("content", "").strip()
            # Cleanup markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[0].strip()

            data = json.loads(content)

            score = float(data.get("score", 0.0))
            categories = data.get("categories", [])
            analysis = data.get("analysis", "")

            return BiasResult(
                bias_score=score,
                categories=categories,
                analysis=analysis,
                is_biased=score > 0.3 # Threshold
            )

        except Exception as e:
            logger.error(f"Bias detection failed: {e}")
            return BiasResult(
                bias_score=0.0,
                categories=[],
                analysis="Error during detection",
                is_biased=False
            )
