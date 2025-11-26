#!/usr/bin/env python3
"""
LLM Cost Dashboard for Khala Project (Task 57).

This script visualizes the cost tracking data stored by the Gemini CostTracker.
It provides a terminal-based dashboard with:
1. Budget status and alerts
2. Cost breakdown by model tier
3. Daily spending trends
4. Optimization recommendations
"""

import os
import sys
import json
from datetime import datetime
from decimal import Decimal
import argparse
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from khala.infrastructure.gemini.cost_tracker import CostTracker
from khala.infrastructure.gemini.models import ModelTier

def format_currency(amount: float) -> str:
    """Format amount as USD currency."""
    return f"${amount:.6f}"

def print_header(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_alert(level: str, message: str):
    """Print an alert with color coding (simulated)."""
    colors = {
        "critical": "\033[91m", # Red
        "warning": "\033[93m",  # Yellow
        "caution": "\033[94m",  # Blue
        "normal": "\033[92m",   # Green
        "reset": "\033[0m"
    }
    
    color = colors.get(level, colors["reset"])
    print(f"{color}[{level.upper()}] {message}{colors['reset']}")

def draw_bar_chart(data: Dict[str, float], title: str, width: int = 40):
    """Draw a simple ASCII bar chart."""
    print(f"\n--- {title} ---")
    
    if not data:
        print("No data available.")
        return
        
    max_val = max(data.values()) if data else 0
    if max_val == 0:
        max_val = 1
        
    for label, value in data.items():
        bar_len = int((value / max_val) * width)
        bar = "█" * bar_len
        print(f"{label:<15} | {bar:<{width}} | {value:.4f}")

def main():
    parser = argparse.ArgumentParser(description="Khala LLM Cost Dashboard")
    parser.add_argument("--budget", type=float, default=50.0, help="Monthly budget in USD")
    parser.add_argument("--days", type=int, default=30, help="Days of history to analyze")
    args = parser.parse_args()
    
    # Initialize tracker
    tracker = CostTracker(budget_usd_per_month=Decimal(str(args.budget)))
    
    # Load data (it loads automatically in __init__ now, but let's be sure)
    # The persistence path is relative to the module, so it should work if the file exists
    
    if not tracker.cost_records:
        print("No cost records found. Run some LLM operations first.")
        return

    # Get status
    status = tracker.get_budget_status()
    report = tracker.get_optimization_report()
    
    # 1. Overview
    print_header("LLM COST DASHBOARD")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Calls: {status['total_calls']}")
    print(f"Avg Cost/Call: {format_currency(status['avg_cost_per_call'])}")
    
    # 2. Budget Status
    print_header("BUDGET STATUS")
    print(f"Budget: {format_currency(args.budget)}")
    print(f"Used:   {format_currency(status['budget_used_usd'])} ({status['budget_used_percent']:.1f}%)")
    print(f"Remaining: {format_currency(status['budget_remaining_usd'])}")
    print(f"Predicted: {format_currency(status['predicted_monthly_cost_usd'])}")
    
    print("\nStatus:")
    print_alert(status['alert_level'], f"Budget usage is {status['alert_level']}")
    
    # 3. Cost Breakdown
    print_header("COST BREAKDOWN")
    
    # Tier breakdown
    tier_data = status.get("tier_breakdown", {})
    draw_bar_chart(tier_data, "Cost by Tier ($)")
    
    # Model breakdown
    model_data = status.get("model_breakdown", {})
    draw_bar_chart(model_data, "Cost by Model ($)")
    
    # 4. Optimization
    print_header("OPTIMIZATION REPORT")
    
    optimizations = report.get("optimizations", [])
    if not optimizations:
        print("No optimizations found. Good job!")
    else:
        for i, opt in enumerate(optimizations, 1):
            print(f"{i}. {opt['type'].upper()}")
            print(f"   Recommendation: {opt['recommendation']}")
            print(f"   Potential Savings: {format_currency(opt['potential_savings'])}")
            print()

if __name__ == "__main__":
    main()
