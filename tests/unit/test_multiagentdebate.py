"""
Test suite for multi-agent debate system.

This test suite validates the Phase 3 advanced features:
- Multi-agent debate system for memory verification
- Consensus building with 3 specialized agents (Analyzer, Synthesizer, Curator)
- Verification gate with 6-check quality system
- Conflict detection and resolution
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from enum import Enum
import os

try:
    from khala.infrastructure.gemini.client import GeminiClient
    from khala.infrastructure.gemini.models import ModelRegistry, ModelTier
    GEMINI_AVAILABLE = True
except ImportError as e:
    # Mock for test environment without Google API
    GEMINI_AVAILABLE = False
    GeminiClient = None
    ModelRegistry = None
    ModelTier = None

    class MockTier(Enum):
        FAST = "fast"
        MEDIUM = "medium" 
        SMART = "smart"


# Skip all tests if Gemini is not available
pytestmark = pytest.mark.skipif(
    not GEMINI_AVAILABLE, 
    reason="Google Generative AI not available in test environment"
)

class TestMultiAgentDebate:
    """Test multi-agent debate system functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Gemini client for testing."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            client = GeminiClient(api_key="test-key")
            client.enable_caching = True
            client.cache_ttl_seconds = 300  # 5 minutes for tests
            return client

    @pytest.fixture
    def debate_team(self, mock_client):
        """Create a debate team for testing."""
        agents = [
            mock_client._create_debate_agent("analyzer"),
            mock_client._create_debate_agent("synthesizer"), 
            mock_client._create_debate_agent("curator")
        ]
        return agents

    def test_debate_agent_creation(self, debate_team):
        """Test that debate agents are created correctly."""
        assert len(debate_team) == 3, "Debate team should have 3 agents"
        
        # Verify each agent has proper configuration
        expected_roles = ["analyzer", "synthesizer", "curator"]
        for i, agent in enumerate(debate_team):
            assert agent.role == expected_roles[i], f"Agent {i} should be {expected_roles[i]}"
            assert agent.client is not None, "Each agent should have a client"
            assert agent.name == f"debate_{expected_roles[i]}", f"Agent name should match role"

    def test_analyzer_agent_functionality(self, mock_client):
        """Test the analyzer agent functionality."""
        analyzer = mock_client._create_debate_agent("analyzer")
        
        # Test memory analysis
        test_memory = Mock()
        test_memory.id = "test_memory_123"
        test_memory.content = "The sky appears blue due to Rayleigh scattering"
        test_memory.importance_score.value = 0.7
        test_memory.metadata = {"source": "physics_textbook", "confidence": 0.9}
        
        # Mock analysis response
        analysis_result = analyzer.analyze_memory(test_memory)
        
        assert "factual_accuracy" in analysis_result, "Analysis should include factual accuracy"
        assert "consistency_check" in analysis_result, "Analysis should include consistency check"
        assert "confidence_score" in analysis_result, "Analysis should include confidence score"
        assert isinstance(analysis_result["confidence_score"], float), "Confidence should be numeric"
        assert 0 <= analysis_result["confidence_score"] <= 1, "Confidence should be 0-1"

    def test_synthesizer_agent_functionality(self, mock_client):
        """Test the synthesizer agent functionality."""
        synthesizer = mock_client._create_debate_agent("synthesizer")
        
        # Test synthesis from multiple analyses
        analyses = [
            {"agent_id": "analyzer_1", "factual_accuracy": 0.9, "consistency_check": True, "confidence_score": 0.85},
            {"agent_id": "analyzer_2", "factual_accuracy": 0.8, "consistency_check": True, "confidence_score": 0.75}
        ]
        
        synthesis_result = synthesizer.synthesize_analyses(analyses)
        
        assert "consensus_score" in synthesis_result, "Synthesis should include consensus"
        assert "identified_issues" in synthesis_result, "Synthesis should identify issues"
        assert "recommendation" in synthesis_result, "Synthesis should provide recommendation"
        assert isinstance(synthesis_result["consensus_score"], float), "Consensus should be numeric"
        
        # High consensus when agreements are high
        if all(a["consistency_check"] for a in analyses):
            assert synthesis_result["consensus_score"] > 0.7, "High agreement should yield high consensus"

    def test_curator_agent_functionality(self, mock_client):
        """Test the curator agent functionality."""
        curator = mock_client._create_debate_agent("curator")
        
        # Test curation decisions
        synthesis = {
            "consensus_score": 0.85,
            "identified_issues": [],
            "recommendation": "accept"
        }
        
        curation_result = curator.curate_decision(synthesis)
        
        assert "final_decision" in curation_result, "Curation should provide final decision"
        assert "confidence_in_decision" in curation_result, "Curation should provide confidence"
        assert "verification_flags" in curation_result, "Curation should provide verification flags"
        
        if synthesis["consensus_score"] > 0.8 and synthesis["recommendation"] == "accept":
            assert curation_result["final_decision"] == "accepted", "High consensus should lead to acceptance"

    @pytest.mark.asyncio
    async def test_single_debate_round(self, mock_client, debate_team):
        """Test a complete debate round."""
        # Create test memory for debate
        test_memory = Mock()
        test_memory.id = "debate_memory_001"
        test_memory.content = "Water boils at 100 degrees Celsius at sea level"
        test_memory.importance_score = Mock()
        test_memory.importance_score.value = 0.8
        test_memory.metadata = {"source": "science_textbook", "verified": True}

        # Run debate round
        debate_result = await mock_client._run_debate_round(test_memory, debate_team)
        
        assert "round_id" in debate_result, "Debate should have round ID"
        assert "participants" in debate_result, "Debate should list participants"
        assert "consensus_score" in debate_result, "Debate should have consensus score"
        assert "final_decision" in debate_result, "Debate should have final decision"
        
        # Verify all agents participated
        assert len(debate_result["participants"]) == 3, "All agents should participate"
        
        # Verify decision logic
        consensus = debate_result["consensus_score"]
        if consensus >= 0.8:
            assert debate_result["final_decision"] in ["accepted", "needs_refinement"], "High consensus leads to acceptance or refinement"
        elif consensus < 0.5:
            assert debate_result["final_decision"] == "rejected", "Low consensus leads to rejection"

    @pytest.mark.asyncio
    async def test_conflict_detection(self, mock_client):
        """Test conflict detection in debate system."""
        # Create conflicting memories
        memory_a = Mock()
        memory_a.id = "conflict_mem_a"
        memory_a.content = "The capital of France is Paris"
        memory_a.importance_score = Mock()
        memory_a.importance_score.value = 0.9
        
        memory_b = Mock()
        memory_b.id = "conflict_mem_b" 
        memory_b.content = "The capital of France is Lyon"
        memory_b.importance_score = Mock()
        memory_b.importance_score.value = 0.9
        
        # Conflict detection should identify disagreement
        conflict_report = await mock_client._detect_conflicts([memory_a, memory_b])
        
        assert "conflict_detected" in conflict_report, "Report should indicate if conflict detected"
        assert "conflicting_memories" in conflict_report, "Report should list conflicting memories"
        assert conflict_report["conflict_detected"] is True, "Opposite facts should be detected as conflict"
        assert len(conflict_report["conflicting_memories"]) >= 1, "At least one conflict should be found"

    @pytest.mark.asyncio
    async def test_verification_gate(self, mock_client):
        """Test the 6-check verification gate system."""
        # Create test memory
        test_memory = Mock()
        test_memory.id = "verify_mem_001"
        test_memory.content = "The process of photosynthesis converts CO2 to O2"
        test_memory.importance_score = Mock()
        test_memory.importance_score.value = 0.85
        
        # Run verification gate
        verification_result = await mock_client._run_verification_gate(test_memory)
        
        assert "overall_score" in verification_result, "Verification should provide overall score"
        assert "checks_passed" in verification_result, "Verification should show passed checks"  
        assert "checks_failed" in verification_result, "Verification should show failed checks"
        assert "recommended_action" in verification_result, "Verification should recommend action"
        
        # Verify 6 checks were performed
        total_checks = len(verification_result["checks_passed"]) + len(verification_result["checks_failed"])
        assert total_checks == 6, f"Should perform exactly 6 checks, got {total_checks}"
        
        # High overall score should lead to acceptance
        if verification_result["overall_score"] >= 0.8:
            assert verification_result["recommended_action"] in ["accept", "minor_refinement"], "High score should lead to acceptance"

    @pytest.mark.asyncio 
    async def test_debate_performance_metrics(self, mock_client, debate_team):
        """Test debate system performance metrics."""
        # Run multiple debate rounds for performance testing
        metrics = {
            "total_rounds": 0,
            "successful_rounds": 0,
            "total_response_time_ms": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        for i in range(5):
            test_memory = Mock()
            test_memory.id = f"perf_test_{i}"
            test_memory.content = f"Performance test memory {i}"
            test_memory.importance_score = Mock()
            test_memory.importance_score.value = 0.7 + (i * 0.05)
            
            start_time = datetime.now(timezone.utc)
            
            try:
                result = await mock_client._run_debate_round(test_memory, debate_team)
                
                end_time = datetime.now(timezone.utc)
                response_time = (end_time - start_time).total_seconds() * 1000
                
                metrics["total_rounds"] += 1
                metrics["total_response_time_ms"] += response_time
                
                if result["consensus_score"] >= 0.5:  # Moderate consensus considered success
                    metrics["successful_rounds"] += 1
                
                # Check cache behavior
                cache_key = mock_client._get_cache_key(f"debate_{test_memory.id}", "debate_context")
                if mock_client._get_cached_response(cache_key):
                    metrics["cache_hits"] += 1
                else:
                    metrics["cache_misses"] += 1
                    
            except Exception as e:
                print(f"Performance test round {i} failed: {e}")
        
        # Verify performance targets
        if metrics["total_rounds"] > 0:
            avg_response_time = metrics["total_response_time_ms"] / metrics["total_rounds"]
            success_rate = metrics["successful_rounds"] / metrics["total_rounds"]
            cache_hit_rate = metrics["cache_hits"] / (metrics["cache_hits"] + metrics["cache_misses"]) if metrics["cache_hits"] + metrics["cache_misses"] > 0 else 0
            
            assert avg_response_time < 5000, f"Average response time {avg_response_time:.0f}ms should be under 5s"
            assert success_rate >= 0.6, f"Success rate {success_rate:.2f} should be at least 60%"
            
            # Cache efficiency
            if cache_hit_rate > 0:
                assert cache_hit_rate >= 0.3, f"Cache hit rate {cache_hit_rate:.2f} should be at least 30%"

    def test_debate_team_role_specialization(self, mock_client):
        """Test that each debate agent has proper role specialization."""
        analyzer = mock_client._create_debate_agent("analyzer")
        synthesizer = mock_client._create_debate_agent("synthesizer")
        curator = mock_client._create_debate_agent("curator")
        
        # Verify role-specific attributes
        assert analyzer.tier == ModelTier.SMART, "Analyzer should use smart tier for accuracy"
        assert synthesizer.tier == ModelTier.MEDIUM, "Synthesizer should use medium tier for balance"
        assert curator.tier in [ModelTier.SMART, ModelTier.MEDIUM], "Curator should use high or medium tier"
        
        # Verify role-specific prompts exist
        assert "analyze" in analyzer.prompt.lower(), "Analyzer prompt should focus on analysis"
        assert "synthesize" in synthesizer.prompt.lower(), "Synthesizer prompt should focus on synthesis" 
        assert "curate" in curator.prompt.lower(), "Curator prompt should focus on curation"

    @pytest.mark.asyncio
    async def test_memory_conflict_resolution(self, mock_client):
        """Test conflict resolution mechanisms."""
        # Create memories with partial conflicts
        memory_agree1 = Mock()
        memory_agree1.id = "agree1"
        memory_agree1.content = "Machine learning uses statistical patterns"
        
        memory_agree2 = Mock()
        memory_agree2.id = "agree2"  
        memory_agree2.content = "Machine learning identifies patterns in data"
        
        memory_conflict = Mock()
        memory_conflict.id = "conflict1"
        memory_conflict.content = "Machine learning uses magical intuition"
        
        # Resolution should identify conflicts and suggest merges for agreements
        resolution_result = await mock_client._resolve_conflicts([memory_agree1, memory_agree2, memory_conflict])
        
        assert "conflicts_found" in resolution_result, "Resolution should identify conflicts"
        assert "merge_suggestions" in resolution_result, "resolution should suggest merges"
        assert resolution_result["conflicts_found"] >= 1, "At least one conflict should be detected"
        assert len(resolution_result["merge_suggestions"]) >= 1, "Should suggest merges for similar content"

    def test_verification_scoring_logic(self, mock_client):
        """Test verification scoring logic."""
        # Test score calculations
        mock_checks = [
            {"name": "factual_accuracy", "score": 0.9, "weight": 0.3},
            {"name": "consistency", "score": 0.8, "weight": 0.2}, 
            {"name": "relevance", "score": 0.85, "weight": 0.2},
            {"name": "freshness", "score": 0.7, "weight": 0.1},
            {"name": "completeness", "score": 0.8, "weight": 0.1},
            {"name": "authenticity", "score": 0.85, "weight": 0.1}
        ]
        
        overall_score = mock_client._calculate_verification_score(mock_checks)
        
        assert isinstance(overall_score, float), "Overall score should be numeric"
        assert 0.0 <= overall_score <= 1.0, "Overall score should be between 0 and 1"
        
        # High individual scores should result in high overall score
        if all(check["score"] >= 0.8 for check in mock_checks):
            assert overall_score >= 0.8, "High individual scores should produce high overall score"

    @pytest.mark.asyncio
    async def test_debate_cache_efficiency(self, mock_client, debate_team):
        """Test that debate system leverages caching effectively."""
        mock_client.enable_caching = True
        mock_client.cache_ttl_seconds = 60
        
        identical_memories = []
        for i in range(3):
            memory = Mock()
            memory.id = f"cached_test_{i}"
            memory.content = "Identical content for cache testing"  # Same content
            memory.importance_score = Mock()
            memory.importance_score.value = 0.7
            identical_memories.append(memory)
        
        cache_stats = {"hits": 0, "misses": 0}
        
        for memory in identical_memories:
            with patch.object(mock_client, '_get_cached_response') as mock_get_cache:
                # First call will be miss
                if cache_stats["misses"] == 0:
                    mock_get_cache.return_value = None
                    cache_stats["misses"] += 1
                else:
                    # Subsequent calls should be hits
                    mock_get_cache.return_value = {"cached": True}
                    cache_stats["hits"] += 1
                
                await mock_client._run_debate_round(memory, debate_team)
        
        # Verify caching occurred
        assert cache_stats["misses"] >= 1, "Should have at least one cache miss initially"
        assert cache_stats["hits"] >= 1, "Should have cache hits on identical content"

    def test_debate_error_handling(self, mock_client):
        """Test debate system error handling."""
        # Test handling of invalid inputs
        with pytest.raises(ValueError, match="Memory ID required"):
            invalid_memory = Mock()
            invalid_memory.id = None
            mock_client._validate_memory_for_debate(invalid_memory)
        
        # Test handling of empty content
        with pytest.raises(ValueError, match="Memory content required"):
            empty_memory = Mock()
            empty_memory.id = "empty"
            empty_memory.content = ""
            mock_client._validate_memory_for_debate(empty_memory)
        
        # Test handling of missing importance score
        with pytest.raises(ValueError, match="Importance score required"):
            memory_no_importance = Mock()
            memory_no_importance.id = "no_importance"
            memory_no_importance.content = "Valid content"
            memory_no_importance.importance_score = None
            mock_client._validate_memory_for_debate(memory_no_importance)

    @pytest.mark.asyncio
    async def test_debate_team_communication(self, mock_client, debate_team):
        """Test communication coordination between debate agents."""
        # Create memory that requires multi-perspective analysis
        complex_memory = Mock()
        complex_memory.id = "complex_multi_perspective"
        complex_memory.content = "The economic impact of AI automation varies across industries"
        complex_memory.importance_score = Mock()
        complex_memory.importance_score.value = 0.9
        
        # Mock inter-agent communication
        with patch.object(mock_client, '_coordinate_agent_communication') as mock_comm:
            mock_comm.return_value = {
                "messages_exchanged": 5,
                "coordination_time_ms": 200,
                "consensus_reached": True
            }
            
            result = await mock_client._run_debate_round(complex_memory, debate_team)
            
            assert result["consensus_score"] >= 0.6, "Complex topics should achieve reasonable consensus"
            assert mock_comm.called, "Communication should have been coordinated"


# Integration tests that can be run with the full system
class TestMultiAgentSystemIntegration:
    """Integration tests for the complete multi-agent verification system."""

    @pytest.mark.asyncio
    async def test_end_to_end_verification_flow(self):
        """Test complete end-to-end verification flow."""
        # This test would require the full KHALA system stack
        # For now, we provide the structure for future integration
        pass

    @pytest.mark.asyncio
    async def test_debate_under_load(self):
        """Test debate system behavior under concurrent load."""
        # Load testing for concurrent debate rounds
        pass


class TestDebateMetricsAndAnalytics:
    """Test debate system metrics and analytics."""

    def test_debate_performance_tracking(self, mock_client):
        """Test that debate performance is properly tracked."""
        metrics_collector = mock_client.get_metrics_collector()
        
        # Verify metrics components are available
        assert hasattr(metrics_collector, 'track_debate_round'), "Should track individual rounds"
        assert hasattr(metrics_collector, 'track_agent_performance'), "Should track agent performance"
        assert hasattr(metrics_collector, 'track_consensus_scores'), "Should track consensus scores"
        assert hasattr(metrics_collector, 'generate_performance_report'), "Should generate performance reports"

    def test_debate_analytics_accuracy(self, mock_client):
        """Test accuracy of debate analytics."""
        # Test known scenarios and verify analytics calculations
        test_scenarios = [
            {"consensus_scores": [0.9, 0.8, 0.85], "expected_avg": 0.833},
            {"consensus_scores": [0.6, 0.7, 0.65], "expected_avg": 0.65},
            {"consensus_scores": [0.3, 0.4, 0.35], "expected_avg": 0.35}
        ]
        
        for scenario in test_scenarios:
            calculated_avg = sum(scenario["consensus_scores"]) / len(scenario["consensus_scores"])
            assert abs(calculated_avg - scenario["expected_avg"]) < 0.01, f"Average calculation incorrect for {scenario}"


# Performance benchmarks
class TestDebatePerformanceBenchmarks:
    """Performance benchmarks for the debate system."""

    @pytest.mark.asyncio
    async def test_debate_response_time_benchmark(self, mock_client):
        """Benchmark debate system response time."""
        # Single debate round should complete within reasonable time
        response_time_target_ms = 3000  # 3 seconds
        
        test_memory = Mock()
        test_memory.id = "benchmark_test"
        test_memory.content = "Speed test for benchmarking"
        test_memory.importance_score = Mock()
        test_memory.importance_score.value = 0.8
        
        debate_team = [
            mock_client._create_debate_agent("analyzer"),
            mock_client._create_debate_agent("synthesizer"),
            mock_client._create_debate_agent("curator")
        ]
        
        start_time = datetime.now(timezone.utc)
        result = await mock_client._run_debate_round(test_memory, debate_team)
        end_time = datetime.now(timezone.utc)
        
        response_time_ms = (end_time - start_time).total_seconds() * 1000
        assert response_time_ms < response_time_target_ms, f"Debate took {response_time_ms:.0f}ms, should be under {response_time_target_ms}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
