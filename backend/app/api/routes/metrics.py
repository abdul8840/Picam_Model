"""
PICAM Metrics API Routes
Endpoints for physics-based calculations and metrics
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import date, datetime

from app.models.mongodb_models import OperationalDataPoint
from app.models.domain import FlowMeasurement, LocationType, CapacityConstraint
from app.core import (
    LittlesLawCalculator,
    EntropyCalculator,
    LossCalculator,
    get_physics_engine
)
from app.utils import get_date_range, now_utc
from app.config import get_settings

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
                utilizations.append(min(rho, 2.0))
        
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


@router.get("/littles-law/{target_date}", response_model=dict)
async def calculate_littles_law(
    target_date: date,
    location_id: Optional[str] = None
):
    """
    Calculate Little's Law metrics (L = λW) for a specific date.
    
    Returns:
    - L: Average number in system
    - λ: Arrival rate
    - W: Average time in system
    - Plus queue-specific metrics (Lq, Wq, ρ)
    """
    try:
        query = {"date": target_date}
        if location_id:
            query["location_id"] = location_id
            
        data_points = await OperationalDataPoint.find(query).to_list()
        
        if len(data_points) < 10:
            return {
                "date": target_date.isoformat(),
                "status": "insufficient_data",
                "message": f"Need at least 10 data points, have {len(data_points)}"
            }
        
        # Convert to FlowMeasurements
        measurements = []
        for dp in data_points:
            m = FlowMeasurement(
                timestamp=dp.timestamp,
                location_id=dp.location_id,
                location_type=LocationType(dp.location_type),
                arrival_count=dp.arrival_count,
                departure_count=dp.departure_count,
                queue_length=dp.queue_length,
                in_service_count=dp.in_service_count,
                avg_service_duration=dp.avg_service_duration,
                avg_wait_time=dp.avg_wait_time,
                observation_period_seconds=dp.observation_period_seconds
            )
            measurements.append(m)
        
        # Calculate Little's Law
        calculator = LittlesLawCalculator()
        result = calculator.calculate(measurements)
        
        if not result:
            return {
                "date": target_date.isoformat(),
                "status": "calculation_failed",
                "message": "Could not calculate Little's Law metrics"
            }
        
        # Verify the law holds
        verification = calculator.verify_littles_law(measurements)
        
        return {
            "date": target_date.isoformat(),
            "status": "calculated",
            "littles_law": {
                "L": round(result.L, 4),
                "lambda_rate": round(result.lambda_rate, 6),
                "W_seconds": round(result.W, 2),
                "formula": "L = λW"
            },
            "queue_metrics": {
                "L_q": round(result.L_q, 4),
                "W_q_seconds": round(result.W_q, 2),
                "utilization_rho": round(result.rho, 4)
            },
            "system_state": {
                "is_stable": result.rho < 1.0,
                "is_valid": result.is_valid,
                "confidence_interval": [
                    round(result.confidence_interval_lower, 4),
                    round(result.confidence_interval_upper, 4)
                ]
            },
            "verification": verification,
            "data_points_used": result.data_points_used,
            "calculation_metadata": {
                "timestamp": now_utc().isoformat(),
                "is_deterministic": True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entropy/{target_date}", response_model=dict)
async def calculate_entropy(
    target_date: date,
    location_id: Optional[str] = None
):
    """
    Calculate operational entropy (variability) for a specific date.
    
    Returns:
    - Coefficient of variation for arrivals and service
    - Entropy score (0-1)
    - Kingman's formula impact on wait times
    """
    try:
        query = {"date": target_date}
        if location_id:
            query["location_id"] = location_id
            
        data_points = await OperationalDataPoint.find(query).to_list()
        
        if len(data_points) < 10:
            return {
                "date": target_date.isoformat(),
                "status": "insufficient_data"
            }
        
        # Convert to FlowMeasurements
        measurements = [
            FlowMeasurement(
                timestamp=dp.timestamp,
                location_id=dp.location_id,
                location_type=LocationType(dp.location_type),
                arrival_count=dp.arrival_count,
                departure_count=dp.departure_count,
                queue_length=dp.queue_length,
                in_service_count=dp.in_service_count,
                avg_service_duration=dp.avg_service_duration,
                avg_wait_time=dp.avg_wait_time,
                observation_period_seconds=dp.observation_period_seconds
            )
            for dp in data_points
        ]
        
        # Calculate entropy
        calculator = EntropyCalculator()
        entropy = calculator.calculate_entropy(
            measurements,
            location_id or data_points[0].location_id
        )
        
        if not entropy:
            return {
                "date": target_date.isoformat(),
                "status": "calculation_failed"
            }
        
        # Analyze patterns
        patterns = calculator.analyze_patterns(measurements)
        
        # Calculate Kingman impact
        # Need utilization for this
        littles_calc = LittlesLawCalculator()
        littles_result = littles_calc.calculate(measurements)
        
        kingman_impact = None
        if littles_result:
            kingman_impact = calculator.calculate_kingman_impact(
                entropy.arrival_cv,
                entropy.service_cv,
                littles_result.rho
            )
        
        return {
            "date": target_date.isoformat(),
            "status": "calculated",
            "entropy": {
                "arrival_cv": round(entropy.arrival_cv, 4),
                "service_cv": round(entropy.service_cv, 4),
                "entropy_score": round(entropy.entropy_score, 4),
                "variance_impact_multiplier": round(entropy.variance_impact_multiplier, 4)
            },
            "interpretation": {
                "arrival_variability": (
                    "low" if entropy.arrival_cv < 0.5 else
                    "moderate" if entropy.arrival_cv < 1.0 else
                    "high"
                ),
                "service_variability": (
                    "low" if entropy.service_cv < 0.5 else
                    "moderate" if entropy.service_cv < 1.0 else
                    "high"
                )
            },
            "patterns": patterns,
            "kingman_impact": kingman_impact,
            "calculation_metadata": {
                "timestamp": now_utc().isoformat(),
                "formula": "Kingman: Wq ≈ (ρ/(1-ρ)) × ((Ca² + Cs²)/2) × (1/μ)"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/loss/{target_date}", response_model=dict)
async def calculate_financial_loss(
    target_date: date,
    location_id: Optional[str] = None
):
    """
    Calculate conservative financial loss for a specific date.
    
    Returns breakdown of:
    - Wait time cost
    - Lost throughput revenue
    - Walk-away cost
    - Idle time cost
    - Overtime cost
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
        
        # Convert to FlowMeasurements
        measurements = [
            FlowMeasurement(
                timestamp=dp.timestamp,
                location_id=dp.location_id,
                location_type=LocationType(dp.location_type),
                arrival_count=dp.arrival_count,
                departure_count=dp.departure_count,
                queue_length=dp.queue_length,
                in_service_count=dp.in_service_count,
                avg_service_duration=dp.avg_service_duration,
                avg_wait_time=dp.avg_wait_time,
                observation_period_seconds=dp.observation_period_seconds
            )
            for dp in data_points
        ]
        
        # Get settings for capacity
        settings = get_settings()
        loc_type = data_points[0].location_type
        
        capacity = None
        if loc_type == "front_desk":
            capacity = CapacityConstraint(
                location_type=LocationType.FRONT_DESK,
                max_servers=settings.front_desk_stations,
                max_queue_capacity=50
            )
        
        # Calculate supporting metrics
        littles_calc = LittlesLawCalculator()
        entropy_calc = EntropyCalculator()
        
        littles_result = littles_calc.calculate(measurements, capacity)
        entropy = entropy_calc.calculate_entropy(
            measurements,
            location_id or data_points[0].location_id
        )
        
        # Calculate loss
        loss_calc = LossCalculator()
        loss = loss_calc.calculate_total_loss(
            measurements=measurements,
            littles_result=littles_result,
            entropy=entropy,
            capacity=capacity,
            target_date=target_date
        )
        
        return {
            "date": target_date.isoformat(),
            "location": location_id or data_points[0].location_id,
            "status": "calculated",
            "loss_breakdown": {
                "wait_time_cost": round(loss.wait_time_cost, 2),
                "lost_throughput_revenue": round(loss.lost_throughput_revenue, 2),
                "walkaway_cost": round(loss.walkaway_cost, 2),
                "idle_time_cost": round(loss.idle_time_cost, 2),
                "overtime_cost": round(loss.overtime_cost, 2)
            },
            "total_loss": round(loss.total_loss, 2),
            "supporting_data": {
                "total_wait_time_seconds": round(loss.total_wait_time_seconds, 0),
                "lost_throughput_count": loss.lost_throughput_count,
                "estimated_walkaways": loss.estimated_walkaways,
                "idle_time_hours": round(loss.idle_time_seconds / 3600, 2),
                "overtime_hours": round(loss.overtime_hours, 2)
            },
            "calculation_hash": loss.create_hash(),
            "is_conservative": True,
            "calculation_metadata": {
                "timestamp": now_utc().isoformat(),
                "confidence_factor": 0.7,
                "note": "All losses are conservative lower-bound estimates"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{target_date}", response_model=dict)
async def get_complete_analysis(
    target_date: date,
    location_id: Optional[str] = None
):
    """
    Get complete physics-based analysis for a date.
    
    Combines Little's Law, entropy, and loss calculations
    into a unified analysis.
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
        
        # Convert to FlowMeasurements
        measurements = [
            FlowMeasurement(
                timestamp=dp.timestamp,
                location_id=dp.location_id,
                location_type=LocationType(dp.location_type),
                arrival_count=dp.arrival_count,
                departure_count=dp.departure_count,
                queue_length=dp.queue_length,
                in_service_count=dp.in_service_count,
                avg_service_duration=dp.avg_service_duration,
                avg_wait_time=dp.avg_wait_time,
                observation_period_seconds=dp.observation_period_seconds
            )
            for dp in data_points
        ]
        
        # Use physics engine for complete analysis
        engine = get_physics_engine()
        
        settings = get_settings()
        capacity = CapacityConstraint(
            location_type=LocationType.FRONT_DESK,
            max_servers=settings.front_desk_stations,
            max_queue_capacity=50
        )
        
        analysis = engine.analyze_location(measurements, capacity)
        
        return {
            "date": target_date.isoformat(),
            **analysis
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
        
        # Find peak hour
        peak_hour = None
        if result:
            peak_hour = max(result.keys(), key=lambda h: result[h]["arrivals"])
        
        return {
            "date": target_date.isoformat(),
            "hourly_metrics": result,
            "peak_hour": peak_hour,
            "peak_arrivals": result[peak_hour]["arrivals"] if peak_hour else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))