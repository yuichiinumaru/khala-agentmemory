"""Gemini infrastructure components.

This module contains the integration with Google Gemini API
for LLM services and embedding generation.
"""

try:
    from .client import GeminiClient
    from .models import GeminiModel, ModelTier
    from .cost_tracker import CostTracker
    gemini_available = True
except ImportError as e:
    # Optional dependencies may not be available in test environment
    gemini_available = False
    GeminiClient = None
    GeminiModel = None
    ModelTier = None
    CostTracker = None

__all__ = ["GeminiClient", "GeminiModel", "ModelTier", "CostTracker"]
