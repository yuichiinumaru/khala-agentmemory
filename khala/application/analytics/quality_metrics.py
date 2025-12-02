"""
Quality Metrics and Analytics Service.

Implements tasks 107 (Debate Outcome Trends) and 108 (Learning Curve Tracking).
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import logging

from ...infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class QualityAnalyticsService:
    """Service for analyzing system quality metrics and trends."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def get_debate_trends(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get debate outcome trends (Task 107).

        Args:
            start_date: Start of the analysis period (default: 30 days ago)
            end_date: End of the analysis period (default: now)

        Returns:
            Dictionary containing trend analysis data.
        """
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Format dates for SurrealDB query (ISO 8601)
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        # Query memories with debate consensus within the time range
        # Note: 'debate_consensus' is a dictionary, checking if it is not null
        query = """
        SELECT
            created_at,
            debate_consensus.consensus_score as score,
            debate_consensus.decision as decision,
            debate_consensus.confidence_level as confidence
        FROM memory
        WHERE debate_consensus != NONE
        AND created_at >= $start
        AND created_at <= $end
        ORDER BY created_at ASC;
        """

        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, {"start": start_str, "end": end_str})

            # Handle SurrealDB response structure
            items = []
            if result and isinstance(result, list):
                if isinstance(result[0], dict) and 'result' in result[0]:
                     items = result[0]['result']
                else:
                     items = result

            # Process data for trends
            total_debates = len(items)
            if total_debates == 0:
                return {
                    "period": {"start": start_str, "end": end_str},
                    "total_debates": 0,
                    "trends": []
                }

            # Aggregate by day
            daily_stats = {}
            decisions_count = {}

            for item in items:
                # Parse date
                created_at_str = item.get('created_at')
                if not created_at_str:
                    continue

                # Extract date part (YYYY-MM-DD)
                date_key = created_at_str.split('T')[0]

                if date_key not in daily_stats:
                    daily_stats[date_key] = {
                        "count": 0,
                        "total_score": 0.0,
                        "total_confidence": 0.0,
                        "decisions": {}
                    }

                stats = daily_stats[date_key]
                stats["count"] += 1
                stats["total_score"] += item.get('score', 0.0)
                stats["total_confidence"] += item.get('confidence', 0.0)

                decision = item.get('decision', 'UNKNOWN')
                stats["decisions"][decision] = stats["decisions"].get(decision, 0) + 1
                decisions_count[decision] = decisions_count.get(decision, 0) + 1

            # Format trends list
            trends = []
            sorted_dates = sorted(daily_stats.keys())

            for date_key in sorted_dates:
                stats = daily_stats[date_key]
                count = stats["count"]
                trends.append({
                    "date": date_key,
                    "debates_count": count,
                    "avg_consensus_score": stats["total_score"] / count if count > 0 else 0,
                    "avg_confidence": stats["total_confidence"] / count if count > 0 else 0,
                    "decisions_breakdown": stats["decisions"]
                })

            return {
                "period": {"start": start_str, "end": end_str},
                "total_debates": total_debates,
                "overall_decisions": decisions_count,
                "trends": trends
            }

        except Exception as e:
            logger.error(f"Failed to get debate trends: {e}")
            raise

    async def get_learning_curve(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get learning curve (verification score trends) (Task 108).

        Args:
            start_date: Start of the analysis period (default: 30 days ago)
            end_date: End of the analysis period (default: now)

        Returns:
            Dictionary containing learning curve data.
        """
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        # Query verification scores
        query = """
        SELECT
            created_at,
            verification_score
        FROM memory
        WHERE verification_score > 0
        AND created_at >= $start
        AND created_at <= $end
        ORDER BY created_at ASC;
        """

        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, {"start": start_str, "end": end_str})

            items = []
            if result and isinstance(result, list):
                if isinstance(result[0], dict) and 'result' in result[0]:
                     items = result[0]['result']
                else:
                     items = result

            if not items:
                return {
                    "period": {"start": start_str, "end": end_str},
                    "data_points": 0,
                    "curve": []
                }

            # Aggregate by day
            daily_stats = {}

            for item in items:
                created_at_str = item.get('created_at')
                if not created_at_str:
                    continue

                date_key = created_at_str.split('T')[0]

                if date_key not in daily_stats:
                    daily_stats[date_key] = {"count": 0, "total_score": 0.0}

                daily_stats[date_key]["count"] += 1
                daily_stats[date_key]["total_score"] += item.get('verification_score', 0.0)

            # Calculate moving average or simple daily average
            curve = []
            sorted_dates = sorted(daily_stats.keys())

            cumulative_score = 0.0
            cumulative_count = 0

            for date_key in sorted_dates:
                stats = daily_stats[date_key]
                daily_avg = stats["total_score"] / stats["count"]

                cumulative_score += stats["total_score"]
                cumulative_count += stats["count"]
                running_avg = cumulative_score / cumulative_count

                curve.append({
                    "date": date_key,
                    "daily_avg_score": daily_avg,
                    "running_avg_score": running_avg, # Smoothed learning curve
                    "sample_size": stats["count"]
                })

            return {
                "period": {"start": start_str, "end": end_str},
                "data_points": len(items),
                "curve": curve
            }

        except Exception as e:
            logger.error(f"Failed to get learning curve: {e}")
            raise
