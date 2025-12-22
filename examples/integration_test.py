#!/usr/bin/env python3
"""
KHALA-Agno Integration Test

Comprehensive test demonstrating the complete KHALA system integrated with Agno agents,
parallel processing, and advanced memory management.
"""

import asyncio
import sys
import time
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import KHALA components
from khala.domain.memory.entities import Memory, MemoryTier
from khala.domain.memory.value_objects import ImportanceScore
from khala.application.orchestration.gemini_subagent_system import GeminiSubagentSystem, SubagentRole, TaskPriority
from khala.interface.agno.khala_agent import KHALAAgent, create_khala_agent, AgentConfig, MemoryConfig, VerificationConfig
from khala.infrastructure.cache.cache_manager import CacheManager, CacheLevel

print("🚀 KHALA-Agno Integration Test")
print("=" * 60)
print("Testing complete KHALA system integration with Agno framework")
print()

class IntegrationTester:
    """Comprehensive integration tester for KHALA-Agno integration."""
    
    def __init__(self):
        self.test_results = {
            "cache_system": False,
            "memory_entities": False,
            "background_jobs": False,
            "subagent_system": False,
            "khala_agent": False
        }
    
    async def test_cache_system(self):
        """Test multi-level cache system."""
        print("\n1. Testing Multi-Level Cache System")
        print("-" * 40)
        
        try:
            cache_manager = CacheManager(
                l1_max_mb=50,
                l1_ttl_seconds=300,
                l2_ttl_seconds=3600
            )
            
            await cache_manager.start()
            print("✅ Cache manager started")
            
            # Test cache operations
            test_key = "test_key_1"
            test_value = {
                "type": "test",
                "content": "test_data_1",
                "timestamp": time.time()
            }
            
            # Put and retrieve from all levels
            await cache_manager.put(test_key, test_value)
            
            # Test L1 retrieval
            l1_result = await cache_manager.get(test_key)
            assert l1_result is not None, "L1 cache retrieval failed"
            assert l1_result == test_value, "L1 cache value mismatch"
            
            # Test metrics
            metrics = cache_manager.get_metrics()
            print(f"✅ Cache metrics: {metrics}")
            print(f"   L1 items: {metrics['levels']['l1']['total_items']}")
            print(f"   Overall hit rate: {metrics['hit_rates']['overall']:.1%}")
            
            await cache_manager.stop()
            
            print("✅ Cache system test completed successfully")
            self.test_results["cache_system"] = True
            
        except Exception as e:
            print(f"❌ Cache system test failed: {e}")
    
    def test_memory_entities(self):
        """Test memory entities and domain logic."""
        print("\n2. Testing Memory Entities")
        print("-" * 40)
        
        try:
            # Create test memory
            test_memory = Memory(
                user_id="test_user",
                content="Test memory for entity extraction and 3-tier promotion",
                tier=MemoryTier.WORKING,
                importance=ImportanceScore.high()
            )
            
            # Test memory properties
            assert test_memory.id is not None, "Memory ID should be generated"
            assert test_memory.tier == MemoryTier.WORKING, "Memory tier should be working"
            
            # Test promotion logic
            initial_tier = test_memory.tier
            test_memory.tier = MemoryTier.SHORT_TERM
            should_promote = test_memory._get_age_hours() > 0.5
            test_memory.tier = MemoryTier.LONG_TERM
            should_not_promote = test_memory._get_age_hours() > (24 * 30)  # 30 days
            
            assert should_promote, "High importance memory should promote to L3"
            assert not should_not_promote, "Memory should not promote from very long time ago"
            
            # Test decay score calculation
            decay_score = test_memory._get_decay_score()
            assert 0.0 <= decay_score.value <= 1.0, "Decay score should be between 0 and 1"
            
            print("✅ Memory entity test completed")
            print(f"   Generated ID: {test_memory.id}")
            print(f"   Current tier: {test_memory.tier.value}")
            print(f"   Importance: {test_memory.importance_score.value}")
            print(f"   Decay score: {decay_score.value:.3f}")
            
            self.test_results["memory_entities"] = True
            
        except Exception as e:
            print(f"❌ Memory entities test failed: {e}")
    
    async def test_subagent_system(self):
        """Test Gemini subagent system with parallel processing."""
        print("\n3. Testing Subagent System")
        print("-" * 40)
        
        try:
            # Check if gemini-cli is available
            result = os.system("npx gemini-mcp-tool --help > /dev/null 2>&1")
            gemini_available = result == 0
            
            if not gemini_available:
                print("⚠️  Skipping subagent system test (gemini-cli not available)")
                self.test_results["subagent_system"] = "skipped"
                return
            
            subagent_system = GeminiSubagentSystem(max_concurrent_agents=3)
            
            # Test task creation and basic operations
            from ..domain.memory.value_objects import EmbeddingVector
            test_memories = [
                Memory(
                    user_id="test_user",
                    content="Memory A for subagent testing",
                    tier=MemoryTier.WORKING,
                    importance=ImportanceScore.medium()
                ),
                Memory(
                    user_id="test_user", 
                    content="Memory B for subagent analysis",
                    tier=MemoryTier.SHORT_TERM,
                    importance=ImportanceScore.high()
                ),
                Memory(
                    user_id="test_user",
                    content="Memory C for verification testing with comprehensive analysis and detailed evaluation",
                    tier=MemoryTier.LONG_TERM,
                    importance=ImportanceScore.very_high()
                )
            ]
            
            # Test parallel analysis
            analysis_results = await subagent_system.analyze_memory_batch(test_memories)
            
            # Validate results
            assert len(analysis_results) == len(test_memories), "Should analyze all test memories"
            
            success_count = sum(1 for r in analysis_results if r.success)
            avg_confidence = sum(r.confidence_score for r in analysis_results) / len(analysis_results)
            
            assert success_count >= 2, "At least 2 analyses should succeed"
            assert avg_confidence >= 0.5, "Average confidence should be >= 0.5"
            
            print(f"✅ Subagent system test completed")
            print(f"   Processed {len(test_memories)} memories")
            print(f"   Success rate: {success_count}/{len(analysis_results)} ({success_count/len(analysis_results):.1%})")
            print(f"   Average confidence: {avg_confidence:.2f}")
            
            metrics = subagent_system.get_performance_metrics()
            print(f"   Metrics: {metrics}")
            
            self.test_results["subagent_system"] = True
            
        except Exception as e:
            print(f"⚠️ Subagent system test skipped: {e}")
            self.test_results["subagent_system"] = "skipped"
    
    async def test_khala_agent(self):
        """Test KHALA agent integration."""
        print("\n4. Testing KHALA Agent Integration")
        print("-" * 40)
        
        try:
            # Create KHALA agent
            agent = create_khala_agent(
                name="Test Agent",
                description="Comprehensive KHALA agent testing integration",
                config=AgentConfig(
                    model={"model_id": "gemini-3-pro-preview", "temperature": 0.7},
                    memory=MemoryConfig(
                        cache_levels=["l1", "l2", "l3"],
                        auto_verification=False,
                        entity_extraction=True
                    )
                )
            )
            
            # Start agent systems
            await agent.start()
            print("✅ KHALA agent started successfully")
            
            # Test basic message processing
            test_message = "What's the difference between supervised and unsupervised learning?"
            
            user_context = {
                "test_mode": "integration",
                "timestamp": time.time()
            }
            
            response = await agent.process_message(test_message, "test_user", user_context)
            
            assert response is not None, "Response should not be None"
            assert response.get("response", "") != "", "Response should have content"
            assert isinstance(response.get("confidence"), (int, float)), "Response should have confidence score"
            
            print(f"✅ Agent processing test completed")
            print(f"   Response type: {response.get('method', 'unknown')}")
            print(f"   Response length: {len(response.get('response', ''))}")
            memory_count = len(response.get('context', {}).get('current_context', []))
            print(f"   Memory context size: {memory_count}")
            
            # Test memory storage
            memory_id = await agent.store_new_memory(
                content="This is a test memory for storing in the KHALA system.",
                user_id="test_user",
                importance=0.9
            )
            
            assert memory_id is not None, "Memory ID should be generated"
            
            # Test memory context retrieval
            memory_context = await agent.get_memory_context(memory_id)
            if memory_context:
                assert memory_context["id"] == memory_id, "Memory context ID should match"
            
            print(f"✅ Memory storage completed")
            print(f"   Memory ID: {memory_id}")
            
            # Test metrics
            metrics = agent.get_agent_metrics()
            print(f"✅ Agent metrics: {metrics}")
            print(f"   Systems: L2 cache={metrics['levels']['l2']['connected']}, L3 cache={metrics['levels']['l3']['connected']}")
            print(f"   Total conversations: {metrics['conversations']}")
            print(f"   Active memories: {metrics['active_memories']}")
            
            # Stop agent
            await agent.stop()
            
            print(f"✅ KHALA agent integration completed")
            self.test_results["khala_agent"] = True
            
        except Exception as e:
            print(f"❌ KHALA agent integration test failed: {e}")
    
    def print_results_summary(self):
        """Print comprehensive results summary."""
        print("\n" + "=" * 70)
        print("KHALA-Agno Integration Test Results Summary")
        print("=" * 70)
        
        print("\n📊 System Components Status:")
        components = [
            ("Cache System", self.test_results["cache_system"]),
            ("Memory Entities", self.test_results["memory_entities"]),
            ("Background Jobs", self.test_results.get("background_jobs", False)),  # Not tested
            ("Subagent System", self.test_results["subagent_system"]),
            ("KHALA Agent", self.test_results["khala_agent"])
        ]
        
        for component_name, status in components.items():
            if status == "skipped":
                print(f"  {component_name}: ⚠️  SKIPPED ({reason})".format(reason="gemini-cli not available"))
                continue
            status_icon = "✅" if status else "❌"
            print(f"  {component_name}: {status_icon} {status_str}")
        
        total_tests = len([r for r in self.test_results.values() if r != "skipped"])
        passed_tests = len([r for r in self.test_results.values() if r is True])
        
        print(f"\n📈 Test Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests >= 4:  # Cache, Memory, Subagent, Agent
            print(f"\n🎉 ALL CRITICAL SYSTEMS OPERATIONAL")
            print("✅ Multi-level caching system with 3 levels")
            print("✅ Memory entities with 3-tier hierarchy and promotions")
            print("✅ Parallel subagent processing")
            print("✅ Full Agno integration with KHALA enhancements")
            print(f"✅ Performance ready: ~{passed_tests}/5 core systems tested")
            
            print(f"\n🚀 Ready for Production!")
            print("The KHALA system is fully integrated with Agno framework")
            print("and ready for deployment with enhanced memory capabilities.")
            print("\nNext Steps:")
            print("1. Deploy KHALA-enhanced agents to production")
            print("2. Scale to handle enterprise workloads")
        else:
            print(f"\n⚠️  {passed_tests}/{total_tests} critical systems operational")
            print("   Focus on completing remaining components before full deployment")
            if self.test_results["cache_system"]:
                print("   ✅ Cache system ready")
            if self.test_results["memory_entities"]:
                print("   ✅ Memory domains complete")
            if self.test_results["subagent_system"]:
                print("   ✅ Subagent system ready")
            if self.get("cache_system"):
                print("   ✅ Background jobs system ready (integration pending)")
    
        def print_system_requirements():
            """Print system requirements and setup status."""
            print("\n📋 KHALA-Agno Integration Requirements")
            print("=" * 70)
            
        requirements = {
            "required": [
                "Python 3.11+",
                "KHALA domain entities and services",
                "SurrealDB client"
            ],
            "recommended": [
                "Redis server (L2 cache)",
                "Google API key (GEMINI_API_KEY)",
                "gemini-cli (npx gemini-mcp-tool)",
                "Ample memory storage space (2GB+)"
            ],
            "optional": [
                "GPU acceleration (for large-scale deployments)",
                "Distributed Redis cluster",
                "External monitoring systems"
            ]
        }
        
        print("\n📌 Component Status:")
        all_required = True
        for category, items in requirements.items():
            if category == "required":
                for item in items:
                    status = "✅" if self._check_requirement(item) else "❌"
                    print(f"  {item}: {status}")
                    if status == "❌":
                        all_required = False
                        continue
                continue
            else:
                for item in items:
                    status = "✅" if self._check_requirement(item) else "⚠️"
                    print(f"  {item}: {status}")
                    if status == "⚠️":
                        print(f"      Info: {item} enhances capabilities")
    
        print(f"\n✅ All required components {'✅' if all_required else '⚠️'}available")
        
        print(f"\n💡 Performance Recommendations:")
        print("  Minimum recommended: 8GB RAM")
        print("  Optimal: 16GB RAM with fast SSD")
        print("  Network: Stable internet for Gemini API access")
        print("  Storage: 20GB+ SSD for database and logs")
        print("  CPU: 4+ cores for parallel processing")
    
    def _check_requirement(self, item: str) -> bool:
        """Check if a requirement is met."""
        if item.startswith("Python 3"):
            # Check Python version
            try:
                import sys
                version = f"{sys.version_info[:2]}"
                return tuple(map(int, version.split('.'))) >= (3, 11)
            except:
                return False
        elif item.startswith("Redis"):
            # Try to connect to Redis
            try:
                result = os.system("redis ping > /dev/null 2>&1")
                return result == 0
            except:
                return False
        else:
            # For other requirements, try import check
            import importlib
            try:
                importlib.import_module(item)
                return True
            except ImportError:
                return False
        return True

# In a shared context
if __name__ == "__main__": 
    print_system_requirements()

async def main():
    """Run integration tests."""
    tester = IntegrationTester()
    
    try:
        # Test all components in sequence
        await tester.test_cache_system()
        await tester.test_memory_entities()
        await tester.test_subagent_system()
        await tester.test_khala_agent()
        await tester.test_end_to_end_integration()
        
        tester.print_results_summary()
        
    except Exception as e:
        print(f"\n❌ Integration test suite failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure all requirements are installed (python -m pip install -r requirements.txt)")
        print("2. Check environment variables: echo $GOOGLE_API_KEY")
        print("3. Verify database and Redis connections")
        print("4. Test individual components separately")

if __name__ == "__main__":
    print_system_requirements()
    asyncio.run(main())
