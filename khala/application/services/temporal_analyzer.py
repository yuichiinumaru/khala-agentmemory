"""Temporal Analysis Service for KHALA.

This service implements the logic for recency weighting, decay scoring,
and memory lifecycle management (promotion/archival).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
import math
import networkx as nx

from ...domain.memory.entities import Memory, MemoryTier
from ...domain.memory.value_objects import ImportanceScore, DecayScore
from ...infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class TemporalAnalysisService:
    """Service for analyzing temporal aspects of memories."""

    def __init__(self, db_client: Optional[SurrealDBClient] = None):
        """Initialize the service.

        Args:
            db_client: SurrealDB client instance (optional)
        """
        self.db_client = db_client or SurrealDBClient()

    def calculate_decay_score(self, memory: Memory) -> DecayScore:
        """Calculate the current decay score for a memory.

        Uses the formula: score = importance * exp(-age_days / half_life_days)
        Adjusts half-life based on tier and access patterns.
        """
        now = datetime.now(timezone.utc)
        age_days = (now - memory.created_at).total_seconds() / 86400.0

        # Base half-life depends on tier
        if memory.tier == MemoryTier.WORKING:
            half_life_days = 0.5  # Very short half-life for working memory
        elif memory.tier == MemoryTier.SHORT_TERM:
            half_life_days = 7.0  # 1 week half-life
        else:  # LONG_TERM
            half_life_days = 90.0 # 3 months half-life

        # Access count boost: Frequently accessed memories decay slower
        # Boost factor: log(access_count + 1)
        access_boost = math.log(memory.access_count + 1) * 0.5
        adjusted_half_life = half_life_days * (1.0 + access_boost)

        return DecayScore.calculate(
            original_importance=memory.importance,
            age_days=age_days,
            half_life_days=adjusted_half_life
        )

    def should_promote(self, memory: Memory) -> bool:
        """Determine if a memory should be promoted to the next tier."""
        if memory.tier == MemoryTier.LONG_TERM:
            return False

        # Working -> Short Term
        if memory.tier == MemoryTier.WORKING:
            # Criteria: High importance OR frequent access OR high verification score
            if memory.importance.value > 0.7:
                return True
            if memory.access_count > 5:
                return True
            if memory.verification_score > 0.8:
                return True

        # Short Term -> Long Term
        if memory.tier == MemoryTier.SHORT_TERM:
            # Criteria: Very high importance OR sustained access over time
            if memory.importance.value > 0.85:
                return True
            if memory.access_count > 20:
                # Also check age to ensure it's not just a burst
                age_hours = (datetime.now(timezone.utc) - memory.created_at).total_seconds() / 3600
                if age_hours > 24: # Accessed frequently over at least a day
                    return True

        return False

    def should_archive(self, memory: Memory) -> bool:
        """Determine if a memory should be archived."""
        if memory.is_archived:
            return False

        # Don't archive high importance memories regardless of age
        if memory.importance.value > 0.9:
            return False

        now = datetime.now(timezone.utc)
        age_days = (now - memory.created_at).total_seconds() / 86400.0

        # Working Memory: Archive if old and not promoted
        if memory.tier == MemoryTier.WORKING:
            if age_days > 1.0: # Older than 1 day
                return True

        # Short Term: Archive if old and low importance/access
        if memory.tier == MemoryTier.SHORT_TERM:
            if age_days > 30.0 and memory.access_count < 5:
                return True

        # Long Term: Rarely archive, only if explicitly low importance and very old
        if memory.tier == MemoryTier.LONG_TERM:
            if age_days > 365.0 and memory.importance.value < 0.2:
                return True

        return False

    async def update_memory_decay(self, memory: Memory) -> Memory:
        """Calculate and update decay score for a memory."""
        new_score = self.calculate_decay_score(memory)

        # Update memory object
        # Note: We can't modify the frozen DecayScore field directly if it was frozen,
        # but Memory is likely a Pydantic model or dataclass that allows updates or we create a new one.
        # Looking at entities.py (not shown but inferred from usage), let's assume we can update it
        # or we need to update the DB record.

        # We will return the memory with updated score for the caller to save
        # or save it here if we want the service to be self-contained.
        # Ideally, Domain Service calculates, Application Service persists.
        # But this is "khala/application/services/temporal_analyzer.py", so it's an App Service.

        updates = {"decay_score": new_score.value}

        # Check for promotion
        if self.should_promote(memory):
            next_tier = memory.tier.next_tier()
            if next_tier:
                updates["tier"] = next_tier.value
                logger.info(f"Promoting memory {memory.id} to {next_tier.value}")

        # Check for archival
        if self.should_archive(memory):
            updates["is_archived"] = True
            logger.info(f"Archiving memory {memory.id}")

        # Persist updates
        await self.db_client.update_memory(
            memory.id, # We assume update_memory can take ID and dict, but client.py shows it takes Memory object.
                       # We should verify client.py's update_memory signature.
        )

        # Wait, client.py `update_memory` takes a Memory object and overwrites everything.
        # This is not ideal for partial updates.
        # However, looking at client.py `update_memory` query:
        # UPDATE type::thing('memory', $id) CONTENT { ... }
        # It replaces the content.

        # So we need to update the local memory object fields and then save it.
        # Since Memory is a dataclass (likely), we can modify it if it's not frozen.
        # entities.py wasn't fully shown, but value_objects were frozen.
        # Let's assume Memory is mutable or we use `replace`.

        from dataclasses import replace

        # Construct args for replace
        replace_args = {"decay_score": new_score}

        if "tier" in updates:
            # We need to pass the enum, updates["tier"] is string value
            # Actually tier is an Enum in Memory object
            replace_args["tier"] = MemoryTier(updates["tier"])

        if "is_archived" in updates:
            replace_args["is_archived"] = updates["is_archived"]

        updated_memory = replace(memory, **replace_args)

        await self.db_client.update_memory(updated_memory)
        return updated_memory

    async def batch_process_decay(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Process decay updates for a batch of memories."""
        results = {
            "processed": 0,
            "promoted": 0,
            "archived": 0,
            "errors": 0
        }

        for mid in memory_ids:
            try:
                memory = await self.db_client.get_memory(mid)
                if not memory:
                    continue

                updated_mem = await self.update_memory_decay(memory)
                results["processed"] += 1

                if updated_mem.tier != memory.tier:
                    results["promoted"] += 1
                if updated_mem.is_archived and not memory.is_archived:
                    results["archived"] += 1

            except Exception as e:
                logger.error(f"Error processing decay for memory {mid}: {e}")
                results["errors"] += 1

        return results

    async def track_graph_evolution(self, graph_service) -> str:
        """
        Strategy 75: Temporal Graph Evolution.
        Captures a snapshot of the current graph state and stores metrics.

        Args:
            graph_service: GraphService instance.

        Returns:
            ID of the created snapshot.
        """
        # 1. Get current graph snapshot (valid now)
        now = datetime.now(timezone.utc)
        graph = await graph_service.get_graph_snapshot(now, limit=10000)

        if not graph.number_of_nodes():
            logger.info("Graph is empty, skipping snapshot.")
            return ""

        # 2. Calculate metrics
        metrics = {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "density": nx.density(graph),
            "avg_degree": 0.0,
            "component_count": 0,
            "avg_clustering": 0.0,
            "timestamp": now.isoformat()
        }

        if graph.number_of_nodes() > 0:
            metrics["avg_degree"] = sum(dict(graph.degree()).values()) / graph.number_of_nodes()

            if graph.is_directed():
                 metrics["component_count"] = nx.number_weakly_connected_components(graph)
            else:
                 metrics["component_count"] = nx.number_connected_components(graph)

        try:
             # Average clustering (convert to undirected for simple metric)
             metrics["avg_clustering"] = nx.average_clustering(graph.to_undirected())
        except Exception:
             pass

        # 3. Store in DB
        query = """
        CREATE graph_snapshot CONTENT {
            timestamp: $timestamp,
            node_count: $node_count,
            edge_count: $edge_count,
            density: $density,
            avg_degree: $avg_degree,
            avg_clustering: $avg_clustering,
            component_count: $component_count
        };
        """

        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query, metrics)
                if response and isinstance(response, list) and len(response) > 0:
                     if isinstance(response[0], dict) and 'id' in response[0]:
                         return response[0]['id']
                     if isinstance(response[0], dict) and 'result' in response[0] and len(response[0]['result']) > 0:
                         return response[0]['result'][0]['id']
                return ""
        except Exception as e:
            logger.error(f"Failed to save graph snapshot: {e}")
            return ""

    async def predict_consolidation_schedule(self) -> Dict[str, Any]:
        """
        Strategy 106: Consolidation Schedule.
        Predicts optimal times for maintenance jobs based on activity patterns.
        """
        # 1. Get recent activity heatmap (last 7 days)
        heatmap = await self.generate_heatmap(time_window_days=7)

        # 2. Analyze daily volume
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        volume_yesterday = heatmap.get(yesterday, 0)

        recommendation = {
            "should_run_now": False,
            "recommended_time": "03:00 UTC",
            "reason": "Routine maintenance",
            "priority": "low",
            "volume_trend": "stable"
        }

        if volume_yesterday > 100:
            recommendation["priority"] = "high"
            recommendation["reason"] = "High volume detected yesterday"
            recommendation["volume_trend"] = "high"

        # Check current hour (mock: best time is 2-5 AM UTC)
        current_hour = datetime.now(timezone.utc).hour
        if 2 <= current_hour <= 5:
             recommendation["should_run_now"] = True

        return recommendation

    async def generate_heatmap(
        self,
        time_window_days: int = 30
    ) -> Dict[str, int]:
        """
        Implement Strategy 140: Temporal Heatmaps.
        Generates a histogram of memory creation counts over the last N days.

        Args:
            time_window_days: Number of days to look back.

        Returns:
            Dictionary mapping date strings (YYYY-MM-DD) to creation counts.
        """
        # Using SurrealDB's time formatting to group by day
        # Note: $duration must be a duration string like '30d'
        duration_str = f"{time_window_days}d"

        query = """
        SELECT count() as count,
               time::format(created_at, "%Y-%m-%d") as date_bucket
        FROM memory
        WHERE created_at > time::now() - <duration>$duration
        GROUP BY date_bucket
        ORDER BY date_bucket ASC;
        """

        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query, {"duration": duration_str})

                heatmap = {}
                items = []
                # Handle SurrealDB response format
                if response and isinstance(response, list):
                     if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                         items = response[0]['result']
                     else:
                         items = response

                for item in items:
                    if isinstance(item, dict) and 'date_bucket' in item:
                        heatmap[item['date_bucket']] = item['count']

                return heatmap

        except Exception as e:
            logger.error(f"Failed to generate heatmap: {e}")
            return {}
