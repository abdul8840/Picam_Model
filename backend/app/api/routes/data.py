"""
PICAM Data Ingestion API Routes (Updated)
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from typing import List, Optional
from datetime import date

from app.models.schemas import (
    OperationalDataInput,
    BatchOperationalDataInput,
    DateRangeQuery
)
from app.services import (
    DataIngestionService,
    VideoProcessorService,
    get_ingestion_service,
    get_video_processor
)
from app.utils import now_utc

router = APIRouter()


@router.post("/ingest", response_model=dict)
async def ingest_operational_data(data: OperationalDataInput):
    """
    Ingest a single operational data point.
    
    Accepts operational measurements and stores them for physics-based analysis.
    **Privacy Note**: No personal data is accepted or stored.
    """
    service = get_ingestion_service()
    result = await service.ingest_single(data, source="api")
    
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail={"errors": result.errors}
        )
    
    return {
        "status": "success",
        "message": "Data point ingested",
        "id": result.data_point_ids[0] if result.data_point_ids else None,
        "timestamp": now_utc().isoformat()
    }


@router.post("/ingest/batch", response_model=dict)
async def ingest_batch_operational_data(data: BatchOperationalDataInput):
    """
    Ingest multiple operational data points in batch.
    """
    service = get_ingestion_service()
    result = await service.ingest_batch(data, source="api_batch")
    
    return {
        "status": "success" if result.success else "partial",
        "message": f"Processed {result.records_processed} records",
        "processed": result.records_processed,
        "failed": result.records_failed,
        "errors": result.errors[:10] if result.errors else []
    }


@router.post("/ingest/video-frame", response_model=dict)
async def ingest_video_frame(
    location_id: str,
    location_type: str,
    frame: UploadFile = File(...),
    camera_id: str = "default"
):
    """
    Process a video frame to extract people count.
    
    **PRIVACY**: Frame is processed in memory and immediately discarded.
    Only the count is retained.
    """
    processor = get_video_processor()
    
    # Read frame data
    frame_data = await frame.read()
    
    # Process (frame is discarded after processing)
    result = await processor.process_frame(
        frame_data=frame_data,
        location_id=location_id,
        location_type=location_type,
        camera_id=camera_id
    )
    
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail={"error": result.error}
        )
    
    return {
        "status": "success",
        "processing_id": result.processing_id,
        "detected_count": result.detected_count,
        "confidence": round(result.confidence, 4),
        "processing_time_ms": round(result.processing_time_ms, 2),
        "privacy": {
            "frame_stored": False,
            "personal_data_extracted": False
        }
    }


@router.get("/locations", response_model=List[str])
async def get_locations():
    """
    Get list of all location IDs with data.
    """
    service = get_ingestion_service()
    return await service.get_locations()


@router.get("/quality", response_model=dict)
async def get_data_quality(
    start_date: date,
    end_date: date,
    location_id: Optional[str] = None
):
    """
    Get data quality report for a date range.
    """
    service = get_ingestion_service()
    report = await service.check_data_quality(start_date, end_date, location_id)
    
    return {
        "period": f"{report.start_date.isoformat()} to {report.end_date.isoformat()}",
        "total_records": report.total_records,
        "completeness_score": report.completeness_score,
        "consistency_score": report.consistency_score,
        "issues": report.issues,
        "quality_grade": (
            "A" if report.completeness_score > 0.9 and report.consistency_score > 0.95 else
            "B" if report.completeness_score > 0.7 and report.consistency_score > 0.9 else
            "C" if report.completeness_score > 0.5 else
            "D"
        )
    }


@router.get("/date-range", response_model=dict)
async def get_available_date_range():
    """
    Get the date range that has data.
    """
    service = get_ingestion_service()
    start, end = await service.get_date_range_with_data()
    
    if start and end:
        return {
            "status": "available",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "days": (end - start).days + 1
        }
    else:
        return {
            "status": "no_data"
        }


@router.get("/video-stats", response_model=dict)
async def get_video_processing_stats(
    location_id: Optional[str] = None
):
    """
    Get video processing statistics.
    """
    processor = get_video_processor()
    return await processor.get_processing_stats(location_id)


@router.get("/privacy-compliance", response_model=dict)
async def verify_privacy_compliance():
    """
    Verify video processing privacy compliance.
    """
    processor = get_video_processor()
    compliance = processor.verify_privacy_compliance()
    
    return {
        "compliant": compliance.is_compliant,
        "details": {
            "frames_stored": compliance.frames_stored,
            "personal_data_extracted": compliance.personal_data_extracted,
            "raw_video_retained": compliance.raw_video_retained,
            "only_counts_saved": compliance.only_counts_saved
        }
    }