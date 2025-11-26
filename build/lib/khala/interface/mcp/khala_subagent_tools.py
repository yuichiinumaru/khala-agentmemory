"""
KHALA Subagent Tools for MCP Integration.

Provides MCP tools that leverage Gemini subagents for parallel KHALA operations.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from ...application.orchestration.gemini_subagent_system import GeminiSubagentSystem, SubagentRole, TaskPriority, SubagentTask
from ...domain.memory.entities import Memory, MemoryTier
from ...domain.memory.value_objects import ImportanceScore, EmbeddingVector
from ...domain.memory.repository import MemoryRepository


class KHALASubagentTools:
    """MCP tools for KHALA subagent operations."""
    
    def __init__(self, max_concurrent_agents: int = 6, repository: Optional[MemoryRepository] = None):
        """Initialize the subagent tools."""
        self.subagent_system = GeminiSubagentSystem(max_concurrent_agents)
        self.repository = repository
        self.session_stats = {
            "session_start": datetime.now(timezone.utc),
            "tasks_created": 0,
            "tasks_completed": 0,
            "memories_processed": 0
        }
    
    async def analyze_memories_parallel(self, memory_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze multiple memories in parallel using Gemini subagents.
        
        Args:
            memory_data_list: List of memory dictionaries with content, importance, etc.
            
        Returns:
            Analysis results with confidence scores and insights
        """
        try:
            # Convert to Memory entities
            memories = []
            for mem_data in memory_data_list:
                memory = Memory(
                    user_id=mem_data.get("user_id", "mcp_user"),
                    content=mem_data["content"],
                    tier=MemoryTier(mem_data.get("tier", "working")),
                    importance=ImportanceScore(mem_data.get("importance", 0.7))
                )
                memories.append(memory)
            
            # Create analysis tasks
            tasks = []
            for memory in memories:
                task = SubagentTask(
                    task_id=f"mcp_analyze_{memory.id[:8]}_{datetime.now().timestamp()}",
                    role=SubagentRole.ANALYZER,
                    priority=TaskPriority.MEDIUM,
                    task_type="memory_analysis",
                    input_data={
                        "memory_content": memory.content,
                        "memory_id": memory.id,
                        "importance_score": memory.importance.value,
                        "tier": memory.tier.value,
                        "tags": memory.tags,
                        "metadata": memory.metadata
                    },
                    context={
                        "operation": "mcp_parallel_analysis",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "analysis_focus": "content_quality, factuality, structure"
                    }
                )
                tasks.append(task)
            
            # Execute parallel analysis
            task_ids = await self.subagent_system.submit_batch_tasks(tasks)
            results = await self.subagent_system.wait_for_batch_results(task_ids, timeout_ms=120000)
            
            # Update session stats
            self.session_stats["tasks_created"] += len(tasks)
            self.session_stats["tasks_completed"] += len(results)
            self.session_stats["memories_processed"] += len(memories)
            
            # Format results for MCP
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "memory_id": result.task_id.split("_")[2],  # Extract memory ID from task ID
                    "analysis_success": result.success,
                    "confidence_score": result.confidence_score,
                    "execution_time_ms": result.execution_time_ms,
                    "analysis_output": result.output,
                    "reasoning": result.reasoning[:500] if result.reasoning else None,
                    "error": result.error
                })
            
            return {
                "status": "completed",
                "analyzed_memories": len(formatted_results),
                "success_rate": sum(1 for r in formatted_results if r["analysis_success"]) / len(formatted_results),
                "avg_confidence": sum(r["confidence_score"] for r in formatted_results) / len(formatted_results),
                "results": formatted_results,
                "session_stats": self.session_stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "session_stats": self.session_stats
            }
    
    async def extract_entities_batch(self, memory_contents: List[str]) -> Dict[str, Any]:
        """
        Extract entities from multiple memory texts in parallel.
        
        Args:
            memory_contents: List of memory text strings
            
        Returns:
            Extracted entities with confidence scores
        """
        try:
            tasks = []
            for i, content in enumerate(memory_contents):
                task = SubagentTask(
                    task_id=f"mcp_extract_{i}_{datetime.now().timestamp()}",
                    role=SubagentRole.EXTRACTOR,
                    priority=TaskPriority.MEDIUM,
                    task_type="entity_extraction",
                    input_data={
                        "memory_content": content,
                        "content_index": i
                    },
                    context={
                        "operation": "mcp_entity_extraction",
                        "entity_types": ["person", "tool", "concept", "place", "event", "organization"],
                        "confidence_threshold": 0.7
                    }
                )
                tasks.append(task)
            
            # Execute parallel extraction
            task_ids = await self.subagent_system.submit_batch_tasks(tasks)
            results = await self.subagent_system.wait_for_batch_results(task_ids, timeout_ms=90000)
            
            # Format results
            extraction_results = []
            for result in results:
                extraction_results.append({
                    "content_index": result.task_id.split("_")[1],
                    "extraction_success": result.success,
                    "entities": result.output if isinstance(result.output, list) else [],
                    "confidence_score": result.confidence_score,
                    "execution_time_ms": result.execution_time_ms,
                    "reasoning": result.reasoning[:300] if result.reasoning else None,
                    "error": result.error
                })
            
            return {
                "status": "completed",
                "contents_processed": len(extraction_results),
                "success_rate": sum(1 for r in extraction_results if r["extraction_success"]) / len(extraction_results),
                "total_entities_extracted": sum(len(r["entities"]) for r in extraction_results if r["extraction_success"]),
                "results": extraction_results
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def consolidate_memories_smart(self, memory_groups: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Intelligently consolidate similar memories using subagent analysis.
        
        Args:
            memory_groups: Groups of similar memories to consolidate
            
        Returns:
            Consolidation decisions and merged content
        """
        try:
            tasks = []
            for i, group in enumerate(memory_groups):
                task = SubagentTask(
                    task_id=f"mcp_consolidate_{i}_{datetime.now().timestamp()}",
                    role=SubagentRole.CONSOLIDATOR,
                    priority=TaskPriority.LOW,
                    task_type="smart_consolidation",
                    input_data={
                        "memory_group": group,
                        "group_index": i
                    },
                    context={
                        "operation": "mcpSmart_consolidation",
                        "consolidation_strategy": "semantic_merging",
                        "preserve_high_importance": True
                    }
                )
                tasks.append(task)
            
            # Execute parallel consolidation
            task_ids = await self.subagent_system.submit_batch_tasks(tasks)
            results = await self.subagent_system.wait_for_batch_results(task_ids, timeout_ms=180000)
            
            # Format results
            consolidation_results = []
            for result in results:
                consolidation_results.append({
                    "group_index": result.task_id.split("_")[1],
                    "consolidation_success": result.success,
                    "consolidation_decision": result.output if result.output else {},
                    "confidence_score": result.confidence_score,
                    "execution_time_ms": result.execution_time_ms,
                    "reasoning": result.reasoning[:400] if result.reasoning else None,
                    "error": result.error
                })
            
            return {
                "status": "completed",
                "groups_processed": len(consolidation_results),
                "success_rate": sum(1 for r in consolidation_results if r["consolidation_success"]) / len(consolidation_results),
                "recommended_consolidations": sum(1 for r in consolidation_results if r.get("consolidation_decision", {}).get("should_consolidate", False)),
                "results": consolidation_results
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def verify_memories_comprehensive(self, memory_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Comprehensive multi-agent verification of memories.
        
        Args:
            memory_list: List of memory data for verification
            
        Returns:
            Detailed verification results with multi-agent consensus
        """
        try:
            # Limit to reasonable number for demo
            verification_memories = memory_list[:3]
            
            # Create verification tasks with multiple agents per memory
            all_tasks = []
            for memory in verification_memories:
                # Factual analysis
                all_tasks.append(SubagentTask(
                    task_id=f"mcp_verify_fact_{memory.get('id', 'unknown')}_{datetime.now().timestamp()}",
                    role=SubagentRole.ANALYZER,
                    priority=TaskPriority.HIGH,
                    task_type="verification",
                    input_data={"memory_content": memory["content"]},
                    context={"verification_type": "factual_accuracy"}
                ))
                
                # Source validation
                all_tasks.append(SubagentTask(
                    task_id=f"mcp_verify_source_{memory.get('id', 'unknown')}_{datetime.now().timestamp()}",
                    role=SubagentRole.RESEARCHER,
                    priority=TaskPriority.HIGH,
                    task_type="verification",
                    input_data={"memory_content": memory["content"]},
                    context={"verification_type": "source_validation"}
                ))
                
                # Quality assessment
                all_tasks.append(SubagentTask(
                    task_id=f"mcp_verify_quality_{memory.get('id', 'unknown')}_{datetime.now().timestamp()}",
                    role=SubagentRole.CURATOR,
                    priority=TaskPriority.HIGH,
                    task_type="verification",
                    input_data={"memory_content": memory["content"]},
                    context={"verification_type": "quality_assessment"}
                ))
            
            # Execute verification
            task_ids = await self.subagent_system.submit_batch_tasks(all_tasks)
            results = await self.subagent_system.wait_for_batch_results(task_ids, timeout_ms=300000)
            
            # Group results by memory ID
            verification_by_memory = {}
            for result in results:
                # Extract memory ID from task ID
                task_parts = result.task_id.split("_")
                memory_id = "_".join(task_parts[2:-1]) if len(task_parts) > 3 else "unknown"
                agent_role = result.role.value
                
                if memory_id not in verification_by_memory:
                    verification_by_memory[memory_id] = {}
                verification_by_memory[memory_id][agent_role] = {
                    "success": result.success,
                    "confidence": result.confidence_score,
                    "output": result.output,
                    "reasoning": result.reasoning[:300] if result.reasoning else None,
                    "error": result.error
                }
            
            # Calculate consensus scores
            verification_consensus = {}
            for memory_id, agent_results in verification_by_memory.items():
                successful_agents = [result for result in agent_results.values() if result["success"]]
                if successful_agents:
                    avg_confidence = sum(result["confidence"] for result in successful_agents) / len(successful_agents)
                    high_confidence_agents = sum(1 for result in successful_agents if result["confidence"] > 0.7)
                    consensus_score = high_confidence_agents / len(successful_agents)
                    
                    verification_consensus[memory_id] = {
                        "overall_confidence": avg_confidence,
                        "consensus_score": consensus_score,
                        "agent_count": len(successful_agents),
                        "agent_results": agent_results,
                        "recommendation": "accept" if consensus_score >= 0.8 else "review" if consensus_score >= 0.6 else "reject"
                    }
            
            return {
                "status": "completed",
                "memories_verified": len(verification_consensus),
                "avg_consensus_score": sum(r["consensus_score"] for r in verification_consensus.values()) / len(verification_consensus),
                "verification_results": verification_consensus
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e)
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current status and performance metrics."""
        try:
            subagent_metrics = self.subagent_system.get_performance_metrics()
            
            return {
                "system_status": "operational",
                "session_stats": self.session_stats,
                "subagent_metrics": subagent_metrics,
                "available_roles": [role.value for role in SubagentRole],
                "supported_operations": [
                    "analyze_memories_parallel",
                    "extract_entities_batch", 
                    "consolidate_memories_smart",
                    "verify_memories_comprehensive"
                ]
            }
        except Exception as e:
            return {
                "error": str(e)
            }

    async def save_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a memory to the repository."""
        if not self.repository:
            return {"status": "error", "error": "Repository not initialized"}
            
        try:
            memory = Memory(
                user_id=memory_data.get("user_id", "mcp_user"),
                content=memory_data["content"],
                tier=MemoryTier(memory_data.get("tier", "working")),
                importance=ImportanceScore(memory_data.get("importance", 0.5)),
                tags=memory_data.get("tags", []),
                category=memory_data.get("category"),
                metadata=memory_data.get("metadata", {})
            )
            
            memory_id = await self.repository.create(memory)
            return {"status": "success", "memory_id": memory_id}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def search_memories(self, query: str, user_id: str = "mcp_user", limit: int = 5) -> Dict[str, Any]:
        """Search memories using text search."""
        if not self.repository:
            return {"status": "error", "error": "Repository not initialized"}
            
        try:
            results = await self.repository.search_by_text(query, user_id, limit)
            return {
                "status": "success",
                "count": len(results),
                "results": [
                    {
                        "id": m.id,
                        "content": m.content,
                        "score": m.importance.value, # Placeholder for search score
                        "created_at": m.created_at.isoformat()
                    } for m in results
                ]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Export for MCP integration
__all__ = [
    "KHALASubagentTools"
]
