"""
PICAM Admin API Routes

Administrative endpoints for system management.
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import date, timedelta

from app.services.sample_data_generator import generate_sample_data
from app.services import get_insight_generator

router = APIRouter()


@router.post("/generate-sample-data", response_model=dict)
async def generate_sample_data_endpoint(
    days: int = Query(default=7, ge=1, le=30),
    seed: int = Query(default=42)
):
    """
    Generate sample operational data for testing.
    
    Generates realistic hotel operational patterns.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    
    return await generate_sample_data(start_date, end_date, seed)


@router.post("/generate-all-insights", response_model=dict)
async def generate_all_insights(
    days: int = Query(default=7, ge=1, le=30)
):
    """
    Generate insights for recent days with data.
    """
    service = get_insight_generator()
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    
    return await service.regenerate_insights(start_date, end_date)