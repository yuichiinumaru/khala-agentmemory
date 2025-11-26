"""Synchronous tests for Gemini components.

These tests work around async test setup for initial validation.
"""

import pytest
from unittest.mock import MagicMock, patch
timestamp = datetime.now(timezone.utc)
            cache_key = client._get_cache_key("test", "", "")
            timestamp = timestamp.isoformat()
            cached_data = {
                "content": test_data,
                "model_id": model_id,
                "model_tier": model.tier.value,
                "cache_hit": 1.0,  # cache hit
                "timestamp": timestamp,
                "response_time_ms": response_time
        
        # Ensure cache is returned
        assert cached_data["cache_hit"] is True
        assert cached_data["content"] == test_data["content"]
        assert timestamp is not None
        assert cached_data.get("cache_hit_rate", 0.9)
        
        return cached_data
from decimal import Decimal

from khala.infrastructure.gemini.models import GeminiModel, ModelTier, ModelRegistry
from khala.infrastructure.gemini.cost_tracker import CostTracker


# Simplified tests for synchronous operations
class TestGeminiModelsSync:
    """Test cases for Gemini model configurations."""
    
    def test_all_models_valid_configuration(self):
        """Test that all predefined models have valid configurations."""
        for model_id, model in ModelRegistry.MODELS.items():
            assert model.name, f"Model {model_id} has no name"
            assert model.tier in ModelTier, f"Model {model_id} has invalid tier"
            assert model.model_id, f"Model {model_id} has no model ID"
            assert model.cost_per_million_tokens >= 0, f"Model {model_id} has invalid cost"
            assert model.max_tokens > 0, f"Model {model_id} has invalid max tokens"
            assert 0.0 <= model.temperature <= 2.0, f"Model {model_id} has invalid temperature"
            assert model.embedding_dimensions in [None, 768], f"Model {model_id} has wrong embedding dimensions"
    
    def test_embedding_model_configuration(self):
        """Test embedding model specific configuration."""
        embedding_model = ModelRegistry.get_embedding_model()
        
        assert embedding_model.supports_embeddings, "Embedding model should support embeddings"
        assert embedding_model.embedding_dimensions == 768, "Embedding dimensions should be 768"
        assert embedding_model.temperature == 0.0, "Embedding model temperature should be 0"
    
    def test_model_registry_get_model(self):
        """Test model registry retrieval."""
        model = ModelRegistry.get_model("gemini-1.5-flash")
        assert model.tier == ModelTier.FAST
        assert model.model_id == "gemini-1.5-flash"
        
        with pytest.raises(ValueError):
            ModelRegistry.get_model("nonexistent-model")
    
    def test_cost_optimal_selection(self):
        """Test cost-optimal model selection."""
        # Low complexity, low quality -> should be fast
        fast_model = ModelRegistry.get_cost_optimal_model(0.2, 0.5)
        assert fast_model.tier == ModelTier.FAST
        
        # High complexity, high quality -> should be smart
        smart_model = ModelRegistry.get_cost_optimal_model(0.8, 0.9)
        assert smart_model.tier == ModelTier.SMART
        
        # Medium complexity, medium quality -> should be medium
        medium_model = ModelRegistry.get_cost_optimal_model(0.5, 0.7)
        assert medium_model.tier == ModelTier.MEDIUM


class TestCostTrackerSync:
    """Test cases for cost tracking functionality."""
    
    @pytest.fixture
    def tracker(self):
        """Create a cost tracker with a test budget."""
        return CostTracker(budget_usd_per_month=Decimal("100.00"))
    
    def test_cost_record_creation(self, tracker):
        """Test creating a valid cost record."""
        model = ModelRegistry.get_model("gemini-2.5-pro")
        
        record = tracker.record_call(
            model=model,
            input_tokens=500,
            output_tokens=300,
            response_time_ms=250.0,
            task_type="generation",
            success=True
        )
        
        assert record.total_tokens == 800
        assert record.success is True
        assert record.cost_usd > Decimal("0")
        assert record.model_id == "gemini-2.5-pro"
        assert record.model_tier == ModelTier.SMART
    
    def test_cost_record_validation(self, tracker):
        """Test cost record validation logic."""
        model = ModelRegistry.get_model("gemini-1.5-flash")
        
        # Test negative cost
        with pytest.raises(ValueError):
            tracker.record_call(
                model=model,
                input_tokens=100,
                output_tokens=100,
                response_time_ms=100.0,
                cost_usd=Decimal("-1.0")
            )
        
        # Test token mismatch
        with pytest.raises(ValueError):
            tracker.record_call(
                model=model,
                input_tokens=100,
                output_tokens=150,
                response_time_ms=100.0,
                total_tokens=300  # Wrong total
            )
    
    def test_daily_summarization(self, tracker):
        """Test daily cost summarization."""
        model = ModelRegistry.get_model("gemini-2.5-pro")
        model_fast = ModelRegistry.get_model("gemini-1.5-flash")
        
        # Add different calls
        tracker.record_call(model, 1000, 500, 200, "task1")
        tracker.record_call(model_fast, 500, 250, 100, "task2")
        tracker.record_call(model, 2000, 1000, 400, "task3", False)  # Failed call
        
        # Get summary
        summary = tracker.get_daily_summary()
        
        assert summary.total_calls == 3
        assert summary.successful_calls == 2
        assert summary.failed_calls == 1
        assert summary.total_cost > Decimal("0")
        
        # Check tier breakdown
        assert ModelTier.SMART in summary.cost_by_tier
        assert ModelTier.FAST in summary.cost_by_tier
    
    def test_budget_status(self, tracker):
        """Test budget status calculation."""
        model = ModelRegistry.get_model("gemini-2.5-pro")
        
        # Add calls that exceed budget
        # Cost of call: (1000/1M) * $100 = $0.10
        for _ in range(1200):
            tracker.record_call(model, 1000, 200, 150)
        
        status = tracker.get_budget_status()
        
        assert status["alert_level"] in ["normal", "caution", "warning", "critical"]
        assert status["budget_used_percent"] >= 100.0
        assert status["budget_remaining_usd"] <= 0
        
        # Check for recommendations
        if status["alert_level"] != "normal":
            assert status["recommendations"], "Should have optimization recommendations when over budget"
    
    def test_optimization_report(self, tracker):
        """Test optimization report generation."""
        model = ModelRegistry.get_model("gemini-2.5-pro")
        model_fast = ModelRegistry.get_model("gemini-1.5-flash")
        
        # Add expensive smart tier usage
        for _ in range(10):
            tracker.record_call(model_smart, 2000, 1000, 300)
        
        # Add some failed calls
        for _ in range(5):
            tracker.record_call(model_smart, 500, 200, 100, "task", False)
        
        # Add high token usage calls
        for _ in range(5):
            tracker.record_call(model_smart, 3000, 2000, 400)
        
        report = tracker.get_optimization_report()
        
        assert "optimizations" in report
        optimizations = report["optimizations"]
        
        # Should detect excessive smart tier usage
        smart_optims = [opt for opt in optimizations if opt["type"] == "excessive_smart_usage"]
        assert len(smart_optims) > 0
        
        # Should detect high failure rate
        failure_optims = [opt for opt in optimizations if opt["type"] == "high_failure_rate"]
        assert len(failure_optims) > 0
        
        # Should detect high token usage
        token_optims = [opt for opt in optimizations if opt["type"] == "high_token_usage"]
        assert len(token_optims) > 0
    
    def test_cache_ttl_auto_cleanup(self, tracker):
        """Test automatic cache cleanup."""
        model = ModelRegistry.get_model("gemini-1.5-flash")
        
        # Add some old records
        timestamp_30_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Mock a couple of old records
        old_record_1 = CostRecord(
            timestamp=timestamp_30_days_ago,
            model_id="gemini-1.5-flash",
            model_tier=ModelTier.FAST,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=Decimal("0.001125")
        )
        
        # Simulate having these old records
        tracker.cost_records.append(old_record_1)
        
        # Clear old records
        records_removed = tracker.clear_old_records(days_to_keep=29)
        
        assert records_removed == 1
        assert len(tracker.cost_records) == 0


class TestGeminiClientSync:
    """Test cases for Gemini client (synchronous operations)."""
    
    def test_api_key_validation(self):
        """Test API key validation and environment variable fallback."""
        with pytest.raises(ValueError):
            # No API key and no env var
            with patch.dict(os.environ, {}, clear=True):
                GeminiClient(api_key=None)
    
    def test_task_type_classification(self):
        """Test task type classification."""
        client = GeminiClient(api_key="test-key")
        
        text = "Please embed this text for vector search"
        task_type = client.classify_task_type(text)
        assert task_type == "embedding"
        
        text = "Analyze this document"
        task_type = client.classify_task_type(text)
        assert task_type == "generation"  # Default
    
    def test_model_selection_with_cascading(self):
        """Test model selection with cascading enabled."""
        client = GeminiClient(api_key="test-key", enable_cascading=True)
        
        # Simple text should use fast tier
        simple_text = "What is 2+2?"
        model = client.select_model(simple_text, "generation")
        assert model.tier == ModelTier.FAST
        
        # Complex text should use smart tier  
        complex_text = "Analyze the following complex algorithm involving multiple steps..."
        model = client.select_model(complex_text, "generation")
        assert model.tier == ModelTier.SMART
        
        # Embedding text should use fast tier
        embedding_text = "Embed this text for search"
        model = client.select_model(embedding_text, "embedding")
        assert model.tier == ModelTier.FAST
    
    def test_model_selection_without_cascading(self):
        """Test model selection without cascading."""
        client = GeminiClient(api_key="test-key", enable_cascading=False)
        
        # Without cascading, should always use smart tier
        text = "Simple question"
        model = client.select_model(text, "generation")
        assert model.tier == ModelTier.SMART
    
    def test_cache_management(self):
        """Test cache functionality."""
        client = GeminiClient(api_key="test-key")
        
        cache_key = client._get_cache_key("test", "gemini-1.5-flash")
        
        # Cache should start empty
        assert client._get_cached_response(cache_key) is None
        
        # Add to cache
        test_data = {"content": "test"}
        client._cache_response(cache_key, test_data)
        
        # Should return cached data
        assert client._get_cached_response(cache_key) == test_data
        assert client._cache_timestamps[cache_key] is not None
        
        # Clear cache
        client.clear_cache()
        assert client._get_cached_response(cache_key) is None
        assert cache_key not in client._response_cache
    
    def test_budget_status_integration(self):
        """Test budget status integration."""
        client = GeminiClient(api_key="test-key")
        
        budget_status = client.get_budget_status()
        
        # Should contain required fields
        required_fields = [
            "budget_used_usd",
            "budget_remaining_usd", 
            "budget_used_percent",
            "predicted_monthly_cost_usd",
            "alert_level",
            "recommendations"
        ]
        for field in required_fields:
            assert field in budget_status, f"Missing required field: {field}"
    
    def test_optimization_report_integration(self):
        """Test optimization report integration."""
        client = GeminiClient(api_key="test-key")
        optimizations = client.get_optimization_report()
        
        # Should contain tier breakdown and optimization opportunities
        assert "tier_percentages" in optimizations
        assert "optimizations" in optimizations
        
        if "optimizations" in optimizations and optimizations["optimizations"]:
            for optimization in optimizations["optimizations"]:
                assert "type" in optimization, "Optimization missing type"
                assert "recommendation" in optimization, "Optimization missing recommendation"
    
    def test_disable_cascading(self):
        """Test client with cascading disabled."""
        client = GeminiClient(api_key="test-key")
        client.enable_cascading = False
        
        # Without cascading, model selection should fallback to smart tier
        model = client.select_model("Any prompt", "generation")
        assert model.tier == ModelTier.SMART
    
    def test_disable_caching(self):
        """Test client with caching disabled."""
        client = GeminiClient(api_key="test-key")
        client.enable_caching = False
        
        assert client.enable_caching is False
        assert client.clear_cache()  # Should work even when disabled
    
    def test_custom_configuration(self):
        """Test client with custom configuration."""
        custom_client = GeminiClient(
            api_key="test-key",
            enable_cascading=False,
            enable_caching=False,
            max_retries=5,
            timeout_seconds=60
        )
        
        assert custom_client.enable_cascading is False
        assert custom_client.enable_caching is False
        assert custom_client.max_retries == 5
        assert custom_client.timeout_seconds == 60
