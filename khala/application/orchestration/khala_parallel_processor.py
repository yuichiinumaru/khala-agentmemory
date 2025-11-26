"""
KHALA Parallel Memory Processing System.

Demonstrates the use of Gemini subagents for parallel memory processing,
verification, and analysis operations.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from .gemini_subagent_system import GeminiSubagentSystem, SubagentRole, TaskPriority, SubagentTask
from ...domain.memory.entities import Memory, MemoryTier
from ...domain.memory.value_objects import ImportanceScore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KHALAParallelProcessor:
    """High-level interface for parallel KHALA operations."""
    
    def __init__(self, max_concurrent_agents: int = 6):
        """Initialize the parallel processor."""
        self.subagent_system = create_subagent_system(max_concurrent_agents)
        self.processed_metrics = {
            "memories_analyzed": 0,
            "entities_extracted": 0,
            "memories_consolidated": 0,
            "verification_tasks": 0
        }
    
    async def process_memory_batch(self, memories: List[Memory], operations: List[str]) -> Dict[str, Any]:
        """Process a batch of memories with specified operations."""
        logger.info(f"Starting parallel processing of {len(memories)} memories")
        start_time = datetime.now(timezone.utc)
        
        results = {}
        
        # Memory Analysis
        if "analysis" in operations:
            logger.info("Starting memory analysis...")
            analysis_results = await self.subagent_system.analyze_memory_batch(memories)
            results["analysis"] = {
                "results": analysis_results,
                "success_rate": sum(1 for r in analysis_results if r.success) / len(analysis_results),
                "avg_confidence": sum(r.confidence_score for r in analysis_results) / len(analysis_results)
            }
            self.processed_metrics["memories_analyzed"] += len(memories)
        
        # Entity Extraction
        if "entity_extraction" in operations:
            logger.info("Starting entity extraction...")
            entity_results = await self.subagent_system.extract_entities_batch(memories)
            results["entity_extraction"] = {
                "results": entity_results,
                "success_rate": sum(1 for r in entity_results if r.success) / len(entity_results),
                "avg_confidence": sum(r.confidence_score for r in entity_results) / len(entity_results)
            }
            self.processed_metrics["entities_extracted"] += len(memories)
        
        # Memory Consolidation (group similar memories)
        if "consolidation" in operations and len(memories) > 1:
            logger.info("Starting memory consolidation...")
            # Simple grouping by content similarity for demo
            memory_groups = self._group_memories_for_consolidation(memories)
            consolidation_results = await self.subagent_system.consolidate_memories(memory_groups)
            results["consolidation"] = {
                "results": consolidation_results,
                "success_rate": sum(1 for r in consolidation_results if r.success) / len(consolidation_results),
                "groups_processed": len(memory_groups)
            }
            self.processed_metrics["memories_consolidated"] += len(memory_groups)
        
        # Multi-Agent Verification
        if "verification" in operations:
            logger.info("Starting multi-agent verification...")
            verification_results = await self.subagent_system.verify_memories(memories[:min(3, len(memories))])  # Limit for demo
            results["verification"] = {
                "results": verification_results,
                "success_rate": sum(1 for r in verification_results if r.success) / len(verification_results),
                "verification_tasks": len(verification_results)
            }
            self.processed_metrics["verification_tasks"] += len(verification_results)
        
        # Calculate processing summary
        end_time = datetime.now(timezone.utc)
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        results["summary"] = {
            "total_memories": len(memories),
            "operations_completed": list(results.keys()),
            "processing_time_ms": processing_time_ms,
            "avg_time_per_memory_ms": processing_time_ms / len(memories),
            "subagent_metrics": self.subagent_system.get_performance_metrics(),
            "processed_metrics": self.processed_metrics
        }
        
        logger.info(f"Parallel processing completed in {processing_time_ms:.0f}ms")
        
        return results
    
    def _group_memories_for_consolidation(self, memories: List[Memory], group_size: int = 3) -> List[List[Memory]]:
        """Simple grouping for consolidation demonstration."""
        groups = []
        for i in range(0, len(memories), group_size):
            group = memories[i:i+group_size]
            if len(group) > 1:  # Only group with 2+ memories
                groups.append(group)
        return groups


async def demo_parallel_processing():
    """Demonstrate the parallel processing capabilities."""
    print("🚀 KHALA Parallel Processing Demo")
    print("=" * 50)
    
    # Create sample memories
    sample_memories = [
        Memory(
            user_id="demo_user",
            content="Machine learning models utilize statistical patterns to make predictions.",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.high()
        ),
        Memory(
            user_id="demo_user", 
            content="Neural networks learn through backpropagation algorithms.",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.high()
        ),
        Memory(
            user_id="demo_user",
            content="Deep learning architectures include CNNs, RNNs, and Transformers.",
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore.medium()
        ),
        Memory(
            user_id="demo_user",
            content="Data preprocessing is crucial for model performance.",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium()
        )
    ]
    
    # Initialize parallel processor
    processor = KHALAParallelProcessor(max_concurrent_agents=4)
    
    # Process with multiple operations
    operations = ["analysis", "entity_extraction"]
    if len(sample_memories) >= 2:
        operations.append("consolidation")
    
    results = await processor.process_memory_batch(sample_memories, operations)
    
    # Display results
    print("\n📊 Results Summary:")
    print(f"Total memories processed: {results['summary']['total_memories']}")
    print(f"Operations completed: {', '.join(results['summary']['operations_completed'])}")
    print(f"Processing time: {results['summary']['processing_time_ms']:.0f}ms")
    print(f"Avg time per memory: {results['summary']['avg_time_per_memory_ms']:.0f}ms")
    
    for op_name, op_result in results.items():
        if op_name != "summary":
            print(f"\n🔍 {op_name.title()}:")
            print(f"  Success rate: {op_result['success_rate']:.1%}")
            print(f"  Avg confidence: {op_result['avg_confidence']:.1%}")
            if "groups_processed" in op_result:
                print(f"  Groups processed: {op_result['groups_processed']}")
    
    print(f"\n🎯 Subagent System Metrics:")
    metrics = results['summary']['subagent_metrics']
    print(f"  Total tasks: {metrics['total_tasks']}")
    print(f"  Success rate: {metrics['success_rate']:.1%}")
    print(f"  Avg execution time: {metrics['avg_execution_time_ms']:.0f}ms")
    print(f"  Active tasks: {metrics['active_tasks']}")
    
    # Show detailed results for first operation
    if results:
        first_op = next(iter(results.keys()))
        if first_op != "summary" and results[first_op]["results"]:
            print(f"\n📋 Detailed {first_op} results (first 2):")
            for i, result in enumerate(results[first_op]["results"][:2]):
                print(f"  Task {i+1}:")
                print(f"    ID: {result.task_id}")
                print(f"    Success: {'✅' if result.success else '❌'}")
                print(f"    Confidence: {result.confidence_score:.2f}")
                print(f"    Execution time: {result.execution_time_ms:.0f}ms")
                if result.reasoning:
                    reasoning_preview = result.reasoning[:100] + "..." if len(result.reasoning) > 100 else result.reasoning
                    print(f"    Reasoning: {reasoning_preview}")
    
    return results


async def demo_advanced_verification():
    """Demonstrate advanced multi-agent verification."""
    print("\n🔐 Advanced Multi-Agent Verification Demo")
    print("=" * 50)
    
    # Create a complex memory for verification
    complex_memory = Memory(
        user_id="verification_demo",
        content="The Transformer architecture revolutionized NLP with its self-attention mechanism, enabling parallel processing and capturing long-range dependencies without recurrence.",
        tier=MemoryTier.SHORT_TERM,
        importance=ImportanceScore.very_high()
    )
    
    # Create processor with more agents for verification
    verifier = KHALAParallelProcessor(max_concurrent_agents=6)
    
    # Run verification
    verification_results = await verifier.subagent_system.verify_memories([complex_memory])
    
    print(f"🔍 Verification Analysis ({len(verification_results)} agent insights):")
    
    # Group results by agent role
    by_role = {}
    for result in verification_results:
        role = result.role.value
        if role not in by_role:
            by_role[role] = []
        by_role[role].append(result)
    
    agent_descriptions = {
        "analyzer": "🔬 Detailed factual analysis",
        "researcher": "📚 External source verification", 
        "curator": "🎯 Quality and trustworthiness assessment"
    }
    
    for role, results_list in by_role.items():
        print(f"\n{agent_descriptions.get(role, f'🤖 {role.title()}')}:")
        for result in results_list:
            print(f"  Status: {'✅ Success' if result.success else '❌ Failed'}")
            print(f"  Confidence: {result.confidence_score:.2f}")
            print(f"  Time: {result.execution_time_ms:.0f}ms")
            if result.reasoning:
                preview = result.reasoning[:150] + "..." if len(result.reasoning) > 150 else result.reasoning
                print(f"  Analysis: {preview}")
    
    # Calculate overall verification score
    successful_results = [r for r in verification_results if r.success]
    if successful_results:
        avg_confidence = sum(r.confidence_score for r in successful_results) / len(successful_results)
        consensus_score = min(
            len([r for r in successful_results if r.confidence_score > 0.7]) / len(successful_results),
            1.0
        )
        
        print(f"\n📊 Verification Summary:")
        print(f"  Overall confidence: {avg_confidence:.2f}")
        print(f"  Consensus score: {consensus_score:.2f}")
        print(f"  Success rate: {len(successful_results)}/{len(verification_results)} ({len(successful_results)/len(verification_results):.1%})")
        
        if consensus_score >= 0.8:
            print(f"  Recommendation: ✅ ACCEPT (High consensus)")
        elif consensus_score >= 0.6:
            print(f"  Recommendation: ⚠️ REVIEW (Moderate consensus)")
        else:
            print(f"  Recommendation: ❌ REJECT (Low consensus)")
    
    return verification_results


async def main():
    """Main demonstration function."""
    try:
        # Demo 1: Basic Parallel Processing
        results1 = await demo_parallel_processing()
        
        # Demo 2: Advanced Verification  
        results2 = await demo_advanced_verification()
        
        print("\n🎉 Demo completed successfully!")
        print("Key capabilities demonstrated:")
        print("• Parallel memory processing with multiple subagent types")
        print("• Concurrent analysis, entity extraction, and consolidation") 
        print("• Multi-agent verification with consensus building")
        print("• Real-time performance metrics and monitoring")
        print("\nReady for integration with KHALA memory system!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        print("This demo requires gemini-cli to be properly installed and configured.")


if __name__ == "__main__":
    asyncio.run(main())
