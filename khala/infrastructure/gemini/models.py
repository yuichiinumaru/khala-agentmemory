"""Gemini model configuration and management.

This module defines the model tiers and configurations for the LLM cascading system.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """LLM model tiers for cascading optimization."""
    
    FAST = "fast"        # gemini-2.0-flash
    MEDIUM = "medium"    # gemini-2.5-flash
    SMART = "smart"     # gemini-2.5-pro


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
    
    # Predefined model configurations following KHALA documentation
    MODELS: Dict[str, GeminiModel] = {
        # Fast tier - gemini-2.0-flash
        "gemini-2.0-flash": GeminiModel(
            name="Gemini 2.0 Flash",
            tier=ModelTier.FAST,
            model_id="gemini-2.0-flash",
            cost_per_million_tokens=1.0,  # Estimated lower cost
            max_tokens=1048576,
            temperature=0.1,
            top_p=0.9,
            top_k=64
        ),
        
        # Medium tier - gemini-2.5-flash
        "gemini-2.5-flash": GeminiModel(
            name="Gemini 2.5 Flash",
            tier=ModelTier.MEDIUM,
            model_id="gemini-2.5-flash",
            cost_per_million_tokens=2.0,  # Estimated
            max_tokens=1048576,
            temperature=0.3,
            top_p=0.8,
            top_k=40
        ),
        
        # Smart tier - gemini-2.5-pro
        "gemini-2.5-pro": GeminiModel(
            name="Gemini 2.5 Pro",
            tier=ModelTier.SMART,
            model_id="gemini-2.5-pro",
            cost_per_million_tokens=10.0,  # Estimated
            max_tokens=2097152,
            temperature=0.7,
            top_p=0.8,
            top_k=40
        ),
        
        # Embedding model
        "gemini-embedding-001": GeminiModel(
            name="Gemini Embedding 001",
            tier=ModelTier.FAST,  # Treat as fast tier for cost purposes
            model_id="gemini-embedding-001",
            cost_per_million_tokens=2.0,  # $0.002/1M tokens (estimate)
            max_tokens=2048,  # Embeddings don't need large token limits
            supports_embeddings=True,
            embedding_dimensions=768,
            temperature=0.0,  # Embeddings are deterministic
            top_p=0.0,
            top_k=1
        ),

        # Secondary Embedding model (Strategy 89: Vector Ensemble)
        "text-embedding-004": GeminiModel(
            name="Text Embedding 004",
            tier=ModelTier.FAST,
            model_id="text-embedding-004",
            cost_per_million_tokens=2.0,
            max_tokens=2048,
            supports_embeddings=True,
            embedding_dimensions=768,
            temperature=0.0,
            top_p=0.0,
            top_k=1
        ),
    }
    
    @classmethod
    def get_model(cls, model_id: str) -> GeminiModel:
        """Get model configuration by model ID."""
        if model_id not in cls.MODELS:
            raise ValueError(f"Unknown model: {model_id}")
        return cls.MODELS[model_id]
    
    @classmethod
    def get_tier_models(cls, tier: ModelTier) -> List[GeminiModel]:
        """Get all models in a specific tier."""
        return [model for model in cls.MODELS.values() if model.tier == tier]
    
    @classmethod
    def get_embedding_model(cls) -> GeminiModel:
        """Get the default embedding model."""
        for model in cls.MODELS.values():
            if model.supports_embeddings:
                return model
        raise ValueError("No embedding model found")
    
    @classmethod
    def get_cost_optimal_model(
        cls, 
        complexity: float, 
        required_quality: float = 0.8
    ) -> GeminiModel:
        """Get cost-optimal model based on complexity and quality requirements.
        
        Args:
            complexity: Task complexity score (0.0-1.0)
            required_quality: Minimum quality threshold (0.0-1.0)
            
        Returns:
            Selected model configuration
        """
        # Define tier thresholds
        if complexity <= 0.3 and required_quality <= 0.6:
            # Simple task, low quality requirement - use fast
            tier = ModelTier.FAST
        elif complexity <= 0.7 and required_quality <= 0.8:
            # Moderate task and quality - use medium
            tier = ModelTier.MEDIUM  
        else:
            # Complex task or high quality requirement - use smart
            tier = ModelTier.SMART
        
        models = cls.get_tier_models(tier)
        if not models:
            raise ValueError(f"No models available for tier: {tier}")
        
        # Return the lowest cost model in the tier
        return min(models, key=lambda m: m.cost_per_million_tokens)


class ModelMetrics:
    """Model performance metrics collection."""
    
    def __init__(self):
        """Initialize metrics tracking."""
        self.model_stats: Dict[str, Dict[str, str]] = {}
    
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
            self.model_stats[model_id] = {
                "usage_count": "0",
                "total_input_tokens": "0", 
                "total_output_tokens": "0",
                "total_response_time": "0.0",
                "success_count": "0",
                "failure_count": "0"
            }
        
        stats = self.model_stats[model_id]
        stats["usage_count"] = str(int(stats["usage_count"]) + 1)
        stats["total_input_tokens"] = str(int(stats["total_input_tokens"]) + input_tokens)
        stats["total_output_tokens"] = str(int(stats["total_output_tokens"]) + output_tokens)
        stats["total_response_time"] = f"{float(stats['total_response_time']) + response_time_ms:.2f}"
        
        if success:
            stats["success_count"] = str(int(stats["success_count"]) + 1)
        else:
            stats["failure_count"] = str(int(stats["failure_count"]) + 1)
    
    def get_model_stats(self, model_id: str) -> Dict[str, Any]:
        """Get aggregated statistics for a model."""
        if model_id not in self.model_stats:
            return {}
        
        stats = self.model_stats[model_id]
        usage_count = int(stats["usage_count"])
        
        if usage_count == 0:
            return {
                "usage_count": 0,
                "avg_response_time_ms": 0.0,
                "success_rate": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0
            }
        
        success_count = int(stats["success_count"])
        failure_count = int(stats["failure_count"])
        
        return {
            "usage_count": usage_count,
            "avg_response_time_ms": float(stats["total_response_time"]) / usage_count,
            "success_rate": success_count / usage_count,
            "total_input_tokens": int(stats["total_input_tokens"]),
            "total_output_tokens": int(stats["total_output_tokens"]),
            "total_tokens": int(stats["total_input_tokens"]) + int(stats["total_output_tokens"])
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all used models."""
        return {
            model_id: self.get_model_stats(model_id)
            for model_id in self.model_stats.keys()
        }
