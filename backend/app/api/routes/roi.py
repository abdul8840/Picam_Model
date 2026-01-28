"""
PICAM ROI Tracking API Routes (Updated)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date
from pydantic import BaseModel

from app.services import ROITrackerService, get_roi_tracker
from app.utils import now_utc

router = APIRouter()


class ActionImplementationRequest(BaseModel):
    """Request to mark action as implemented."""
    action_id: str
    implementation_date: date
    actual_cost: Optional[float] = None
    notes: Optional[str] = None


class VerificationRequest(BaseModel):
    """Request to verify improvement."""
    action_id: str
    before_start_date: date
    before_end_date: date
    after_start_date: date
    after_end_date: date
    actual_cost: float


@router.get("/log", response_model=dict)
async def get_roi_log(
    limit: int = Query(default=50, ge=1, le=500),
    skip: int = Query(default=0, ge=0)
):
    """
    Get ROI log entries with chain verification.
    """
    service = get_roi_tracker()
    return await service.get_roi_log(limit, skip)


@router.get("/summary", response_model=dict)
async def get_roi_summary():
    """
    Get cumulative ROI statistics.
    """
    service = get_roi_tracker()
    return await service.get_cumulative_roi()


@router.post("/implement", response_model=dict)
async def record_action_implementation(request: ActionImplementationRequest):
    """
    Record that an action has been implemented.
    """
    service = get_roi_tracker()
    return await service.record_action_implementation(
        action_id=request.action_id,
        implementation_date=request.implementation_date,
        actual_cost=request.actual_cost,
        notes=request.notes
    )


@router.post("/verify", response_model=dict)
async def verify_and_record_improvement(request: VerificationRequest):
    """
    Verify improvement and create ROI log entry.
    
    Compares before and after periods using physics calculations.
    """
    service = get_roi_tracker()
    
    # Verify improvement
    verification = await service.verify_improvement(
        action_id=request.action_id,
        before_start_date=request.before_start_date,
        before_end_date=request.before_end_date,
        after_start_date=request.after_start_date,
        after_end_date=request.after_end_date
    )
    
    if not verification.is_valid:
        return {
            "status": "failed",
            "message": verification.notes,
            "verification": None
        }
    
    # Create ROI entry
    entry_id = await service.create_roi_entry(
        action_id=request.action_id,
        verification=verification,
        action_cost=request.actual_cost
    )
    
    return {
        "status": "success",
        "entry_id": entry_id,
        "verification": {
            "before_daily_loss": verification.before_loss,
            "after_daily_loss": verification.after_loss,
            "daily_reduction": verification.loss_reduction,
            "improvement_percentage": verification.improvement_percentage,
            "confidence": verification.confidence,
            "physics_verified": verification.physics_verified
        },
        "roi": {
            "action_cost": request.actual_cost,
            "net_daily_benefit": verification.loss_reduction - request.actual_cost,
            "payback_days": round(
                request.actual_cost / verification.loss_reduction, 1
            ) if verification.loss_reduction > 0 else None
        }
    }


@router.get("/verify/{entry_id}", response_model=dict)
async def verify_roi_entry(entry_id: str):
    """
    Verify integrity of a specific ROI entry.
    """
    service = get_roi_tracker()
    return await service.verify_single_entry(entry_id)


@router.get("/chain-integrity", response_model=dict)
async def verify_chain_integrity():
    """
    Verify integrity of entire ROI chain.
    """
    service = get_roi_tracker()
    is_valid = await service.verify_chain_integrity()
    
    return {
        "chain_status": "valid" if is_valid else "broken",
        "verified_at": now_utc().isoformat(),
        "message": (
            "All entries verified - no tampering detected"
            if is_valid else
            "Chain integrity compromised - investigate immediately"
        )
    }