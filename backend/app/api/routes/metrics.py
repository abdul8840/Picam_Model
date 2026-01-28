"""
PICAM Metrics API Routes
Endpoints for physics-based calculations and metrics
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date, datetime

from app.models.mongodb_models import OperationalDataPoint
from app.models.schemas import (
    LittlesLawResultResponse,
    FinancialLossResponse,
    MetricsSummaryResponse
)
from app.utils import get_date_range, now_utc

router = APIRouter()


@router.get("/summary/{target_date}", response_model=dict)
async def get_metrics_summary(
    target_date: date,
    location_id: Optional[str] = None
):
    """
    Get summary metrics for a specific date.
    
    Returns aggregated flow, time, and utilization metrics.
    All calculations are deterministic and traceable.
    """
    try:
        start_dt, end_dt = get_date_range(target_date, target_date)
        
        # Build query
        query = {"date": target_date}
        if location_id:
            query["location_id"] = location_id
        
        # Fetch data points
        data_points = await OperationalDataPoint.find(query).to_list()
        
        if not data_points:
            return {
                "date": target_date.isoformat(),
                "status": "no_data",
                "message": "No operational data for this date"
            }
        
        # Aggregate metrics
        total_arrivals = sum(dp.arrival_count for dp in data_points)
        total_departures = sum(dp.departure_count for dp in data_points)
        
        queue_lengths = [dp.queue_length for dp in data_points]
        avg_queue = sum(queue_lengths) / len(queue_lengths)
        max_queue = max(queue_lengths)
        
        wait_times = [dp.avg_wait_time for dp in data_points if dp.avg_wait_time]
        avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0
        max_wait = max(wait_times) if wait_times else 0
        
        service_times = [dp.avg_service_duration for dp in data_points if dp.avg_service_duration]
        avg_service = sum(service_times) / len(service_times) if service_times else 0
        
        # Calculate utilization
        utilizations = []
        for dp in data_points:
            if dp.departure_rate and dp.departure_rate > 0:
                rho = dp.arrival_rate / dp.departure_rate
                utilizations.append(min(rho, 2.0))  # Cap at 200%
        
        avg_util = sum(utilizations) / len(utilizations) if utilizations else 0
        peak_util = max(utilizations) if utilizations else 0
        
        return {
            "date": target_date.isoformat(),
            "data_points_count": len(data_points),
            "flow_metrics": {
                "total_arrivals": total_arrivals,
                "total_departures": total_departures,
                "net_flow": total_arrivals - total_departures
            },
            "queue_metrics": {
                "avg_queue_length": round(avg_queue, 2),
                "max_queue_length": max_queue
            },
            "time_metrics": {
                "avg_wait_time_seconds": round(avg_wait, 2),
                "max_wait_time_seconds": round(max_wait, 2),
                "avg_service_time_seconds": round(avg_service, 2)
            },
            "utilization_metrics": {
                "avg_utilization": round(avg_util, 4),
                "peak_utilization": round(peak_util, 4),
                "is_overloaded": peak_util >= 1.0
            },
            "calculation_metadata": {
                "timestamp": now_utc().isoformat(),
                "is_deterministic": True,
                "formula": "Standard queueing metrics aggregation"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hourly/{target_date}", response_model=dict)
async def get_hourly_metrics(
    target_date: date,
    location_id: Optional[str] = None
):
    """
    Get metrics broken down by hour for a specific date.
    
    Useful for identifying peak periods and patterns.
    """
    try:
        query = {"date": target_date}
        if location_id:
            query["location_id"] = location_id
            
        data_points = await OperationalDataPoint.find(query).to_list()
        
        if not data_points:
            return {
                "date": target_date.isoformat(),
                "status": "no_data"
            }
        
        # Group by hour
        hourly = {h: {"arrivals": 0, "queue_lengths": [], "wait_times": []} 
                  for h in range(24)}
        
        for dp in data_points:
            hour = dp.timestamp.hour
            hourly[hour]["arrivals"] += dp.arrival_count
            hourly[hour]["queue_lengths"].append(dp.queue_length)
            if dp.avg_wait_time:
                hourly[hour]["wait_times"].append(dp.avg_wait_time)
        
        # Calculate hourly averages
        result = {}
        for hour, data in hourly.items():
            if data["queue_lengths"]:
                result[hour] = {
                    "arrivals": data["arrivals"],
                    "avg_queue_length": round(
                        sum(data["queue_lengths"]) / len(data["queue_lengths"]), 2
                    ),
                    "avg_wait_time": round(
                        sum(data["wait_times"]) / len(data["wait_times"]), 2
                    ) if data["wait_times"] else None
                }
        
        return {
            "date": target_date.isoformat(),
            "hourly_metrics": result,
            "peak_hour": max(result.keys(), key=lambda h: result[h]["arrivals"]) if result else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations/{target_date}", response_model=dict)
async def get_location_metrics(target_date: date):
    """
    Get metrics for all locations on a specific date.
    """
    try:
        data_points = await OperationalDataPoint.find(
            {"date": target_date}
        ).to_list()
        
        if not data_points:
            return {
                "date": target_date.isoformat(),
                "status": "no_data"
            }
        
        # Group by location
        by_location = {}
        for dp in data_points:
            loc = dp.location_id
            if loc not in by_location:
                by_location[loc] = []
            by_location[loc].append(dp)
        
        # Calculate per-location metrics
        result = {}
        for loc, dps in by_location.items():
            arrivals = sum(dp.arrival_count for dp in dps)
            queues = [dp.queue_length for dp in dps]
            waits = [dp.avg_wait_time for dp in dps if dp.avg_wait_time]
            
            result[loc] = {
                "total_arrivals": arrivals,
                "avg_queue_length": round(sum(queues) / len(queues), 2),
                "max_queue_length": max(queues),
                "avg_wait_time": round(sum(waits) / len(waits), 2) if waits else None,
                "data_points": len(dps)
            }
        
        return {
            "date": target_date.isoformat(),
            "locations": result,
            "total_locations": len(result)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))