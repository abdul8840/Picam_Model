"""
PICAM Insight Generator Service

Generates daily insights combining all physics calculations.

Each daily insight includes:
- Top loss point identification
- Recommended action
- Aggregated metrics
- Trend analysis
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import uuid

from app.models.mongodb_models import (
    DailyInsight as DailyInsightDoc,
    OperationalDataPoint,
    ActionRecommendation as ActionRecommendationDoc
)
from app.models.domain import (
    DailyInsight,
    FlowMeasurement,
    LocationType,
    CapacityConstraint
)
from app.core import get_physics_engine
from app.services.data_ingestion import get_ingestion_service
from app.services.action_recommender import get_action_recommender
from app.utils import now_utc, create_deterministic_hash
from app.config import get_settings

logger = logging.getLogger(__name__)


class InsightGeneratorService:
    """
    Service for generating daily operational insights.
    
    Orchestrates data retrieval, physics calculations, and
    recommendation generation into a single daily summary.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.physics_engine = get_physics_engine()
        self.data_service = get_ingestion_service()
        self.recommender = get_action_recommender()
    
    async def generate_daily_insight(
        self,
        target_date: date,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate or retrieve daily insight.
        
        Args:
            target_date: Date to generate insight for
            force_regenerate: If True, regenerate even if exists
            
        Returns:
            Daily insight data
        """
        # Check if already exists
        if not force_regenerate:
            existing = await DailyInsightDoc.find_one({"date": target_date})
            if existing:
                return self._format_insight(existing)
        
        # Get data grouped by location
        data_by_location = await self.data_service.get_data_grouped_by_location(
            target_date
        )
        
        if not data_by_location:
            return {
                "date": target_date.isoformat(),
                "status": "no_data",
                "message": "No operational data for this date"
            }
        
        # Build capacity constraints
        capacities = self._build_capacities(data_by_location.keys())
        
        # Use physics engine for complete analysis
        daily_insight = self.physics_engine.analyze_day(
            measurements_by_location=data_by_location,
            capacities=capacities,
            target_date=target_date
        )
        
        # Generate recommendation if not already done
        recommendation = await self.recommender.generate_daily_recommendation(
            target_date
        )
        
        # Store the insight
        await self._store_insight(daily_insight, recommendation)
        
        # Return formatted response
        return {
            "date": target_date.isoformat(),
            "status": "generated",
            "generated_at": now_utc().isoformat(),
            "top_loss": {
                "location": daily_insight.top_loss_location,
                "amount": round(daily_insight.top_loss_amount, 2),
                "cause": daily_insight.top_loss_cause
            },
            "recommended_action": {
                "id": recommendation.recommendation_id if recommendation else None,
                "description": recommendation.action_description if recommendation else "No recommendation",
                "potential_recovery": round(
                    recommendation.min_recoverable_amount, 2
                ) if recommendation else 0,
                "confidence": round(
                    recommendation.confidence_score, 2
                ) if recommendation else 0
            },
            "summary": {
                "total_loss": round(daily_insight.total_calculated_loss, 2),
                "total_observations": daily_insight.total_observations,
                "locations_analyzed": len(data_by_location),
                "data_completeness": round(daily_insight.data_completeness, 2),
                "calculation_confidence": round(daily_insight.calculation_confidence, 2)
            },
            "loss_by_location": {
                loc: round(val, 2)
                for loc, val in daily_insight.loss_by_location.items()
            }
        }
    
    async def get_insight(self, target_date: date) -> Optional[Dict[str, Any]]:
        """
        Get existing insight for a date.
        """
        insight = await DailyInsightDoc.find_one({"date": target_date})
        
        if not insight:
            return None
        
        return self._format_insight(insight)
    
    async def get_weekly_summary(
        self,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get summary for the past 7 days.
        """
        if end_date is None:
            end_date = date.today()
        
        start_date = end_date - timedelta(days=6)
        
        insights = await DailyInsightDoc.find({
            "date": {"$gte": start_date, "$lte": end_date}
        }).sort("date").to_list()
        
        if not insights:
            return {
                "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
                "status": "no_data"
            }
        
        # Aggregate
        total_loss = sum(i.total_calculated_loss for i in insights)
        avg_daily_loss = total_loss / len(insights)
        
        # Find worst day
        worst_day = max(insights, key=lambda i: i.total_calculated_loss)
        
        # Top locations across the week
        location_totals: Dict[str, float] = {}
        for insight in insights:
            for loc, loss in insight.loss_by_location.items():
                location_totals[loc] = location_totals.get(loc, 0) + loss
        
        top_locations = sorted(
            location_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "days_with_data": len(insights),
            "summary": {
                "total_loss": round(total_loss, 2),
                "avg_daily_loss": round(avg_daily_loss, 2),
                "worst_day": {
                    "date": worst_day.date.isoformat(),
                    "loss": round(worst_day.total_calculated_loss, 2)
                }
            },
            "top_loss_locations": [
                {"location": loc, "total_loss": round(loss, 2)}
                for loc, loss in top_locations
            ],
            "daily_breakdown": [
                {
                    "date": i.date.isoformat(),
                    "total_loss": round(i.total_calculated_loss, 2),
                    "top_location": i.top_loss_location
                }
                for i in insights
            ]
        }
    
    async def get_trend_analysis(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze trends over a period.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        
        insights = await DailyInsightDoc.find({
            "date": {"$gte": start_date, "$lte": end_date}
        }).sort("date").to_list()
        
        if len(insights) < 7:
            return {
                "status": "insufficient_data",
                "message": "Need at least 7 days of data for trend analysis"
            }
        
        losses = [i.total_calculated_loss for i in insights]
        
        # Calculate trend (simple linear regression slope)
        n = len(losses)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(losses) / n
        
        numerator = sum((x[i] - x_mean) * (losses[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator > 0 else 0
        
        # Trend direction
        if slope < -0.05 * y_mean:
            trend = "improving"
        elif slope > 0.05 * y_mean:
            trend = "worsening"
        else:
            trend = "stable"
        
        # Week-over-week comparison
        if len(insights) >= 14:
            last_week = insights[-7:]
            prev_week = insights[-14:-7]
            
            last_week_avg = sum(i.total_calculated_loss for i in last_week) / 7
            prev_week_avg = sum(i.total_calculated_loss for i in prev_week) / 7
            
            wow_change = ((last_week_avg - prev_week_avg) / prev_week_avg * 100) if prev_week_avg > 0 else 0
        else:
            last_week_avg = None
            prev_week_avg = None
            wow_change = None
        
        return {
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "days_analyzed": len(insights),
            "trend": {
                "direction": trend,
                "slope_per_day": round(slope, 2),
                "interpretation": self._interpret_trend(trend, slope)
            },
            "averages": {
                "overall_avg_daily_loss": round(y_mean, 2),
                "last_7_days_avg": round(last_week_avg, 2) if last_week_avg else None,
                "previous_7_days_avg": round(prev_week_avg, 2) if prev_week_avg else None
            },
            "week_over_week": {
                "change_percentage": round(wow_change, 1) if wow_change else None,
                "interpretation": (
                    "improving" if wow_change and wow_change < -5 else
                    "worsening" if wow_change and wow_change > 5 else
                    "stable" if wow_change else None
                )
            }
        }
    
    async def regenerate_insights(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Regenerate insights for a date range.
        """
        current = start_date
        generated = 0
        failed = 0
        
        while current <= end_date:
            try:
                await self.generate_daily_insight(current, force_regenerate=True)
                generated += 1
            except Exception as e:
                logger.error(f"Failed to generate insight for {current}: {e}")
                failed += 1
            
            current += timedelta(days=1)
        
        return {
            "status": "complete",
            "date_range": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "generated": generated,
            "failed": failed
        }
    
    def _build_capacities(
        self,
        location_ids: List[str]
    ) -> Dict[str, CapacityConstraint]:
        """
        Build capacity constraints for locations.
        """
        capacities = {}
        
        for loc_id in location_ids:
            # Determine type from ID (simple heuristic)
            if "front_desk" in loc_id.lower():
                capacities[loc_id] = CapacityConstraint(
                    location_type=LocationType.FRONT_DESK,
                    max_servers=self.settings.front_desk_stations,
                    max_queue_capacity=50
                )
            elif "restaurant" in loc_id.lower():
                capacities[loc_id] = CapacityConstraint(
                    location_type=LocationType.RESTAURANT,
                    max_servers=self.settings.restaurant_capacity // 4,
                    max_queue_capacity=30
                )
            else:
                capacities[loc_id] = CapacityConstraint(
                    location_type=LocationType.LOBBY,
                    max_servers=2,
                    max_queue_capacity=20
                )
        
        return capacities
    
    async def _store_insight(
        self,
        insight: DailyInsight,
        recommendation
    ) -> None:
        """
        Store daily insight in database.
        """
        # Delete existing if any
        await DailyInsightDoc.find_one({"date": insight.date}).delete()
        
        # Create calculation hash
        calc_data = {
            "date": insight.date.isoformat(),
            "total_loss": insight.total_calculated_loss,
            "top_location": insight.top_loss_location,
            "observations": insight.total_observations
        }
        calculation_hash = create_deterministic_hash(calc_data)
        
        doc = DailyInsightDoc(
            date=insight.date,
            generated_at=insight.generated_at,
            top_loss_location=insight.top_loss_location,
            top_loss_amount=insight.top_loss_amount,
            top_loss_cause=insight.top_loss_cause,
            recommended_action_id=recommendation.recommendation_id if recommendation else "",
            recommended_action_description=recommendation.action_description if recommendation else "",
            recommended_action_potential_recovery=recommendation.min_recoverable_amount if recommendation else 0,
            total_calculated_loss=insight.total_calculated_loss,
            total_observations=insight.total_observations,
            loss_by_location=insight.loss_by_location,
            littles_law_results={},
            entropy_scores={},
            data_completeness=insight.data_completeness,
            calculation_confidence=insight.calculation_confidence,
            calculation_hash=calculation_hash,
            created_at=now_utc()
        )
        
        await doc.insert()
        logger.info(f"Stored insight for {insight.date}")
    
    def _format_insight(self, doc: DailyInsightDoc) -> Dict[str, Any]:
        """
        Format stored insight for API response.
        """
        return {
            "date": doc.date.isoformat(),
            "status": "available",
            "generated_at": doc.generated_at.isoformat(),
            "top_loss": {
                "location": doc.top_loss_location,
                "amount": round(doc.top_loss_amount, 2),
                "cause": doc.top_loss_cause
            },
            "recommended_action": {
                "id": doc.recommended_action_id,
                "description": doc.recommended_action_description,
                "potential_recovery": round(doc.recommended_action_potential_recovery, 2)
            },
            "summary": {
                "total_loss": round(doc.total_calculated_loss, 2),
                "total_observations": doc.total_observations,
                "data_completeness": round(doc.data_completeness, 2),
                "calculation_confidence": round(doc.calculation_confidence, 2)
            },
            "loss_by_location": {
                loc: round(val, 2)
                for loc, val in doc.loss_by_location.items()
            },
            "calculation_hash": doc.calculation_hash
        }
    
    def _interpret_trend(self, trend: str, slope: float) -> str:
        """
        Interpret trend for human understanding.
        """
        if trend == "improving":
            return f"Losses decreasing by ~${abs(slope):.0f}/day. Keep current improvements."
        elif trend == "worsening":
            return f"Losses increasing by ~${slope:.0f}/day. Action recommended."
        else:
            return "Losses stable. Focus on top loss points for improvement."


# Service instance factory
_insight_service: Optional[InsightGeneratorService] = None


def get_insight_generator() -> InsightGeneratorService:
    """Get or create insight generator instance."""
    global _insight_service
    if _insight_service is None:
        _insight_service = InsightGeneratorService()
    return _insight_service