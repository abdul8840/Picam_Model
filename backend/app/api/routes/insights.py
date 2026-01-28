"""
PICAM Insights API Routes
Daily insights and action recommendations
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date

from app.models.mongodb_models import DailyInsight, ActionRecommendation
from app.models.schemas import DailyInsightResponse, ActionRecommendationResponse
from app.utils import now_utc

router = APIRouter()


@router.get("/daily/{target_date}", response_model=dict)
async def get_daily_insight(target_date: date):
    """
    Get daily insight including top loss point and recommended action.
    
    If insight doesn't exist for the date, it will indicate pending calculation.
    """
    try:
        insight = await DailyInsight.find_one({"date": target_date})
        
        if not insight:
            return {
                "date": target_date.isoformat(),
                "status": "pending",
                "message": "Daily insight not yet calculated. Run calculation endpoint."
            }
        
        return {
            "date": target_date.isoformat(),
            "status": "available",
            "generated_at": insight.generated_at.isoformat(),
            "top_loss": {
                "location": insight.top_loss_location,
                "amount": round(insight.top_loss_amount, 2),
                "cause": insight.top_loss_cause
            },
            "recommended_action": {
                "id": insight.recommended_action_id,
                "description": insight.recommended_action_description,
                "potential_recovery": round(insight.recommended_action_potential_recovery, 2)
            },
            "summary": {
                "total_loss": round(insight.total_calculated_loss, 2),
                "observations": insight.total_observations,
                "data_completeness": round(insight.data_completeness, 2),
                "confidence": round(insight.calculation_confidence, 2)
            },
            "loss_by_location": {
                loc: round(val, 2) 
                for loc, val in insight.loss_by_location.items()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/{target_date}", response_model=dict)
async def get_action_recommendations(target_date: date):
    """
    Get all action recommendations for a specific date.
    
    Actions are ranked by ROI (return on investment).
    """
    try:
        actions = await ActionRecommendation.find(
            {"date": target_date}
        ).sort("priority").to_list()
        
        if not actions:
            return {
                "date": target_date.isoformat(),
                "status": "no_actions",
                "message": "No action recommendations for this date"
            }
        
        return {
            "date": target_date.isoformat(),
            "actions": [
                {
                    "id": a.recommendation_id,
                    "priority": a.priority,
                    "location": a.location_id,
                    "type": a.action_type,
                    "description": a.action_description,
                    "min_recovery": round(a.min_recoverable_amount, 2),
                    "max_recovery": round(a.max_recoverable_amount, 2),
                    "cost": round(a.action_cost, 2),
                    "net_benefit": round(a.min_net_benefit, 2),
                    "roi_ratio": round(a.roi_ratio, 2),
                    "confidence": round(a.confidence_score, 2),
                    "justification": a.physics_justification,
                    "status": a.status
                }
                for a in actions
            ],
            "top_action": {
                "id": actions[0].recommendation_id,
                "description": actions[0].action_description,
                "net_benefit": round(actions[0].min_net_benefit, 2)
            } if actions else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends", response_model=dict)
async def get_loss_trends(
    days: int = Query(default=7, ge=1, le=90)
):
    """
    Get loss trends over recent days.
    """
    try:
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        insights = await DailyInsight.find(
            {"date": {"$gte": start_date, "$lte": end_date}}
        ).sort("date").to_list()
        
        if not insights:
            return {
                "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
                "status": "no_data"
            }
        
        daily_losses = [
            {
                "date": i.date.isoformat(),
                "total_loss": round(i.total_calculated_loss, 2),
                "top_location": i.top_loss_location
            }
            for i in insights
        ]
        
        total_loss = sum(i.total_calculated_loss for i in insights)
        avg_daily = total_loss / len(insights)
        
        return {
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "days_with_data": len(insights),
            "daily_losses": daily_losses,
            "summary": {
                "total_loss": round(total_loss, 2),
                "avg_daily_loss": round(avg_daily, 2),
                "max_daily_loss": round(max(i.total_calculated_loss for i in insights), 2),
                "min_daily_loss": round(min(i.total_calculated_loss for i in insights), 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))