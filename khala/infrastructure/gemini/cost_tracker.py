"""Cost tracking and optimization for Gemini API usage.

This module provides comprehensive cost tracking, optimization recommendations,
and budget management for LLM operations.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
import logging
from decimal import Decimal, ROUND_HALF_UP
import json
import os

from .models import GeminiModel, ModelTier

logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """Record of a single LLM API call and its cost."""
    
    timestamp: datetime
    model_id: str
    model_tier: ModelTier
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: Decimal
    response_time_ms: float
    task_type: str = "unknown"
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate cost record."""
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("Total tokens must equal input + output tokens")
        
        if self.cost_usd < Decimal("0"):
            raise ValueError("Cost cannot be negative")


@dataclass
class CostSummary:
    """Summary of costs for a time period."""
    
    start_time: datetime
    end_time: datetime
    total_cost: Decimal
    total_calls: int
    successful_calls: int
    failed_calls: int
    avg_cost_per_call: Decimal
    avg_tokens_per_call: int
    cost_by_tier: Dict[ModelTier, Decimal] = field(default_factory=dict)
    cost_by_model: Dict[str, Decimal] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100.0


class CostTracker:
    """Cost tracking and optimization system for LLM operations."""
    
    def __init__(self, budget_usd_per_month: Decimal = Decimal("500.00")):
        """Initialize cost tracker.
        
        Args:
            budget_usd_per_month: Monthly budget limit
        """
        self.budget_usd_per_month = budget_usd_per_month
        self.cost_records: List[CostRecord] = []
        self.daily_budget_rolling = Decimal("0")  # Daily spending limit
        self.alert_threshold_percent = Decimal("75.0")  # Alert at 75% of budget

        # Cache for frequent calculations
        self._daily_summary_cache: Optional[Tuple[str, CostSummary]] = None
        self._monthly_summary_cache: Optional[Tuple[str, CostSummary]] = None
        
        # Persistence path
        self.persistence_path = os.path.join(os.path.dirname(__file__), "costs.json")
        self.load_from_file()
    
    def record_call(
        self,
        model: GeminiModel,
        input_tokens: int,
        output_tokens: int,
        response_time_ms: float,
        task_type: str = "unknown",
        success: bool = True,
        error_message: Optional[str] = None
    ) -> CostRecord:
        """Record an LLM API call and calculate its cost.
        
        Args:
            model: The model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            response_time_ms: Response time in milliseconds
            task_type: Type of task (embedding, generation, classification, etc.)
            success: Whether the call was successful
            error_message: Error message if failed
            
        Returns:
            Created cost record
        """
        # Calculate cost
        total_tokens = input_tokens + output_tokens
        cost_usd = (Decimal(total_tokens) / Decimal("1000000")) * Decimal(model.cost_per_million_tokens)
        
        # Round to 8 decimal places
        cost_usd = cost_usd.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        
        # Create and store record
        record = CostRecord(
            timestamp=datetime.now(timezone.utc),
            model_id=model.model_id,
            model_tier=model.tier,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            response_time_ms=response_time_ms,
            task_type=task_type,
            success=success,
            error_message=error_message
        )
        
        self.cost_records.append(record)
        
        # Clear cache entries
        self._daily_summary_cache = None
        self._monthly_summary_cache = None
        
        logger.debug(f"Recorded {task_type} call: {record}")
        
        # Auto-save
        self.save_to_file()
        
        return record
    
    def get_daily_summary(self, day: Optional[date] = None) -> CostSummary:
        """Get cost summary for a specific day."""
        if day is None:
            day = datetime.now(timezone.utc).date()
        
        cache_key = day.isoformat()
        if self._daily_summary_cache and self._daily_summary_cache[0] == cache_key:
            return self._daily_summary_cache[1]
        
        # Filter records for the specified date
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        
        daily_records = [
            record for record in self.cost_records
            if day_start <= record.timestamp < day_end
        ]
        
        if not daily_records:
            summary = CostSummary(
                start_time=day_start,
                end_time=day_end,
                total_cost=Decimal("0"),
                total_calls=0,
                successful_calls=0,
                failed_calls=0,
                avg_cost_per_call=Decimal("0"),
                avg_tokens_per_call=0
            )
        else:
            total_cost = sum(record.cost_usd for record in daily_records)
            total_calls = len(daily_records)
            successful_calls = sum(1 for record in daily_records if record.success)
            failed_calls = total_calls - successful_calls
            total_tokens = sum(record.total_tokens for record in daily_records)
            
            summary = CostSummary(
                start_time=day_start,
                end_time=day_end,
                total_cost=total_cost,
                total_calls=total_calls,
                successful_calls=successful_calls,
                failed_calls=failed_calls,
                avg_cost_per_call=total_cost / total_calls if total_calls > 0 else Decimal("0"),
                avg_tokens_per_call=total_tokens // total_calls if total_calls > 0 else 0
            )
            
            # Calculate cost by tier
            for record in daily_records:
                tier = record.model_tier
                if tier not in summary.cost_by_tier:
                    summary.cost_by_tier[tier] = Decimal("0")
                summary.cost_by_tier[tier] += record.cost_usd
            
            # Calculate cost by model
            for record in daily_records:
                if record.model_id not in summary.cost_by_model:
                    summary.cost_by_model[record.model_id] = Decimal("0")
                summary.cost_by_model[record.model_id] += record.cost_usd
        
        # Cache result
        self._daily_summary_cache = (cache_key, summary)
        return summary
    
    def get_monthly_summary(self, year: Optional[int] = None, month: Optional[int] = None) -> CostSummary:
        """Get cost summary for a specific month."""
        now = datetime.now(timezone.utc)
        if year is None:
            year = now.year
        if month is None:
            month = now.month
        
        cache_key = f"{year}-{month}"
        if self._monthly_summary_cache and self._monthly_summary_cache[0] == cache_key:
            return self._monthly_summary_cache[1]
        
        # Filter records for the specified month
        month_start = datetime(year, month, 1, tzinfo=timezone.utc)
        month_end = month_start.replace(day=28) + timedelta(days=4)  # Get to end of month
        while month_end.month != month:
            month_end -= timedelta(days=1)
        month_end = month_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        monthly_records = [
            record for record in self.cost_records
            if month_start <= record.timestamp <= month_end
        ]
        
        if not monthly_records:
            summary = CostSummary(
                start_time=month_start,
                end_time=month_end,
                total_cost=Decimal("0"),
                total_calls=0,
                successful_calls=0,
                failed_calls=0,
                avg_cost_per_call=Decimal("0"),
                avg_tokens_per_call=0
            )
        else:
            total_cost = sum(record.cost_usd for record in monthly_records)
            total_calls = len(monthly_records)
            successful_calls = sum(1 for record in monthly_records if record.success)
            failed_calls = total_calls - successful_calls
            total_tokens = sum(record.total_tokens for record in monthly_records)
            
            summary = CostSummary(
                start_time=month_start,
                end_time=month_end,
                total_cost=total_cost,
                total_calls=total_calls,
                successful_calls=successful_calls,
                failed_calls=failed_calls,
                avg_cost_per_call=total_cost / total_calls if total_calls > 0 else Decimal("0"),
                avg_tokens_per_call=total_tokens // total_calls if total_calls > 0 else 0
            )
        
        self._monthly_summary_cache = (cache_key, summary)
        return summary
    
    def is_over_budget(self) -> bool:
        """Check if monthly spending has exceeded budget."""
        monthly_summary = self.get_monthly_summary()
        return monthly_summary.total_cost > self.budget_usd_per_month
    
    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status and recommendations."""
        monthly_summary = self.get_monthly_summary()
        
        budget_used_percent = (monthly_summary.total_cost / self.budget_usd_per_month) * Decimal("100")
        budget_usd_used = monthly_summary.total_cost
        budget_usd_remaining = self.budget_usd_per_month - budget_usd_used
        
        days_in_month = (monthly_summary.end_time - monthly_summary.start_time).days
        
        # Calculate predicted monthly cost based on current spending
        days_elapsed = (datetime.now(timezone.utc) - monthly_summary.start_time).days
        if days_elapsed > 0 and days_elapsed < days_in_month:
            avg_daily_rate = budget_usd_used / days_elapsed
            predicted_monthly_cost = avg_daily_rate * days_in_month
        else:
            predicted_monthly_cost = budget_usd_used
        
        # Determine alert level
        if budget_used_percent >= 100:
            alert_level = "critical"
        elif budget_used_percent >= 90:
            alert_level = "warning"
        elif budget_used_percent >= self.alert_threshold_percent:
            alert_level = "caution"
        else:
            alert_level = "normal"
        
        # Optimization recommendations
        recommendations = []
        if alert_level != "normal":
            if monthly_summary.cost_by_tier.get(ModelTier.SMART, Decimal("0")) > budget_usd_used * Decimal("0.5"):
                recommendations.append("Consider using medium or fast tier models more frequently")
            
            if monthly_summary.avg_tokens_per_call > 2000:
                recommendations.append("Optimize prompts to reduce token usage")
            
            if monthly_summary.success_rate < 90:
                recommendations.append("Review error handling to reduce failed calls")
        
        return {
            "budget_used_usd": budget_usd_used,
            "budget_remaining_usd": budget_usd_remaining,
            "budget_used_percent": float(budget_used_percent),
            "predicted_monthly_cost_usd": float(predicted_monthly_cost),
            "alert_level": alert_level,
            "total_calls": monthly_summary.total_calls,
            "avg_cost_per_call": float(monthly_summary.avg_cost_per_call),
            "recommendations": recommendations,
            "tier_breakdown": {
                tier.value: float(cost)
                for tier, cost in monthly_summary.cost_by_tier.items()
            },
            "model_breakdown": {
                model: float(cost)
                for model, cost in monthly_summary.cost_by_model.items()
                if cost > 0
            }
        }
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate optimization recommendations based on usage patterns."""
        monthly_summary = self.get_monthly_summary()
        
        # Analyze tier distribution
        tier_costs = monthly_summary.cost_by_tier
        total_cost = monthly_summary.total_cost
        
        if total_cost == 0:
            return {"message": "No usage data available for optimization"}
        
        # Calculate cost by tier percentages
        tier_percentages = {}
        for tier, cost in tier_costs.items():
            tier_percentages[tier.value] = float((cost / total_cost) * Decimal("100"))
        
        # Identify optimization opportunities
        optimizations = []
        
        # Too much smart tier usage?
        smart_tier_cost = tier_costs.get(ModelTier.SMART, Decimal("0"))
        if smart_tier_cost > total_cost * Decimal("0.5"):
            potential_savings = smart_tier_cost * Decimal("0.67")  # Could save 67% with cascading
            optimizations.append({
                "type": "excessive_smart_usage",
                "current_cost": float(smart_tier_cost),
                "potential_savings": float(potential_savings),
                "recommendation": "Implement cascading to use fast/medium tier models for simple tasks"
            })
        
        # Too many failed calls?
        if monthly_summary.success_rate < 90 and monthly_summary.total_calls > 0:
            failed_cost = monthly_summary.total_cost * (Decimal(monthly_summary.failed_calls) / Decimal(monthly_summary.total_calls))
            optimizations.append({
                "type": "high_failure_rate",
                "current_cost": float(failed_cost),
                "potential_savings": float(failed_cost * Decimal("0.8")),  # Could save 80% of failed costs
                "recommendation": f"Improve error handling (success rate: {monthly_summary.success_rate:.1f}%)"
            })
        
        # High average tokens per call?
        if monthly_summary.avg_tokens_per_call > 1000:
            excess_tokens = (monthly_summary.avg_tokens_per_call - 500) * monthly_summary.total_calls
            potential_savings = (Decimal(excess_tokens) / Decimal("1000000")) * Decimal("15.0")  # Assuming medium tier cost
            optimizations.append({
                "type": "high_token_usage",
                "avg_tokens_per_call": monthly_summary.avg_tokens_per_call,
                "potential_savings": float(potential_savings),
                "recommendation": "Optimize prompts and implement context assembly"
            })
        
        return {
            "tier_percentages": tier_percentages,
            "optimizations": optimizations,
            "total_calls": monthly_summary.total_calls,
            "avg_cost_per_call": float(monthly_summary.avg_cost_per_call),
            "success_rate": monthly_summary.success_rate,
        }
    
    def clear_old_records(self, days_to_keep: int = 90) -> int:
        """Clear records older than specified days.
        
        Args:
            days_to_keep: Number of days of records to keep
            
        Returns:
            Number of records removed
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        original_count = len(self.cost_records)
        
        self.cost_records = [
            record for record in self.cost_records
            if record.timestamp >= cutoff_date
        ]
        
        records_removed = original_count - len(self.cost_records)
        
        # Clear cache
        self._daily_summary_cache = None
        self._monthly_summary_cache = None
        
        logger.info(f"Removed {records_removed} old cost records (kept last {days_to_keep} days)")
        self.save_to_file()
        return records_removed

    def save_to_file(self, path: Optional[str] = None) -> None:
        """Save cost records to JSON file."""
        file_path = path or self.persistence_path
        
        try:
            data = []
            for record in self.cost_records:
                data.append({
                    "timestamp": record.timestamp.isoformat(),
                    "model_id": record.model_id,
                    "model_tier": record.model_tier.value,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "total_tokens": record.total_tokens,
                    "cost_usd": str(record.cost_usd),
                    "response_time_ms": record.response_time_ms,
                    "task_type": record.task_type,
                    "success": record.success,
                    "error_message": record.error_message
                })
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save cost records to {file_path}: {e}")

    def load_from_file(self, path: Optional[str] = None) -> None:
        """Load cost records from JSON file."""
        file_path = path or self.persistence_path
        
        if not os.path.exists(file_path):
            return
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            self.cost_records = []
            for item in data:
                try:
                    record = CostRecord(
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        model_id=item["model_id"],
                        model_tier=ModelTier(item["model_tier"]),
                        input_tokens=item["input_tokens"],
                        output_tokens=item["output_tokens"],
                        total_tokens=item["total_tokens"],
                        cost_usd=Decimal(item["cost_usd"]),
                        response_time_ms=item["response_time_ms"],
                        task_type=item.get("task_type", "unknown"),
                        success=item.get("success", True),
                        error_message=item.get("error_message")
                    )
                    self.cost_records.append(record)
                except Exception as e:
                    logger.warning(f"Skipping invalid cost record: {e}")
                    
            logger.info(f"Loaded {len(self.cost_records)} cost records from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load cost records from {file_path}: {e}")
