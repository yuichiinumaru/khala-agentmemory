"""Domain services for context management."""

import logging
from typing import Optional
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class TopicDetector:
    """Service for detecting topic changes in conversation."""
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client
        
    async def detect_change(self, current_text: str, previous_text: str) -> bool:
        """
        Detect if the topic has changed between previous and current text.
        Returns True if topic changed, False otherwise.
        """
        if not previous_text or not current_text:
            return False
            
        # Simple heuristic: if texts are very short, assume no change or hard to tell
        if len(current_text.split()) < 3:
            return False
            
        try:
            prompt = f"""
            Analyze if the topic has changed between these two messages.
            
            Previous: "{previous_text}"
            Current: "{current_text}"
            
            Has the topic changed? Answer with just YES or NO.
            """
            
            response = await self.gemini_client.generate_text(
                prompt,
                model_id="gemini-2.0-flash", # Use fast model
                temperature=0.0
            )
            
            return "YES" in response["content"].upper()
            
        except Exception as e:
            logger.error(f"Error detecting topic change: {e}")
            # Fallback to simple keyword overlap? 
            # For now, return False on error to be safe (don't disrupt flow)
            return False
