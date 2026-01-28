"""
PICAM ROI Tracker Service

Manages the immutable ROI (Return on Investment) log.

Features:
- Hash chain for immutability verification
- Before/after comparison using physics calculations
- Verified financial improvements
- Complete audit trail
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import uuid

from app.models.mongodb_models import (
    ROILogEntry as ROILogEntryDoc,
    ActionRecommendation as ActionRecommendationDoc,
    OperationalDataPoint
)
from app.models.domain import (
    ROILogEntry,
    FinancialLoss,
    FlowMeasurement,
    LocationType,
    CapacityConstraint
)
from app.core import get_physics_engine, LossCalculator
from app.utils import (
    now_utc,
    create_deterministic_hash,
    verify_chain,
    get_date_range
)
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ROIVerificationResult:
    """Result of ROI verification."""
    is_valid: bool
    before_loss: float
    after_loss: float
    loss_reduction: float
    improvement_percentage: float
    confidence: float
    physics_verified: bool
    notes: str


class ROITrackerService:
    """
    Service for tracking and verifying ROI from operational improvements.
    
    Key Features:
    - Immutable log with hash chain
    - Physics-based before/after verification
    - Conservative improvement estimates
    - Complete auditability
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.physics_engine = get_physics_engine()
    
    async def record_action_implementation(
        self,
        action_id: str,
        implementation_date: date,
        actual_cost: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record that an action has been implemented.
        
        This marks the action as implemented and prepares for
        before/after comparison.
        """
        # Find the action recommendation
        action = await ActionRecommendationDoc.find_one(
            {"recommendation_id": action_id}
        )
        
        if not action:
            return {
                "success": False,
                "error": "Action not found"
            }
        
        # Update action status
        action.status = "implemented"
        action.implemented_at = now_utc()
        await action.save()
        
        logger.info(f"Action {action_id} marked as implemented")
        
        return {
            "success": True,
            "action_id": action_id,
            "implementation_date": implementation_date.isoformat(),
            "status": "implemented",
            "message": "Action recorded. Run verification after sufficient data is collected."
        }
    
    async def verify_improvement(
        self,
        action_id: str,
        before_start_date: date,
        before_end_date: date,
        after_start_date: date,
        after_end_date: date
    ) -> ROIVerificationResult:
        """
        Verify improvement by comparing before and after periods.
        
        Uses physics-based calculations for both periods and
        computes the difference.
        """
        # Get the action
        action = await ActionRecommendationDoc.find_one(
            {"recommendation_id": action_id}
        )
        
        if not action:
            return ROIVerificationResult(
                is_valid=False,
                before_loss=0,
                after_loss=0,
                loss_reduction=0,
                improvement_percentage=0,
                confidence=0,
                physics_verified=False,
                notes="Action not found"
            )
        
        location_id = action.location_id
        
        # Get before period data
        before_data = await self._get_period_data(
            location_id, before_start_date, before_end_date
        )
        
        # Get after period data
        after_data = await self._get_period_data(
            location_id, after_start_date, after_end_date
        )
        
        if not before_data or not after_data:
            return ROIVerificationResult(
                is_valid=False,
                before_loss=0,
                after_loss=0,
                loss_reduction=0,
                improvement_percentage=0,
                confidence=0,
                physics_verified=False,
                notes="Insufficient data for comparison"
            )
        
        # Calculate losses for both periods
        loss_calc = LossCalculator()
        
        before_loss = loss_calc.calculate_total_loss(
            measurements=before_data,
            littles_result=None,
            entropy=None,
            target_date=before_start_date
        )
        
        after_loss = loss_calc.calculate_total_loss(
            measurements=after_data,
            littles_result=None,
            entropy=None,
            target_date=after_start_date
        )
        
        # Normalize by number of days
        before_days = (before_end_date - before_start_date).days + 1
        after_days = (after_end_date - after_start_date).days + 1
        
        before_daily = before_loss.total_loss / before_days
        after_daily = after_loss.total_loss / after_days
        
        loss_reduction = before_daily - after_daily
        improvement_pct = (loss_reduction / before_daily * 100) if before_daily > 0 else 0
        
        # Calculate confidence based on data quality
        confidence = min(
            len(before_data) / 100,  # More data = higher confidence
            len(after_data) / 100,
            1.0
        )
        
        return ROIVerificationResult(
            is_valid=True,
            before_loss=round(before_daily, 2),
            after_loss=round(after_daily, 2),
            loss_reduction=round(loss_reduction, 2),
            improvement_percentage=round(improvement_pct, 2),
            confidence=round(confidence, 4),
            physics_verified=True,
            notes=f"Compared {before_days} days before vs {after_days} days after"
        )
    
    async def create_roi_entry(
        self,
        action_id: str,
        verification: ROIVerificationResult,
        action_cost: float
    ) -> Optional[str]:
        """
        Create an immutable ROI log entry.
        
        Entry is added to the hash chain for tamper detection.
        """
        if not verification.is_valid:
            return None
        
        # Get the action
        action = await ActionRecommendationDoc.find_one(
            {"recommendation_id": action_id}
        )
        
        if not action:
            return None
        
        # Get the previous entry for chain
        previous_entry = await ROILogEntryDoc.find_one(
            sort=[("sequence_number", -1)]
        )
        
        previous_hash = previous_entry.entry_hash if previous_entry else "genesis"
        sequence_number = (previous_entry.sequence_number + 1) if previous_entry else 1
        
        # Create entry
        entry_id = f"roi_{uuid.uuid4().hex[:12]}"
        timestamp = now_utc()
        
        # Net benefit
        net_benefit = verification.loss_reduction - action_cost
        
        # Create entry data for hashing
        entry_data = {
            "entry_id": entry_id,
            "timestamp": timestamp.isoformat(),
            "action_id": action_id,
            "before_loss": verification.before_loss,
            "after_loss": verification.after_loss,
            "previous_entry_hash": previous_hash
        }
        
        entry_hash = create_deterministic_hash(entry_data)
        
        # Create document
        doc = ROILogEntryDoc(
            entry_id=entry_id,
            timestamp=timestamp,
            action_id=action_id,
            action_description=action.action_description,
            action_type=action.action_type,
            action_cost=action_cost,
            before_date=action.date,
            before_loss=verification.before_loss,
            before_metrics={"daily_loss": verification.before_loss},
            before_calculation_hash="",
            after_date=action.date + timedelta(days=7),  # Approximate
            after_loss=verification.after_loss,
            after_metrics={"daily_loss": verification.after_loss},
            after_calculation_hash="",
            loss_reduction=verification.loss_reduction,
            improvement_percentage=verification.improvement_percentage,
            net_benefit=net_benefit,
            entry_hash=entry_hash,
            previous_entry_hash=previous_hash,
            sequence_number=sequence_number,
            is_verified=True,
            verification_notes=verification.notes
        )
        
        await doc.insert()
        
        # Update action status
        action.status = "verified"
        action.verified_at = timestamp
        await action.save()
        
        logger.info(f"Created ROI entry {entry_id} with reduction ${verification.loss_reduction}")
        
        return entry_id
    
    async def get_roi_log(
        self,
        limit: int = 50,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Get ROI log entries with chain verification.
        """
        entries = await ROILogEntryDoc.find().sort(
            [("sequence_number", -1)]
        ).skip(skip).limit(limit).to_list()
        
        total = await ROILogEntryDoc.count()
        
        # Calculate totals
        total_savings = sum(
            e.loss_reduction for e in entries if e.loss_reduction > 0
        )
        total_cost = sum(e.action_cost for e in entries)
        total_net = sum(e.net_benefit for e in entries)
        
        # Verify chain integrity
        chain_valid = await self.verify_chain_integrity()
        
        return {
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "timestamp": e.timestamp.isoformat(),
                    "action_id": e.action_id,
                    "action_description": e.action_description,
                    "action_type": e.action_type,
                    "before_loss": e.before_loss,
                    "after_loss": e.after_loss,
                    "loss_reduction": e.loss_reduction,
                    "improvement_percentage": e.improvement_percentage,
                    "action_cost": e.action_cost,
                    "net_benefit": e.net_benefit,
                    "is_verified": e.is_verified,
                    "sequence": e.sequence_number
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
                "total_action_cost": round(total_cost, 2),
                "total_net_benefit": round(total_net, 2),
                "roi_ratio": round(total_savings / total_cost, 2) if total_cost > 0 else None
            },
            "chain_integrity": "valid" if chain_valid else "broken"
        }
    
    async def verify_chain_integrity(self) -> bool:
        """
        Verify the integrity of the entire ROI chain.
        
        Each entry's previous_hash should match the previous entry's hash.
        """
        entries = await ROILogEntryDoc.find().sort(
            [("sequence_number", 1)]
        ).to_list()
        
        if not entries:
            return True
        
        for i in range(1, len(entries)):
            current = entries[i]
            previous = entries[i - 1]
            
            if current.previous_entry_hash != previous.entry_hash:
                logger.error(
                    f"Chain broken at sequence {current.sequence_number}"
                )
                return False
        
        return True
    
    async def verify_single_entry(self, entry_id: str) -> Dict[str, Any]:
        """
        Verify a single ROI entry's hash.
        """
        entry = await ROILogEntryDoc.find_one({"entry_id": entry_id})
        
        if not entry:
            return {"valid": False, "error": "Entry not found"}
        
        # Recalculate hash
        entry_data = {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp.isoformat(),
            "action_id": entry.action_id,
            "before_loss": entry.before_loss,
            "after_loss": entry.after_loss,
            "previous_entry_hash": entry.previous_entry_hash
        }
        
        calculated_hash = create_deterministic_hash(entry_data)
        is_valid = calculated_hash == entry.entry_hash
        
        return {
            "entry_id": entry_id,
            "stored_hash": entry.entry_hash,
            "calculated_hash": calculated_hash,
            "valid": is_valid,
            "integrity": "intact" if is_valid else "compromised"
        }
    
    async def get_cumulative_roi(self) -> Dict[str, Any]:
        """
        Get cumulative ROI statistics.
        """
        entries = await ROILogEntryDoc.find({"is_verified": True}).to_list()
        
        if not entries:
            return {
                "status": "no_data",
                "total_entries": 0
            }
        
        total_savings = sum(e.loss_reduction for e in entries)
        total_cost = sum(e.action_cost for e in entries)
        total_net = sum(e.net_benefit for e in entries)
        
        # Group by action type
        by_type: Dict[str, Dict[str, float]] = {}
        for e in entries:
            if e.action_type not in by_type:
                by_type[e.action_type] = {
                    "count": 0,
                    "savings": 0,
                    "cost": 0
                }
            by_type[e.action_type]["count"] += 1
            by_type[e.action_type]["savings"] += e.loss_reduction
            by_type[e.action_type]["cost"] += e.action_cost
        
        return {
            "status": "available",
            "total_entries": len(entries),
            "cumulative": {
                "total_savings": round(total_savings, 2),
                "total_cost": round(total_cost, 2),
                "total_net_benefit": round(total_net, 2),
                "overall_roi": round(
                    (total_savings / total_cost - 1) * 100, 1
                ) if total_cost > 0 else None
            },
            "by_action_type": {
                action_type: {
                    "count": data["count"],
                    "total_savings": round(data["savings"], 2),
                    "total_cost": round(data["cost"], 2),
                    "roi": round(
                        (data["savings"] / data["cost"] - 1) * 100, 1
                    ) if data["cost"] > 0 else None
                }
                for action_type, data in by_type.items()
            },
            "chain_verified": await self.verify_chain_integrity()
        }
    
    async def _get_period_data(
        self,
        location_id: str,
        start_date: date,
        end_date: date
    ) -> List[FlowMeasurement]:
        """
        Get operational data for a period.
        """
        data_points = await OperationalDataPoint.find({
            "location_id": location_id,
            "date": {"$gte": start_date, "$lte": end_date}
        }).to_list()
        
        return [
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


# Service instance factory
_roi_service: Optional[ROITrackerService] = None


def get_roi_tracker() -> ROITrackerService:
    """Get or create ROI tracker instance."""
    global _roi_service
    if _roi_service is None:
        _roi_service = ROITrackerService()
    return _roi_service