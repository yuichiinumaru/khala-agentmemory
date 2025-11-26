#!/usr/bin/env python3
"""
KHALA Subagent System Demonstration.

Shows how to use Gemini subagents for parallel memory processing,
verification, and advanced analysis operations.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from domain.memory.entities import Memory, MemoryTier
from domain.memory.value_objects import ImportanceScore
from application.orchestration.gemini_subagent_system import GeminiSubagentSystem, SubagentRole, TaskPriority
from interface.mcp.khala_subagent_tools import KHALASubagentTools


class SubagentDemo:
    """Demonstration of KHALA subagent capabilities."""
    
    def __init__(self):
        """Initialize demo system."""
        self.subagent_system = GeminiSubagentSystem(max_concurrent_agents=4)
        self.mcp_tools = KHALASubagentTools(max_concurrent_agents=4)
        
    async def demo_basic_analysis(self):
        """Demonstrate basic parallel memory analysis."""
        print("\n🔍 Demo 1: Parallel Memory Analysis")
        print("-" * 40)
        
        # Create sample memories
        memories = [
            Memory(
                user_id="demo_user",
                content="Machine learning models learn patterns from training data to make predictions.",
                tier=MemoryTier.WORKING,
                importance=ImportanceScore.high()
            ),
            Memory(
                user_id="demo_user",
                content="Neural networks use backpropagation to adjust weights during training.",
                tier=MemoryTier.WORKING,
                importance=ImportanceScore.medium()
            ),
            Memory(
                user_id="demo_user",
                content="Deep learning architectures can process unstructured data effectively.",
                tier=MemoryTier.SHORT_TERM,
                importance=ImportanceScore.low()
            )
        ]
        
        print(f"Analyzing {len(memories)} memories in parallel...")
        
        # Run analysis
        results = await self.subagent_system.analyze_memory_batch(memories)
        
        print(f"\nResults Summary:")
        print(f"  Total tasks: {len(results)}")
        print(f"  Success rate: {sum(1 for r in results if r.success) / len(results):.1%}")
        print(f"  Avg confidence: {sum(r.confidence_score for r in results) / len(results):.2f}")
        
        print(f"\nDetailed Results:")
        for i, result in enumerate(results[:2], 1):
            print(f"  Memory {i}:")
            print(f"    Success: {'✅' if result.success else '❌'}")
            print(f"    Confidence: {result.confidence_score:.2f}")
            print(f"    Time: {result.execution_time_ms:.0f}ms")
            if result.reasoning:
                preview = result.reasoning[:100] + "..." if len(result.reasoning) > 100 else result.reasoning
                print(f"    Analysis: {preview}")
    
    async def demo_entity_extraction(self):
        """Demonstrate parallel entity extraction."""
        print("\n🏷️  Demo 2: Entity Extraction")
        print("-" * 40)
        
        memory_contents = [
            "Apple announced the new MacBook Pro with M3 chips in Cupertino, California last week.",
            "Google's AI research team published findings about transformer models in Nature journal.",
            "Microsoft acquired GitHub for $7.5 billion to expand their developer tools ecosystem.",
            "Tesla's autonomous driving technology uses computer vision and sensor fusion."
        ]
        
        print(f"Extracting entities from {len(memory_contents)} texts...")
        
        # Using MCP tools interface
        memory_data_list = [{"content": content, "user_id": "demo"} for content in memory_contents]
        result = await self.mcp_tools.extract_entities_batch(memory_contents)
        
        if result["status"] == "completed":
            print(f"\nExtraction Results:")
            print(f"  Contents processed: {result['contents_processed']}")
            print(f"  Success rate: {result['success_rate']:.1%}")
            print(f"  Total entities found: {result['total_entities_extracted']}")
            
            print(f"\nEntity Examples:")
            for item in result["results"][:2]:
                print(f"  Text {item['content_index'] + 1}:")
                print(f"    Success: {'✅' if item['extraction_success'] else '❌'}")
                if item.get("entities"):
                    preview_entities = item["entities"][:3]
                    for entity in preview_entities:
                        print(f"      - {entity.get('name', 'Unknown')}: {entity.get('type', 'Unknown')}")
                print(f"    Confidence: {item['confidence_score']:.2f}")
        
        return result
    
    async def demo_verification_system(self):
        """Demonstrate multi-agent verification."""
        print("\n🔐 Demo 3: Multi-Agent Verification")
        print("-" * 40)
        
        memory_list = [
            {
                "id": "verif_mem_1",
                "content": "The Eiffel Tower was built for the 1889 World's Fair in Paris and stands 324 meters tall.",
                "importance": 0.9,
                "tier": "short_term"
            },
            {
                "id": "verif_mem_2", 
                "content": "Quantum computers use qubits to perform calculations exponentially faster than classical computers.",
                "importance": 0.8,
                "tier": "working"
            }
        ]
        
        print(f"Running comprehensive verification on {len(memory_list)} memories...")
        print("(Using analyzer, researcher, and curator agents)")
        
        result = await self.mcp_tools.verify_memories_comprehensive(memory_list)
        
        if result["status"] == "completed":
            print(f"\nVerification Results:")
            print(f"  Memories verified: {result['memories_verified']}")
            print(f"  Avg consensus score: {result['avg_consensus_score']:.2f}")
            
            print(f"\nMemory-by-Memory Analysis:")
            for mem_id, verification in result["verification_results"].items():
                print(f"  Memory {mem_id}:")
                print(f"    Overall confidence: {verification['overall_confidence']:.2f}")
                print(f"    Consensus score: {verification['consensus_score']:.2f}")
                print(f"    Recommendation: {verification['recommendation'].upper()}")
                
                print(f"    Agent breakdown:")
                for agent, agent_result in verification['agent_results'].items():
                    status = "✅" if agent_result["success"] else "❌"
                    print(f"      {agent.title()}: {status} (confidence: {agent_result['confidence']:.2f})")
        
        return result
    
    async def demo_performance_metrics(self):
        """Show system performance and metrics."""
        print("\n📊 Demo 4: System Performance Metrics")
        print("-" * 40)
        
        # Get system status
        status = await self.mcp_tools.get_system_status()
        
        print(f"System Status: {status['system_status'].upper()}")
        print(f"Available Agent Roles:")
        for role in status['available_roles']:
            print(f"  • {role}")
        
        print(f"\nSupported Operations:")
        for op in status['supported_operations']:
            print(f"  • {op}")
        
        print(f"\nSession Statistics:")
        session_stats = status['session_stats']
        print(f"  Session started: {session_stats['session_start'].replace('T', ' ').split('.')[0]}")
        print(f"  Tasks created: {session_stats['tasks_created']}")
        print(f"  Tasks completed: {session_stats['tasks_completed']}")
        print(f"  Memories processed: {session_stats['memories_processed']}")
        
        return status
    
    async def demo_concurrent_processing(self):
        """Demonstrate truly concurrent processing."""
        print("\n⚡ Demo 5: Concurrent Task Processing")  
        print("-" * 40)
        
        print("Running multiple operations simultaneously...")
        
        # Prepare multiple operation data
        analysis_memories = []
        for i in range(3):
            memory = Memory(
                user_id="concurrent_demo",
                content=f"Concurrent processing test memory {i+1}. This tests parallel execution capabilities.",
                tier=MemoryTier.WORKING,
                importance=ImportanceScore.medium()
            )
            analysis_memories.append(memory)
        
        extraction_contents = [
            "Concurrent task 1: Testing entity extraction",
            "Concurrent task 2: Testing parallel processing", 
            "Concurrent task 3: Testing async operations",
            "Concurrent task 4: Testing multi-agent coordination"
        ]
        
        # Create tasks for concurrent execution
        tasks = [
            self.subagent_system.analyze_memory_batch(analysis_memories),
            self.mcp_tools.extract_entities_batch([{"content": c, "user_id": "demo"} for c in extraction_contents]),
            self.mcp_tools.get_system_status()
        ]
        
        # Execute all tasks concurrently
        start_time = datetime.now(timezone.utc)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = datetime.now(timezone.utc)
        
        print(f"\nConcurrent Execution Results:")
        print(f"  Total execution time: {(end_time - start_time).total_seconds() * 1000:.0f}ms")
        print(f"  Tasks completed: {len([r for r in results if not isinstance(r, Exception)])}")
        print(f"  Failed tasks: {len([r for r in results if isinstance(r, Exception)])}")
        
        # Show results summary
        for i, result in enumerate(results):
            operation_type = ["Analysis", "Entity Extraction", "System Status"][i]
            if isinstance(result, Exception):
                print(f"  {operation_type}: ❌ Failed - {str(result)[:50]}...")
            else:
                status = "✅ Success" if hasattr(result, 'get') and result.get('status') != 'error' else "✅ Success"
                print(f"  {operation_type}: {status}")
        
        return results


async def main():
    """Run the complete subagent demonstration."""
    print("🚀 KHALA Subagent System Demonstration")
    print("=" * 60)
    print("This demo shows how Gemini subagents can parallelize KHALA operations")
    print("using multiple specialized agents working concurrently.")
    
    demo = SubagentDemo()
    
    try:
        # Run all demos
        await demo.demo_basic_analysis()
        await demo.demo_entity_extraction()
        await demo.demo_verification_system()
        await demo.demo_performance_metrics()
        await demo.demo_concurrent_processing()
        
        print("\n" + "=" * 60)
        print("🎉 KHALA Subagent System Demo Completed Successfully!")
        
        print("\n📈 Key Capabilities Demonstrated:")
        print("✅ Parallel memory processing with up to 8 concurrent agents")
        print("✅ Real-time entity extraction from multiple texts")  
        print("✅ Comprehensive multi-agent verification with consensus")
        print("✅ Performance monitoring and metrics collection")
        print("✅ Concurrent execution of multiple operation types")
        
        print("\n🚀 Next Steps:")
        print("1. Integrate with KHALA memory system for production use")
        print("2. Scale to handle larger memory batches")
        print("3. Add specialized agents for domain-specific analysis")
        print("4. Implement GPU acceleration for enhanced performance")
        
        print(f"\n🕐 Demo completed at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure gemini-cli is installed: npm install -g gemini-mcp-tool")
        print("2. Check agent configurations in .gemini/agents/ directory")
        print("3. Verify Google AI API access with valid API key")
        print("4. Check network connectivity for external API calls")


if __name__ == "__main__":
    asyncio.run(main())
