"""
PICAM Insights API Routes (Updated)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date, timedelta

from app.services import (
    InsightGeneratorService,
    ActionRecommenderService,
    get_insight_generator,
    get_action_recommender
)
from app.utils import now_utc

router = APIRouter()


@router.get("/daily/{target_date}", response_model=dict)
async def get_daily_insight(
    target_date: date,
    generate: bool = Query(default=False, description="Generate if not exists")
):
    """
    Get daily insight including top loss point and recommended action.
    """
    service = get_insight_generator()
    
    if generate:
        return await service.generate_daily_insight(target_date)
    else:
        insight = await service.get_insight(target_date)
        if insight:
            return insight
        else:
            return {
                "date": target_date.isoformat(),
                "status": "not_generated",
                "message": "Use ?generate=true to generate insight"
            }


@router.post("/daily/{target_date}/generate", response_model=dict)
async def generate_daily_insight(
    target_date: date,
    force: bool = Query(default=False, description="Force regeneration")
):
    """
    Generate daily insight for a specific date.
    """
    service = get_insight_generator()
    return await service.generate_daily_insight(target_date, force_regenerate=force)


@router.get("/weekly", response_model=dict)
async def get_weekly_summary(
    end_date: Optional[date] = None
):
    """
    Get summary for the past 7 days.
    """
    service = get_insight_generator()
    return await service.get_weekly_summary(end_date)


@router.get("/trends", response_model=dict)
async def get_trend_analysis(
    days: int = Query(default=30, ge=7, le=90)
):
    """
    Get trend analysis over a period.
    """
    service = get_insight_generator()
    return await service.get_trend_analysis(days)


@router.post("/regenerate", response_model=dict)
async def regenerate_insights(
    start_date: date,
    end_date: date
):
    """
    Regenerate insights for a date range.
    """
    if (end_date - start_date).days > 90:
        raise HTTPException(
            status_code=400,
            detail="Maximum range is 90 days"
        )
    
    service = get_insight_generator()
    return await service.regenerate_insights(start_date, end_date)


@router.get("/actions/{target_date}", response_model=dict)
async def get_action_recommendations(target_date: date):
    """
    Get action recommendations for a specific date.
    """
    service = get_action_recommender()
    actions = await service.get_recommendations(target_date)
    
    if not actions:
        return {
            "date": target_date.isoformat(),
            "status": "no_actions",
            "message": "No recommendations for this date. Generate insight first."
        }
    
    return {
        "date": target_date.isoformat(),
        "actions": actions,
        "top_action": actions[0] if actions else None
    }


@router.get("/actions/pending", response_model=dict)
async def get_pending_actions():
    """
    Get all pending (not yet implemented) actions.
    """
    service = get_action_recommender()
    actions = await service.get_pending_actions()
    
    return {
        "count": len(actions),
        "actions": actions,
        "total_potential_recovery": sum(a["potential_recovery"] for a in actions)
    }