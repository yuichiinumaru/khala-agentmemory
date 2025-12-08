"""Gemini API client with LLM cascading optimization.

This module provides intelligent model routing, cost optimization,
and connection management for the Google Gemini API.
"""

import asyncio
import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import logging

import cachetools

try:
    import google.generativeai as genai
    from google.api_core import exceptions as gcp_exceptions
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError as e:
    raise ImportError(
        "Google Generative AI is required. Install with: pip install google-generativeai"
    ) from e

from .models import GeminiModel, ModelTier, ModelRegistry
from .cost_tracker import CostTracker
from khala.application.utils import parse_json_safely

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini API client with intelligent cascading and cost optimization."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
        enable_cascading: bool = True,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 300,  # 5 minutes
        max_retries: int = 3,
        timeout_seconds: int = 30
    ):
        """Initialize Gemini client."""
        self.api_key = api_key or self._get_api_key_from_env()
        self.cost_tracker = cost_tracker or CostTracker()
        self.enable_cascading = enable_cascading
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        
        # Response cache
        self._response_cache = cachetools.TTLCache(maxsize=1000, ttl=cache_ttl_seconds)
        self._cache_lock = asyncio.Lock()
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Model configuration
        self._models: Dict[str, genai.GenerativeModel] = {}
        self._model_lock = asyncio.Lock() # Lock for model initialization
        
        # Metrics
        self._prompt_classification_cache = cachetools.TTLCache(maxsize=10000, ttl=3600)
        self._complexity_cache = cachetools.TTLCache(maxsize=10000, ttl=3600)
    
        # Initialize models if cascading is enabled
        if self.enable_cascading:
            self._setup_models()
    
    def get_api_key(self) -> str:
        return self.api_key
    
    def _get_api_key_from_env(self) -> str:
        import os
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("CRITICAL: GOOGLE_API_KEY environment variable is not set.")
        return api_key
    
    def _setup_models(self) -> None:
        """Initialize all configured models."""
        try:
            genai.configure(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to configure Gemini: {e}")
            raise
    
    async def classify_task_complexity(self, prompt: str) -> float:
        """Classify task complexity score."""
        cache_key = hash(prompt)
        if cache_key in self._complexity_cache:
            return self._complexity_cache[cache_key]
        
        complexity = 0.0
        prompt_lower = prompt.lower()
        
        # Improved heuristics
        factors = {
            "length": min(1.0, len(prompt) / 1000),
            "questions": min(1.0, prompt.count("?") / 5),
            "code": min(1.0, prompt.count("```") * 0.2),
            "json": min(1.0, prompt.count(":") / 20),
            "steps": min(1.0, prompt_lower.count("step") / 10),
            "analysis": min(1.0, prompt_lower.count("analyze") / 5),
        }
        
        weights = {
            "length": 0.2, "questions": 0.2, "code": 0.3,
            "json": 0.2, "steps": 0.2, "analysis": 0.2
        }
        
        complexity = sum(factors[factor] * weights[factor] for factor in factors)
        result = min(1.0, complexity)
        
        self._complexity_cache[cache_key] = result
        return result
    
    async def select_model(self, prompt: str, task_type: str = "generation") -> GeminiModel:
        """Select the optimal model."""
        if not self.enable_cascading:
            return ModelRegistry.get_model("gemini-2.5-pro")
        
        quality_requirements = {
            "embedding": 0.5, "classification": 0.7,
            "extraction": 0.8, "generation": 0.8
        }.get(task_type, 0.8)
        
        try:
            complexity_score = await self.classify_task_complexity(prompt)
            return ModelRegistry.get_cost_optimal_model(complexity_score, quality_requirements)
        except Exception as e:
            logger.warning(f"Error selecting optimal model, using default: {e}")
            return ModelRegistry.get_model("gemini-2.5-pro")

    async def _get_or_create_model(self, model_id: str, config: Dict[str, Any]) -> genai.GenerativeModel:
        """Thread-safe model initialization."""
        async with self._model_lock:
            if model_id not in self._models:
                try:
                    # Check if it's an embedding model
                    model_config = ModelRegistry.MODELS.get(model_id)
                    if model_config and model_config.supports_embeddings:
                         self._models[model_id] = genai.GenerativeModel(model_name=model_id)
                    else:
                        self._models[model_id] = genai.GenerativeModel(
                            model_name=model_id,
                            generation_config=genai.types.GenerationConfig(
                                temperature=config.get("temperature"),
                                max_output_tokens=config.get("max_output_tokens")
                            ),
                            safety_settings={
                                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                            }
                        )
                except Exception as e:
                    logger.error(f"Failed to initialize model {model_id}: {e}")
                    raise
            return self._models[model_id]
    
    async def generate_text(
        self,
        prompt: str,
        images: Optional[List[Any]] = None,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_type: str = "generation",
        use_cascading: bool = True
    ) -> Dict[str, Any]:
        """Generate text using the optimal or specified model."""
        start_time = time.time()
        
        # Select model
        if images:
            if not model_id:
                model = await self.select_model(prompt, task_type)
            else:
                model = ModelRegistry.get_model(model_id)
                use_cascading = False
        elif model_id:
            model = ModelRegistry.get_model(model_id)
            use_cascading = False
        else:
            model = await self.select_model(prompt, task_type)
        
        # Check cache if enabled
        if self.enable_caching and not images:
            cache_key = self._get_cache_key(prompt, model_id=model.model_id)
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                self._cache_hits += 1
                return cached_response
            self._cache_misses += 1
        
        # Configure generation parameters
        config = {
            "temperature": temperature or model.temperature,
            "max_output_tokens": max_tokens or model.max_tokens,
        }
        
        # Initialize model thread-safely
        model_instance = await self._get_or_create_model(model.model_id, config)
        
        # Prepare content
        content_parts = [prompt]
        if images:
            content_parts.extend(images)

        # Execute generation with retries
        for attempt in range(self.max_retries + 1):
            try:
                response = await asyncio.to_thread(
                    model_instance.generate_content,
                    content_parts,
                    stream=False,
                    request_options={"timeout": self.timeout_seconds}
                )
                break
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(2 ** attempt)
        
        # Calculate tokens (approximate)
        input_tokens = len(prompt.split()) * 1.3
        output_tokens = len(response.text.split()) * 1.3
        response_time_ms = (time.time() - start_time) * 1000
        
        # Record cost
        cost_record = self.cost_tracker.record_call(
            model=model,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            response_time_ms=response_time_ms,
            task_type=task_type,
            success=True
        )
        
        # Cache response
        if self.enable_caching:
            cache_key = self._get_cache_key(prompt, model_id=model.model_id)
            cached_data = {
                "content": response.text,
                "model_id": model.model_id,
                "model_tier": model.tier.value,
                "cache_hit": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "response_time_ms": response_time_ms,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "cost_usd": str(cost_record.cost_usd)
            }
            await self._cache_response(cache_key, cached_data)
        
        return {
            "content": response.text,
            "model_id": model.model_id,
            "model_tier": model.tier.value,
            "cache_hit": False,
            "response_time_ms": response_time_ms,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "cost_usd": float(cost_record.cost_usd),
            "model_name": model.name
        }

    async def generate_embeddings(self, texts: List[str], model_id: Optional[str] = None) -> List[List[float]]:
        """Generate embeddings for list of texts.

        Raises:
            Exception: If any batch fails, the entire operation fails to preserve data alignment.
        """
        embedding_model = ModelRegistry.get_embedding_model()
        
        embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                # Use to_thread for blocking IO
                result = await asyncio.to_thread(
                    genai.embed_content,
                    model=embedding_model.model_id,
                    content=batch,
                    task_type="retrieval_document",
                    output_dimensionality=embedding_model.embedding_dimensions,
                    request_options={"timeout": self.timeout_seconds}
                )
                embeddings.extend(result['embedding'])
            except Exception as e:
                logger.error(f"Failed to embed batch {i}: {e}")
                # Fail Loudly: Data alignment is critical for embeddings
                raise RuntimeError(f"Embedding batch failed at index {i}: {e}") from e
        
        return embeddings
    
    def _get_cache_key(self, content: str, prefix: str = "", model_id: str = "") -> str:
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        components = []
        if prefix: components.append(prefix)
        if model_id: components.append(model_id)
        components.append(content_hash)
        return "_".join(components)
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        if not self.enable_caching: return None
        async with self._cache_lock:
            cached_record = self._response_cache.get(cache_key)
            if cached_record:
                cached_record["cache_hit"] = True
                return cached_record
            return None

    async def _cache_response(self, cache_key: str, data: Dict[str, Any]) -> None:
        async with self._cache_lock:
            self._response_cache[cache_key] = data
    
    def get_cost_tracker(self) -> CostTracker:
        return self.cost_tracker
    
    def clear_cache(self) -> None:
        self._response_cache.clear()
        self._prompt_classification_cache.clear()
        self._complexity_cache.clear()

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment with robust JSON parsing."""
        prompt = f"""
        Analyze the sentiment of the following text.
        Return a valid JSON object with:
        - score: float between -1.0 (negative) and 1.0 (positive)
        - label: string (positive, negative, neutral, mixed)
        - emotions: dictionary of emotion names and their intensities (0.0-1.0)

        Text: "{text}"
        """
        response = await self.generate_text(
            prompt=prompt,
            task_type="classification",
            model_id="gemini-2.0-flash",
            temperature=0.0
        )
        return parse_json_safely(response.get("content", ""))

    async def translate_text(self, text: str, target_language: str) -> str:
        """Translate text."""
        prompt = f"Translate the following text to {target_language}:\n\n{text}"
        response = await self.generate_text(
            prompt=prompt, task_type="generation", model_id="gemini-2.0-flash"
        )
        return response.get("content", "").strip()

    # --- Mixture of Thought (MoT) ---
    async def generate_mixture_of_thought(
        self,
        prompt: str,
        num_perspectives: int = 3,
        model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate multiple perspectives and synthesize them."""
        start_time = time.time()
        
        tasks = []
        for i in range(num_perspectives):
            perspective_temp = 0.7 + (i * 0.1)
            perspective_prompt = f"Perspective {i+1}: Analyze the following from a unique angle: {prompt}"
            tasks.append(self.generate_text(
                prompt=perspective_prompt,
                model_id=model_id,
                temperature=min(1.0, perspective_temp),
                use_cascading=True
            ))
        
        perspective_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_perspectives = []
        for res in perspective_results:
            if isinstance(res, dict) and 'content' in res:
                valid_perspectives.append(res['content'])
            elif isinstance(res, Exception):
                logger.warning(f"Perspective generation failed: {res}")
        
        if not valid_perspectives:
            raise ValueError("Failed to generate any valid perspectives")
            
        synthesis_prompt = f"""
        Analyze the following perspectives on the topic:
        {prompt}
        
        Perspectives:
        {json.dumps(valid_perspectives, indent=2)}
        
        Synthesize a final comprehensive answer.
        """
        
        final_response = await self.generate_text(
            prompt=synthesis_prompt,
            model_id="gemini-2.5-pro",
            temperature=0.2,
            use_cascading=False
        )
        
        return {
            "final_response": final_response,
            "perspectives": valid_perspectives,
            "meta": {
                "num_perspectives": len(valid_perspectives),
                "total_time_ms": (time.time() - start_time) * 1000
            }
        }
