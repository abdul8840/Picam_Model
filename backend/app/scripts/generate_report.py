"""
PICAM Report Generator

Generates a summary report of operational losses and ROI.
"""

import asyncio
import os
import sys
from datetime import date, timedelta
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import DatabaseManager
from app.models.mongodb_models import DailyInsight, ROILogEntry
from app.services import get_roi_tracker, get_insight_generator
from app.config import get_settings


async def generate_report(days: int = 7):
    """Generate a summary report."""
    
    print("=" * 60)
    print("PICAM Summary Report")
    print("=" * 60)
    
    await DatabaseManager.connect()
    
    try:
        settings = get_settings()
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        
        print(f"\nHotel: {settings.hotel_name}")
        print(f"Period: {start_date} to {end_date}")
        print()
        
        # Get insights
        insights = await DailyInsight.find({
            "date": {"$gte": start_date, "$lte": end_date}
        }).sort("date").to_list()
        
        if not insights:
            print("No data available for this period.")
            return
        
        # Calculate totals
        total_loss = sum(i.total_calculated_loss for i in insights)
        avg_daily_loss = total_loss / len(insights)
        
        # Find worst day
        worst_day = max(insights, key=lambda i: i.total_calculated_loss)
        
        # Loss by location
        location_totals = {}
        for insight in insights:
            for loc, loss in insight.loss_by_location.items():
                location_totals[loc] = location_totals.get(loc, 0) + loss
        
        # Get ROI data
        roi_tracker = get_roi_tracker()
        roi_summary = await roi_tracker.get_cumulative_roi()
        
        # Print report
        print("-" * 60)
        print("FINANCIAL SUMMARY")
        print("-" * 60)
        print(f"  Total Calculated Loss:    ${total_loss:,.2f}")
        print(f"  Average Daily Loss:       ${avg_daily_loss:,.2f}")
        print(f"  Days Analyzed:            {len(insights)}")
        print()
        print(f"  Worst Day: {worst_day.date}")
        print(f"    Loss: ${worst_day.total_calculated_loss:,.2f}")
        print(f"    Location: {worst_day.top_loss_location}")
        print(f"    Cause: {worst_day.top_loss_cause}")
        print()
        
        print("-" * 60)
        print("LOSS BY LOCATION")
        print("-" * 60)
        for loc, loss in sorted(location_totals.items(), key=lambda x: x[1], reverse=True):
            pct = (loss / total_loss) * 100 if total_loss > 0 else 0
            print(f"  {loc:30s} ${loss:>10,.2f} ({pct:5.1f}%)")
        print()
        
        print("-" * 60)
        print("ROI SUMMARY")
        print("-" * 60)
        if roi_summary.get("status") == "available":
            cumulative = roi_summary.get("cumulative", {})
            print(f"  Total Verified Savings:   ${cumulative.get('total_savings', 0):,.2f}")
            print(f"  Total Action Cost:        ${cumulative.get('total_cost', 0):,.2f}")
            print(f"  Net Benefit:              ${cumulative.get('total_net_benefit', 0):,.2f}")
            print(f"  Overall ROI:              {cumulative.get('overall_roi', 'N/A')}%")
        else:
            print("  No verified improvements yet.")
        print()
        
        print("-" * 60)
        print("PHYSICS PRINCIPLES APPLIED")
        print("-" * 60)
        print("  • Little's Law: L = λW")
        print("  • Queueing Theory: M/M/c models")
        print("  • Kingman's Formula: Variability impact")
        print("  • Conservative estimation: 95% confidence")
        print()
        
        print("-" * 60)
        print("RECOMMENDATIONS")
        print("-" * 60)
        # Get latest recommendation
        latest_insight = insights[-1] if insights else None
        if latest_insight and latest_insight.recommended_action_description:
            print(f"  Today's Top Action:")
            print(f"    {latest_insight.recommended_action_description}")
            print(f"    Potential Recovery: ${latest_insight.recommended_action_potential_recovery:,.2f}")
        else:
            print("  Generate insights to see recommendations.")
        print()
        
        print("=" * 60)
        print("Report generated successfully.")
        print("=" * 60)
        
    finally:
        await DatabaseManager.disconnect()


def main():
    """Entry point."""
    days = int(os.environ.get('REPORT_DAYS', 7))
    asyncio.run(generate_report(days))


if __name__ == "__main__":
    main()