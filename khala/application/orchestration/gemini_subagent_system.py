"""
Gemini Subagent System for KHALA.

Implements parallel task delegation using gemini-3-pro-preview subagents
for concurrent memory processing, verification, and analysis.
"""

import asyncio
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import logging

from ...domain.memory.entities import Memory, Entity, Relationship
from ...domain.search.value_objects import SearchIntent, SignificanceScore
from .executor import SubagentExecutor
from .types import SubagentTask, SubagentResult, SubagentRole, TaskPriority, ModelTier

logger = logging.getLogger(__name__)


class GeminiSubagentSystem:
    """Main coordinator for Gemini subagent system."""
    
    def __init__(self, max_concurrent_agents: int = 8, executor: Optional[SubagentExecutor] = None):
        self.max_concurrent_agents = max_concurrent_agents
        self.agent_configs = self._load_agent_configs()
        self.active_tasks: Dict[str, SubagentTask] = {}
        self.completed_tasks: Dict[str, SubagentResult] = {}
        self.task_queue: List[SubagentTask] = []
        self.performance_metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "avg_execution_time_ms": 0.0,
            "agents_utilized": 0
        }
        
        if executor:
            self.executor = executor
        else:
            # Lazy import to avoid circular dependency if possible, or just standard import
            from ...infrastructure.executors.cli_executor import CLISubagentExecutor
            self.executor = CLISubagentExecutor()
    
    def _load_agent_configs(self) -> Dict[SubagentRole, Dict]:
        """Load agent configurations from .gemini folder."""
        configs = {}
        
        base_config = {
            "model": "gemini-3-pro-preview",
            "temperature": 0.7,
            "timeout": 60,
            "tools": ["gemini-cli"]
        }
        
        role_specific_configs = {
            SubagentRole.ANALYZER: {
                **base_config,
                "temperature": 0.3,
                "focus": "detailed analysis, data validation, pattern identification"
            },
            SubagentRole.SYNTHESIZER: {
                **base_config,
                "temperature": 0.5,
                "focus": "information synthesis, conflict resolution, consensus building"
            },
            SubagentRole.CURATOR: {
                **base_config,
                "temperature": 0.4,
                "focus": "quality control, fact-checking, trustworthiness assessment"
            },
            SubagentRole.RESEARCHER: {
                **base_config,
                "temperature": 0.2,
                "focus": "deep research, external verification, source validation"
            },
            SubagentRole.VALIDATOR: {
                **base_config,
                "temperature": 0.1,
                "focus": "validation, testing, verification"
            },
            SubagentRole.CONSOLIDATOR: {
                **base_config,
                "temperature": 0.3,
                "focus": "consolidation, deduplication, merging"
            },
            SubagentRole.EXTRACTOR: {
                **base_config,
                "temperature": 0.4,
                "focus": "entity extraction, pattern recognition, metadata generation"
            },
            SubagentRole.OPTIMIZER: {
                **base_config,
                "temperature": 0.6,
                "focus": "performance optimization, cost reduction, efficiency"
            }
        }
        
        return role_specific_configs

    # _get_model_for_tier removed (moved to executor)
    
    async def submit_task(self, task: SubagentTask) -> str:
        """Submit a task to the subagent system."""
        self.task_queue.append(task)
        logger.info(f"Task submitted: {task.task_id} ({task.role.value})")
        
        # Try to process queue immediately
        await self._process_queue()
        
        return task.task_id
    
    async def get_result(self, task_id: str, timeout_ms: int = 30000) -> Optional[SubagentResult]:
        """Get result of a specific task with timeout."""
        start_time = time.time()
        timeout_seconds = timeout_ms / 1000
        
        while task_id not in self.completed_tasks:
            if time.time() - start_time > timeout_seconds:
                return None
            
            # Check if task is still in queue
            queued_task = next((t for t in self.task_queue if t.task_id == task_id), None)
            if queued_task is None:
                return None  # Task was lost
            
            await asyncio.sleep(0.1)
            await self._process_queue()
        
        return self.completed_tasks[task_id]
    
    async def submit_batch_tasks(self, tasks: List[SubagentTask]) -> List[str]:
        """Submit multiple tasks for concurrent processing."""
        task_ids = []
        
        for task in tasks:
            task_id = await self.submit_task(task)
            task_ids.append(task_id)
        
        return task_ids
    
    async def wait_for_batch_results(self, task_ids: List[str], timeout_ms: int = 60000) -> List[SubagentResult]:
        """Wait for completion of multiple tasks."""
        results = []
        timeout_seconds = timeout_ms / 1000
        start_time = time.time()
        
        while len(results) < len(task_ids):
            if time.time() - start_time > timeout_seconds:
                # Add timeout indicators for incomplete tasks
                for task_id in task_ids:
                    if task_id not in [r.task_id for r in results]:
                        timeout_result = SubagentResult(
                            task_id=task_id,
                            role=SubagentRole.ANALYZER,  # Default
                            success=False,
                            output=None,
                            reasoning="Task timed out",
                            confidence_score=0.0,
                            execution_time_ms=timeout_ms,
                            error="Timeout"
                        )
                        results.append(timeout_result)
                break
            
            # Collect completed results
            completed_results = [
                self.completed_tasks[task_id] 
                for task_id in task_ids 
                if task_id in self.completed_tasks and 
                   task_id not in [r.task_id for r in results]
            ]
            results.extend(completed_results)
            
            if len(results) < len(task_ids):
                await asyncio.sleep(0.5)
                await self._process_queue()
        
        return results
    
    async def _process_queue(self):
        """Process task queue with concurrent execution."""
        # Determine how many tasks we can process concurrently
        available_slots = self.max_concurrent_agents - len(self.active_tasks)
        
        if available_slots <= 0 or not self.task_queue:
            return
        
        # Get tasks by priority
        prioritized_tasks = sorted(
            self.task_queue, 
            key=lambda t: (t.priority.value, t.created_at), 
            reverse=True
        )
        
        tasks_to_execute = prioritized_tasks[:available_slots]
        
        # Execute tasks concurrently
        execution_tasks = []
        for task in tasks_to_execute:
            self.task_queue.remove(task)
            self.active_tasks[task.task_id] = task
            execution_tasks.append(self._execute_task(task))
        
        # Execute and handle results
        if execution_tasks:
            results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    # Handle exception results
                    failed_task = SubagentResult(
                        task_id="unknown",
                        role=SubagentRole.ANALYZER,
                        success=False,
                        output=None,
                        reasoning=f"Execution failed: {str(result)}",
                        confidence_score=0.0,
                        execution_time_ms=0,
                        error=str(result)
                    )
                    self._handle_task_completion(failed_task)
                else:
                    self._handle_task_completion(result)
    
    async def _execute_task(self, task: SubagentTask) -> SubagentResult:
        """Execute a single task using the configured executor."""
        agent_config = self.agent_configs[task.role]
        return await self.executor.execute_task(task, agent_config)
    
    # _get_agent_file and _get_model_for_tier removed (moved to executor)
    
    def _handle_task_completion(self, result: SubagentResult):
        """Handle task completion and metrics update."""
        if result.task_id in self.active_tasks:
            del self.active_tasks[result.task_id]
        
        self.completed_tasks[result.task_id] = result
        
        # Update performance metrics
        self.performance_metrics["total_tasks"] += 1
        if result.success:
            self.performance_metrics["successful_tasks"] += 1
        else:
            self.performance_metrics["failed_tasks"] += 1
        
        # Update average execution time
        total_time = self.performance_metrics["avg_execution_time_ms"] * (self.performance_metrics["total_tasks"] - 1)
        total_time += result.execution_time_ms
        self.performance_metrics["avg_execution_time_ms"] = total_time / self.performance_metrics["total_tasks"]
        
        logger.info(f"Task completed: {result.task_id} ({'SUCCESS' if result.success else 'FAILED'}) in {result.execution_time_ms:.0f}ms")
    
    async def analyze_memory_batch(self, memories: List[Memory]) -> List[SubagentResult]:
        """Analyze a batch of memories in parallel."""
        tasks = []
        
        for memory in memories:
            # Create analyzer task
            task = SubagentTask(
                task_id=f"analyze_memory_{memory.id[:8]}_{str(uuid.uuid4())[:4]}",
                role=SubagentRole.ANALYZER,
                priority=TaskPriority.HIGH,
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
                    "operation": "batch_memory_analysis",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                expected_output="structured_analysis"
            )
            tasks.append(task)
        
        # Submit and wait for results
        task_ids = await self.submit_batch_tasks(tasks)
        results = await self.wait_for_batch_results(task_ids, timeout_ms=120000)
        
        return results
    
    async def extract_entities_batch(self, memories: List[Memory]) -> List[SubagentResult]:
        """Extract entities from memories in parallel."""
        tasks = []
        
        for memory in memories:
            task = SubagentTask(
                task_id=f"extract_entities_{memory.id[:8]}_{str(uuid.uuid4())[:4]}",
                role=SubagentRole.EXTRACTOR,
                priority=TaskPriority.MEDIUM,
                task_type="entity_extraction",
                input_data={
                    "memory_content": memory.content,
                    "memory_id": memory.id
                },
                context={
                    "operation": "ner_extraction",
                    "entity_types": ["person", "tool", "concept", "place", "event"]
                }
            )
            tasks.append(task)
        
        task_ids = await self.submit_batch_tasks(tasks)
        results = await self.wait_for_batch_results(task_ids, timeout_ms=90000)
        
        return results
    
    async def consolidate_memories(self, memory_groups: List[List[Memory]]) -> List[SubagentResult]:
        """Consolidate similar memories in parallel."""
        tasks = []
        
        for i, group in enumerate(memory_groups):
            task = SubagentTask(
                task_id=f"consolidate_group_{i}_{str(uuid.uuid4())[:4]}",
                role=SubagentRole.CONSOLIDATOR,
                priority=TaskPriority.MEDIUM,
                task_type="memory_consolidation",
                input_data={
                    "memories": [
                        {
                            "id": mem.id,
                            "content": mem.content,
                            "importance": mem.importance.value,
                            "tags": mem.tags
                        } for mem in group
                    ]
                },
                context={
                    "operation": "semantic_consolidation",
                    "group_index": i
                }
            )
            tasks.append(task)
        
        task_ids = await self.submit_batch_tasks(tasks)
        results = await self.wait_for_batch_results(task_ids, timeout_ms=180000)
        
        return results
    
    async def verify_memories(self, memories: List[Memory]) -> List[SubagentResult]:
        """Verify memories using multi-agent consensus."""
        # Create tasks for each memory with multiple roles
        all_tasks = []
        
        for memory in memories:
            # Analyzer
            tasks.append(SubagentTask(
                task_id=f"verify_analyze_{memory.id[:8]}_{str(uuid.uuid4())[:4]}",
                role=SubagentRole.ANALYZER,
                priority=TaskPriority.HIGH,
                task_type="memory_verification",
                input_data={"memory_content": memory.content, "memory_id": memory.id},
                context={"verification_check": "factual_accuracy"}
            ))
            
            # Researcher
            tasks.append(SubagentTask(
                task_id=f"verify_research_{memory.id[:8]}_{str(uuid.uuid4())[:4]}",
                role=SubagentRole.RESEARCHER,
                priority=TaskPriority.HIGH,
                task_type="memory_verification",
                input_data={"memory_content": memory.content, "memory_id": memory.id},
                context={"verification_check": "source_validation"}
            ))
            
            # Curator
            tasks.append(SubagentTask(
                task_id=f"verify_curate_{memory.id[:8]}_{str(uuid.uuid4())[:4]}",
                role=SubagentRole.CURATOR,
                priority=TaskPriority.HIGH,
                task_type="memory_verification",
                input_data={"memory_content": memory.content, "memory_id": memory.id},
                context={"verification_check": "quality_assessment"}
            ))
        
        # Execute all verification tasks
        task_ids = await self.submit_batch_tasks(all_tasks)
        results = await self.wait_for_batch_results(task_ids, timeout_ms=300000)
        
        return results

    async def verify_memories_with_consensus(self, memories: List[Memory]) -> Dict[str, Any]:
        """
        Verify memories and calculate consensus scores.
        Returns a structured report with consensus data.
        """
        raw_results = await self.verify_memories(memories)
        
        # Group results by memory ID
        verification_by_memory = {}
        for result in raw_results:
            # Use metadata for reliable ID extraction
            memory_id = result.metadata.get("memory_id", "unknown")
                
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
        
        # Calculate consensus
        verification_consensus = {}
        for memory_id, agent_results in verification_by_memory.items():
            successful_agents = [r for r in agent_results.values() if r["success"]]
            
            if successful_agents:
                avg_confidence = sum(r["confidence"] for r in successful_agents) / len(successful_agents)
                # Simple consensus: % of agents with high confidence (>0.7)
                high_confidence_count = sum(1 for r in successful_agents if r["confidence"] > 0.7)
                consensus_score = high_confidence_count / len(successful_agents)
                
                verification_consensus[memory_id] = {
                    "overall_confidence": avg_confidence,
                    "consensus_score": consensus_score,
                    "agent_count": len(successful_agents),
                    "agent_results": agent_results,
                    "recommendation": "accept" if consensus_score >= 0.8 else "review" if consensus_score >= 0.5 else "reject"
                }
            else:
                verification_consensus[memory_id] = {
                    "overall_confidence": 0.0,
                    "consensus_score": 0.0,
                    "agent_count": 0,
                    "recommendation": "reject",
                    "error": "No successful verifications"
                }
                
        return {
            "status": "completed",
            "memories_verified": len(verification_consensus),
            "results": verification_consensus
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        return {
            **self.performance_metrics,
            "active_tasks": len(self.active_tasks),
            "queued_tasks": len(self.task_queue),
            "completed_available": len(self.completed_tasks),
            "success_rate": (self.performance_metrics["successful_tasks"] / 
                          max(1, self.performance_metrics["total_tasks"])) * 100,
            "current_time": datetime.now(timezone.utc).isoformat()
        }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get detailed status of a specific task."""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "status": "active",
                "task": asdict(task),
                "started_at": task.created_at.isoformat()
            }
        elif task_id in self.completed_tasks:
            result = self.completed_tasks[task_id]
            return {
                "status": "completed",
                "result": asdict(result),
                "completed_at": result.completed_at.isoformat()
            }
        else:
            # Check if in queue
            queued_task = next((t for t in self.task_queue if t.task_id == task_id), None)
            if queued_task:
                return {
                    "status": "queued",
                    "task": asdict(queued_task),
                    "queued_at": queued_task.created_at.isoformat()
                }
            else:
                return {"status": "not_found"}


# Factory function for easy initialization
def create_subagent_system(max_concurrent_agents: int = 8) -> GeminiSubagentSystem:
    """Create a configured Gemini subagent system."""
    return GeminiSubagentSystem(max_concurrent_agents)
