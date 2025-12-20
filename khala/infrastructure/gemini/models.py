"""Gemini model configuration and management.

This module defines the model tiers and configurations for the LLM cascading system.
It enforces type safety and deterministic model selection.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# --- Model Constants ---
GEMINI_FLASH_2_0 = "gemini-2.0-flash"
GEMINI_FLASH_3_PREVIEW = "gemini-3-flash-preview"
GEMINI_PRO_3_PREVIEW = "gemini-3-pro-preview"
GEMINI_EMBEDDING_001 = "models/gemini-embedding-001"
GEMINI_MULTIMODAL_EMBEDDING = "models/multimodal-embedding-001"

# Legacy constants (kept for backward compatibility but mapped to new models if appropriate or kept as is)
GEMINI_FLASH_2_5 = "gemini-2.5-flash"
GEMINI_PRO_2_5 = "gemini-2.5-pro"

# Aliases for easier usage
GEMINI_FAST = GEMINI_FLASH_3_PREVIEW
GEMINI_BALANCED = GEMINI_FLASH_3_PREVIEW
GEMINI_REASONING = GEMINI_PRO_3_PREVIEW
GEMINI_EMBEDDING = GEMINI_EMBEDDING_001


class ModelTier(Enum):
    """LLM model tiers for cascading optimization."""
    
    FAST = "fast"        # gemini-3-flash-preview
    MEDIUM = "medium"    # gemini-3-flash-preview
    SMART = "smart"      # gemini-3-pro-preview


@dataclass
class GeminiModel:
    """Immutable configuration for a specific Gemini model."""
    
    name: str
    tier: ModelTier
    model_id: str
    cost_per_million_tokens: float
    max_tokens: int
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 40
    supports_embeddings: bool = False
    embedding_dimensions: Optional[int] = None
    thinking_mode: bool = False # Indicates if model supports/requires thinking configuration
    
    def __post_init__(self) -> None:
        """Validate model configuration."""
        if not self.name.strip():
            raise ValueError("Model name cannot be empty")
        
        if not self.model_id.strip():
            raise ValueError("Model ID cannot be empty")
        
        if self.cost_per_million_tokens < 0:
            raise ValueError("Cost must be non-negative")
        
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("Temperature must be in [0.0, 2.0]")
            
        if not (0.0 <= self.top_p <= 1.0):
            raise ValueError("Top P must be in [0.0, 1.0]")
            
        if self.top_k <= 0:
            raise ValueError("Top K must be positive")


class ModelRegistry:
    """Registry of available LLM models with their configurations."""
    
    # Predefined model configurations
    MODELS: Dict[str, GeminiModel] = {
        # Fast tier (Gemini 3 Flash Preview)
        GEMINI_FLASH_3_PREVIEW: GeminiModel(
            name="Gemini 3.0 Flash Preview",
            tier=ModelTier.FAST,
            model_id=GEMINI_FLASH_3_PREVIEW,
            cost_per_million_tokens=1.0, # Placeholder cost
            max_tokens=1048576,
            temperature=0.3,
            top_p=0.9,
            top_k=64
        ),

        # Legacy/Alternative Fast (Gemini 2.0 Flash)
        GEMINI_FLASH_2_0: GeminiModel(
            name="Gemini 2.0 Flash",
            tier=ModelTier.FAST,
            model_id=GEMINI_FLASH_2_0,
            cost_per_million_tokens=1.0,
            max_tokens=1048576,
            temperature=0.1,
            top_p=0.9,
            top_k=64
        ),
        
        # Smart tier (Gemini 3 Pro Preview)
        GEMINI_PRO_3_PREVIEW: GeminiModel(
            name="Gemini 3.0 Pro Preview",
            tier=ModelTier.SMART,
            model_id=GEMINI_PRO_3_PREVIEW,
            cost_per_million_tokens=10.0, # Placeholder cost
            max_tokens=2097152,
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            thinking_mode=True # thinking=high
        ),
        
        # Legacy Smart (Gemini 2.5 Pro) - Kept for fallback if needed, but discouraged
        GEMINI_PRO_2_5: GeminiModel(
            name="Gemini 2.5 Pro",
            tier=ModelTier.SMART,
            model_id=GEMINI_PRO_2_5,
            cost_per_million_tokens=10.0,
            max_tokens=2097152,
            temperature=0.7,
            top_p=0.8,
            top_k=40
        ),
        
        # Legacy Medium (Gemini 2.5 Flash)
        GEMINI_FLASH_2_5: GeminiModel(
            name="Gemini 2.5 Flash",
            tier=ModelTier.MEDIUM,
            model_id=GEMINI_FLASH_2_5,
            cost_per_million_tokens=2.0,
            max_tokens=1048576,
            temperature=0.3,
            top_p=0.8,
            top_k=40
        ),

        # Embedding model (Standard)
        GEMINI_EMBEDDING_001: GeminiModel(
            name="Gemini Embedding 001",
            tier=ModelTier.FAST,
            model_id=GEMINI_EMBEDDING_001,
            cost_per_million_tokens=2.0,
            max_tokens=2048,
            supports_embeddings=True,
            embedding_dimensions=768,
            temperature=0.0,
            top_p=0.0,
            top_k=1
        ),

        # Multimodal Embedding model (High Dim)
        GEMINI_MULTIMODAL_EMBEDDING: GeminiModel(
            name="Gemini Multimodal Embedding 001",
            tier=ModelTier.FAST,
            model_id=GEMINI_MULTIMODAL_EMBEDDING,
            cost_per_million_tokens=5.0,
            max_tokens=2048,
            supports_embeddings=True,
            embedding_dimensions=1408,
            temperature=0.0,
            top_p=0.0,
            top_k=1
        ),
    }
    
    @classmethod
    def get_model(cls, model_id: str) -> GeminiModel:
        """Get model configuration by model ID."""
        if model_id not in cls.MODELS:
            # Check if it maps to a new model
            if model_id == "gemini-2.5-pro":
                 return cls.MODELS[GEMINI_PRO_3_PREVIEW]
            if model_id == "gemini-2.5-flash":
                 return cls.MODELS[GEMINI_FLASH_3_PREVIEW]

            # If specifically requested legacy model is in MODELS, return it
            # But usually we want to intercept hardcoded strings.

            raise ValueError(f"Unknown model: {model_id}")
        return cls.MODELS[model_id]
    
    @classmethod
    def get_tier_models(cls, tier: ModelTier) -> List[GeminiModel]:
        """Get all models in a specific tier."""
        return [model for model in cls.MODELS.values() if model.tier == tier]
    
    @classmethod
    def get_embedding_model(cls, dimensions: int = 768) -> GeminiModel:
        """Get an embedding model with specific dimensions."""
        for model in cls.MODELS.values():
            if model.supports_embeddings and model.embedding_dimensions == dimensions:
                return model

        # Fallback to standard
        return cls.MODELS.get("gemini-embedding-001")
    
    @classmethod
    def get_cost_optimal_model(
        cls, 
        complexity: float, 
        required_quality: float = 0.8
    ) -> GeminiModel:
        """Get cost-optimal model based on complexity and quality requirements."""
        # Adjusted thresholds to favor FAST tier for simple tasks
        if complexity <= 0.4 and required_quality <= 0.7:
            tier = ModelTier.FAST
        elif complexity <= 0.8 and required_quality <= 0.85:
            tier = ModelTier.MEDIUM  
        else:
            tier = ModelTier.SMART
        
        models = cls.get_tier_models(tier)
        if not models:
            # Fallback to Smart if lower tier unavailable
            return cls.get_model(GEMINI_PRO_3_PREVIEW)
        
        # Prefer 3.0 models if available
        preferred = [m for m in models if "3" in m.model_id]
        if preferred:
             return min(preferred, key=lambda m: m.cost_per_million_tokens)

        return min(models, key=lambda m: m.cost_per_million_tokens)


@dataclass
class UsageStats:
    """Type-safe usage statistics."""
    usage_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_response_time: float = 0.0
    success_count: int = 0
    failure_count: int = 0

class ModelMetrics:
    """Model performance metrics collection."""
    
    def __init__(self):
        """Initialize metrics tracking."""
        self.model_stats: Dict[str, UsageStats] = {}
    
    def record_usage(
        self, 
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        response_time_ms: float,
        success: bool = True
    ) -> None:
        """Record model usage for performance tracking."""
        if model_id not in self.model_stats:
            self.model_stats[model_id] = UsageStats()
        
        stats = self.model_stats[model_id]
        stats.usage_count += 1
        stats.total_input_tokens += input_tokens
        stats.total_output_tokens += output_tokens
        stats.total_response_time += response_time_ms
        
        if success:
            stats.success_count += 1
        else:
            stats.failure_count += 1
    
    def get_model_stats(self, model_id: str) -> Dict[str, Any]:
        """Get aggregated statistics for a model."""
        if model_id not in self.model_stats:
            return {}
        
        stats = self.model_stats[model_id]
        
        if stats.usage_count == 0:
            return {
                "usage_count": 0,
                "avg_response_time_ms": 0.0,
                "success_rate": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0
            }
        
        return {
            "usage_count": stats.usage_count,
            "avg_response_time_ms": stats.total_response_time / stats.usage_count,
            "success_rate": stats.success_count / stats.usage_count,
            "total_input_tokens": stats.total_input_tokens,
            "total_output_tokens": stats.total_output_tokens,
            "total_tokens": stats.total_input_tokens + stats.total_output_tokens
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all used models."""
        return {
            model_id: self.get_model_stats(model_id)
            for model_id in self.model_stats.keys()
        }
