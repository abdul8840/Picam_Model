"""
PICAM Data Ingestion API Routes
Handles operational data input from various sources
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime

from app.models.schemas import (
    OperationalDataInput,
    BatchOperationalDataInput
)
from app.models.mongodb_models import OperationalDataPoint
from app.utils import now_utc, to_utc

router = APIRouter()


@router.post("/ingest", response_model=dict)
async def ingest_operational_data(data: OperationalDataInput):
    """
    Ingest a single operational data point.
    
    This endpoint accepts operational measurements (counts, durations, queue lengths)
    and stores them for physics-based analysis.
    
    **Privacy Note**: No personal data is accepted or stored.
    """
    try:
        # Calculate rates
        arrival_rate = data.arrival_count / data.observation_period_seconds
        departure_rate = data.departure_count / data.observation_period_seconds
        
        # Create document
        doc = OperationalDataPoint(
            timestamp=to_utc(data.timestamp),
            date=to_utc(data.timestamp).date(),
            location_id=data.location_id,
            location_type=data.location_type.value,
            arrival_count=data.arrival_count,
            departure_count=data.departure_count,
            queue_length=data.queue_length,
            in_service_count=data.in_service_count,
            avg_service_duration=data.avg_service_duration_seconds,
            avg_wait_time=data.avg_wait_time_seconds,
            observation_period_seconds=data.observation_period_seconds,
            arrival_rate=arrival_rate,
            departure_rate=departure_rate,
            data_source="api",
            created_at=now_utc()
        )
        
        await doc.insert()
        
        return {
            "status": "success",
            "message": "Data point ingested",
            "id": str(doc.id),
            "timestamp": data.timestamp.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/batch", response_model=dict)
async def ingest_batch_operational_data(data: BatchOperationalDataInput):
    """
    Ingest multiple operational data points in batch.
    
    Efficient for bulk historical data import.
    """
    try:
        docs = []
        
        for dp in data.data_points:
            arrival_rate = dp.arrival_count / dp.observation_period_seconds
            departure_rate = dp.departure_count / dp.observation_period_seconds
            
            doc = OperationalDataPoint(
                timestamp=to_utc(dp.timestamp),
                date=to_utc(dp.timestamp).date(),
                location_id=dp.location_id,
                location_type=dp.location_type.value,
                arrival_count=dp.arrival_count,
                departure_count=dp.departure_count,
                queue_length=dp.queue_length,
                in_service_count=dp.in_service_count,
                avg_service_duration=dp.avg_service_duration_seconds,
                avg_wait_time=dp.avg_wait_time_seconds,
                observation_period_seconds=dp.observation_period_seconds,
                arrival_rate=arrival_rate,
                departure_rate=departure_rate,
                data_source="api_batch",
                created_at=now_utc()
            )
            docs.append(doc)
        
        # Bulk insert
        await OperationalDataPoint.insert_many(docs)
        
        return {
            "status": "success",
            "message": f"Batch ingested: {len(docs)} data points",
            "count": len(docs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations", response_model=List[str])
async def get_locations():
    """
    Get list of all location IDs with data.
    """
    try:
        locations = await OperationalDataPoint.distinct("location_id")
        return locations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count", response_model=dict)
async def get_data_count():
    """
    Get total count of operational data points.
    """
    try:
        count = await OperationalDataPoint.count()
        return {
            "total_data_points": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))