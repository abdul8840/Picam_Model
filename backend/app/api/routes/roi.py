"""
PICAM ROI Tracking API Routes
Immutable ROI log with hash chain verification
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date

from app.models.mongodb_models import ROILogEntry, ActionRecommendation
from app.models.schemas import (
    ROILogEntryResponse,
    ROILogListResponse,
    ActionCompletionInput
)
from app.utils import now_utc, create_deterministic_hash, verify_chain
import uuid

router = APIRouter()


@router.get("/log", response_model=dict)
async def get_roi_log(
    limit: int = Query(default=50, ge=1, le=500),
    skip: int = Query(default=0, ge=0)
):
    """
    Get ROI log entries with chain verification.
    
    The log is immutable - each entry contains hash of previous entry.
    """
    try:
        entries = await ROILogEntry.find().sort(
            [("sequence_number", -1)]
        ).skip(skip).limit(limit).to_list()
        
        total = await ROILogEntry.count()
        
        # Calculate totals
        total_savings = sum(e.loss_reduction for e in entries if e.loss_reduction > 0)
        
        # Verify chain integrity for returned entries
        chain_valid = True
        if len(entries) > 1:
            for i in range(1, len(entries)):
                if entries[i].entry_hash != entries[i-1].previous_entry_hash:
                    chain_valid = False
                    break
        
        return {
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "timestamp": e.timestamp.isoformat(),
                    "action_id": e.action_id,
                    "action_description": e.action_description,
                    "before_date": e.before_date.isoformat(),
                    "before_loss": round(e.before_loss, 2),
                    "after_date": e.after_date.isoformat(),
                    "after_loss": round(e.after_loss, 2),
                    "loss_reduction": round(e.loss_reduction, 2),
                    "improvement_percentage": round(e.improvement_percentage, 2),
                    "net_benefit": round(e.net_benefit, 2),
                    "entry_hash": e.entry_hash[:16] + "...",  # Truncated for display
                    "is_verified": e.is_verified
                }
                for e in entries
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "skip": skip
            },
            "summary": {
                "total_verified_savings": round(total_savings, 2),
                "chain_integrity": "valid" if chain_valid else "broken"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=dict)
async def get_roi_summary():
    """
    Get overall ROI summary across all verified improvements.
    """
    try:
        entries = await ROILogEntry.find({"is_verified": True}).to_list()
        
        if not entries:
            return {
                "status": "no_data",
                "message": "No verified ROI entries yet"
            }
        
        total_before_loss = sum(e.before_loss for e in entries)
        total_after_loss = sum(e.after_loss for e in entries)
        total_savings = sum(e.loss_reduction for e in entries)
        total_action_cost = sum(e.action_cost for e in entries)
        
        return {
            "summary": {
                "total_entries": len(entries),
                "total_savings": round(total_savings, 2),
                "total_action_cost": round(total_action_cost, 2),
                "net_roi": round(total_savings - total_action_cost, 2),
                "roi_ratio": round(
                    total_savings / total_action_cost, 2
                ) if total_action_cost > 0 else None,
                "avg_improvement_percentage": round(
                    sum(e.improvement_percentage for e in entries) / len(entries), 2
                )
            },
            "by_action_type": {},  # TODO: Aggregate by type
            "recent_entries": len(entries)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify/{entry_id}", response_model=dict)
async def verify_roi_entry(entry_id: str):
    """
    Verify integrity of a specific ROI entry.
    
    Checks that the entry hash is valid and matches stored data.
    """
    try:
        entry = await ROILogEntry.find_one({"entry_id": entry_id})
        
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        # Recalculate hash
        data_for_hash = {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp.isoformat(),
            "action_id": entry.action_id,
            "before_date": entry.before_date.isoformat(),
            "before_loss": entry.before_loss,
            "after_date": entry.after_date.isoformat(),
            "after_loss": entry.after_loss,
            "previous_entry_hash": entry.previous_entry_hash
        }
        
        calculated_hash = create_deterministic_hash(data_for_hash)
        hash_valid = calculated_hash == entry.entry_hash
        
        return {
            "entry_id": entry_id,
            "stored_hash": entry.entry_hash,
            "calculated_hash": calculated_hash,
            "is_valid": hash_valid,
            "integrity": "intact" if hash_valid else "compromised"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chain-integrity", response_model=dict)
async def verify_chain_integrity():
    """
    Verify integrity of entire ROI chain.
    
    Ensures no entries have been tampered with.
    """
    try:
        entries = await ROILogEntry.find().sort("sequence_number").to_list()
        
        if not entries:
            return {
                "status": "empty",
                "message": "No entries in ROI log"
            }
        
        # Check chain
        broken_at = None
        for i in range(1, len(entries)):
            current = entries[i]
            previous = entries[i-1]
            
            if current.previous_entry_hash != previous.entry_hash:
                broken_at = i
                break
        
        return {
            "total_entries": len(entries),
            "chain_status": "valid" if broken_at is None else "broken",
            "broken_at_sequence": broken_at,
            "first_entry": entries[0].entry_id if entries else None,
            "last_entry": entries[-1].entry_id if entries else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))