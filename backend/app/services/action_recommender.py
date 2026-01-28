"""
PICAM Action Recommender Service

Generates actionable recommendations based on physics calculations.

Principle: Recommend the SMALLEST action that recovers the MOST money.

Each recommendation is:
- Based on physics (not prediction)
- Conservative in estimates
- Actionable and specific
- Traceable to calculations
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import uuid

from app.models.mongodb_models import (
    ActionRecommendation as ActionRecommendationDoc,
    OperationalDataPoint,
    DailyInsight as DailyInsightDoc
)
from app.models.domain import (
    ActionRecommendation,
    FinancialLoss,
    FlowMeasurement,
    LocationType,
    CapacityConstraint
)
from app.core import (
    get_physics_engine,
    LittlesLawCalculator,
    EntropyCalculator,
    LossCalculator
)
from app.utils import now_utc, create_deterministic_hash
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ActionCandidate:
    """Candidate action for recommendation."""
    action_type: str
    description: str
    target_loss_category: str
    estimated_recovery_min: float
    estimated_recovery_max: float
    estimated_cost: float
    confidence: float
    physics_basis: str
    supporting_data: Dict[str, Any]
    
    @property
    def net_benefit(self) -> float:
        return self.estimated_recovery_min - self.estimated_cost
    
    @property
    def roi_ratio(self) -> float:
        if self.estimated_cost <= 0:
            return float('inf') if self.estimated_recovery_min > 0 else 0
        return self.estimated_recovery_min / self.estimated_cost


class ActionRecommenderService:
    """
    Service for generating physics-based action recommendations.
    
    Process:
    1. Analyze operational data
    2. Identify loss points
    3. Generate candidate actions
    4. Rank by ROI
    5. Return top recommendation
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.physics_engine = get_physics_engine()
        self.littles_calc = LittlesLawCalculator()
        self.entropy_calc = EntropyCalculator()
        self.loss_calc = LossCalculator()
    
    async def generate_daily_recommendation(
        self,
        target_date: date,
        location_id: Optional[str] = None
    ) -> Optional[ActionRecommendation]:
        """
        Generate the single best recommendation for a day.
        
        Focuses on the action with highest ROI.
        """
        # Get all data for the day
        query = {"date": target_date}
        if location_id:
            query["location_id"] = location_id
        
        data_points = await OperationalDataPoint.find(query).to_list()
        
        if len(data_points) < 10:
            logger.warning(f"Insufficient data for {target_date}")
            return None
        
        # Group by location
        by_location: Dict[str, List[FlowMeasurement]] = {}
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
            if dp.location_id not in by_location:
                by_location[dp.location_id] = []
            by_location[dp.location_id].append(m)
        
        # Analyze each location and generate candidates
        all_candidates: List[ActionCandidate] = []
        
        for loc_id, measurements in by_location.items():
            # Calculate metrics
            littles_result = self.littles_calc.calculate(measurements)
            entropy = self.entropy_calc.calculate_entropy(measurements, loc_id)
            loss = self.loss_calc.calculate_total_loss(
                measurements=measurements,
                littles_result=littles_result,
                entropy=entropy,
                target_date=target_date
            )
            
            patterns = self.entropy_calc.analyze_patterns(measurements)
            
            # Generate candidates for this location
            candidates = self._generate_candidates(
                location_id=loc_id,
                loss=loss,
                littles_result=littles_result,
                entropy=entropy,
                patterns=patterns
            )
            
            all_candidates.extend(candidates)
        
        if not all_candidates:
            return self._create_default_recommendation(target_date, location_id or "general")
        
        # Sort by ROI and select best
        all_candidates.sort(key=lambda c: c.roi_ratio, reverse=True)
        best = all_candidates[0]
        
        # Create recommendation
        recommendation = ActionRecommendation(
            recommendation_id=f"rec_{target_date.isoformat()}_{uuid.uuid4().hex[:8]}",
            date=target_date,
            location_id=best.supporting_data.get("location_id", "unknown"),
            action_description=best.description,
            action_type=best.action_type,
            min_recoverable_amount=best.estimated_recovery_min,
            max_recoverable_amount=best.estimated_recovery_max,
            action_cost=best.estimated_cost,
            confidence_score=best.confidence,
            physics_justification=best.physics_basis,
            supporting_calculations=best.supporting_data
        )
        
        # Store in database
        await self._store_recommendation(recommendation)
        
        return recommendation
    
    async def get_recommendations(
        self,
        target_date: date,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get all recommendations for a date.
        """
        recs = await ActionRecommendationDoc.find(
            {"date": target_date}
        ).sort("priority").limit(limit).to_list()
        
        return [
            {
                "id": r.recommendation_id,
                "location": r.location_id,
                "type": r.action_type,
                "description": r.action_description,
                "min_recovery": r.min_recoverable_amount,
                "max_recovery": r.max_recoverable_amount,
                "cost": r.action_cost,
                "net_benefit": r.min_net_benefit,
                "roi_ratio": r.roi_ratio,
                "confidence": r.confidence_score,
                "status": r.status
            }
            for r in recs
        ]
    
    async def get_pending_actions(self) -> List[Dict[str, Any]]:
        """
        Get all pending (not yet implemented) actions.
        """
        actions = await ActionRecommendationDoc.find(
            {"status": "pending"}
        ).sort([("date", -1)]).to_list()
        
        return [
            {
                "id": a.recommendation_id,
                "date": a.date.isoformat(),
                "location": a.location_id,
                "type": a.action_type,
                "description": a.action_description,
                "potential_recovery": a.min_recoverable_amount,
                "roi_ratio": a.roi_ratio,
                "confidence": a.confidence_score
            }
            for a in actions
        ]
    
    def _generate_candidates(
        self,
        location_id: str,
        loss: FinancialLoss,
        littles_result,
        entropy,
        patterns: Dict[str, Any]
    ) -> List[ActionCandidate]:
        """
        Generate candidate actions based on loss analysis.
        """
        candidates = []
        
        # 1. Wait time reduction actions
        if loss.wait_time_cost > 50:  # Significant wait cost
            candidates.append(self._create_wait_time_action(
                location_id, loss, littles_result, patterns
            ))
        
        # 2. Capacity actions
        if loss.lost_throughput_revenue > 100:  # Significant capacity loss
            candidates.append(self._create_capacity_action(
                location_id, loss, littles_result
            ))
        
        # 3. Walk-away prevention
        if loss.walkaway_cost > 50:
            candidates.append(self._create_walkaway_action(
                location_id, loss
            ))
        
        # 4. Scheduling optimization
        if loss.idle_time_cost > 30:
            candidates.append(self._create_scheduling_action(
                location_id, loss, patterns
            ))
        
        # 5. Variability reduction
        if entropy and entropy.variance_impact_multiplier > 1.5:
            candidates.append(self._create_variability_action(
                location_id, loss, entropy
            ))
        
        return [c for c in candidates if c is not None]
    
    def _create_wait_time_action(
        self,
        location_id: str,
        loss: FinancialLoss,
        littles_result,
        patterns: Dict[str, Any]
    ) -> ActionCandidate:
        """Create action for wait time reduction."""
        peak_hours = patterns.get("peak_hours", [10, 14, 15])
        num_peak_hours = len(peak_hours)
        
        # Adding one staff during peaks
        labor_cost = self.settings.labor_cost_per_hour * num_peak_hours
        
        # Physics: Adding capacity reduces ρ, which reduces Wq exponentially
        if littles_result and littles_result.rho > 0:
            # Current wait is proportional to ρ/(1-ρ)
            # Adding 20% capacity reduces ρ by ~17%
            current_rho = min(littles_result.rho, 0.99)
            new_rho = current_rho * 0.83  # 17% reduction
            
            wait_reduction_factor = (
                (current_rho / (1 - current_rho)) - 
                (new_rho / (1 - new_rho))
            ) / (current_rho / (1 - current_rho)) if current_rho < 1 else 0.5
            
            wait_reduction_factor = max(0.3, min(0.7, wait_reduction_factor))
        else:
            wait_reduction_factor = 0.35
        
        min_recovery = loss.wait_time_cost * wait_reduction_factor * 0.7
        max_recovery = loss.wait_time_cost * wait_reduction_factor * 1.0
        
        return ActionCandidate(
            action_type="add_staff_peak",
            description=f"Add 1 staff during peak hours ({peak_hours})",
            target_loss_category="wait_time_cost",
            estimated_recovery_min=round(min_recovery, 2),
            estimated_recovery_max=round(max_recovery, 2),
            estimated_cost=round(labor_cost, 2),
            confidence=0.8,
            physics_basis=(
                f"Little's Law: W = L/λ. Adding capacity increases effective μ, "
                f"reducing ρ = λ/μ. Wait time Wq ∝ ρ/(1-ρ) decreases exponentially "
                f"as ρ decreases. Current ρ = {littles_result.rho:.2f if littles_result else 'unknown'}."
            ),
            supporting_data={
                "location_id": location_id,
                "peak_hours": peak_hours,
                "current_wait_cost": loss.wait_time_cost,
                "utilization": littles_result.rho if littles_result else None
            }
        )
    
    def _create_capacity_action(
        self,
        location_id: str,
        loss: FinancialLoss,
        littles_result
    ) -> ActionCandidate:
        """Create action for capacity issues."""
        # Temporary capacity (floater, cross-trained staff)
        action_cost = 150  # Daily cost for temporary capacity
        
        min_recovery = loss.lost_throughput_revenue * 0.4
        max_recovery = loss.lost_throughput_revenue * 0.7
        
        return ActionCandidate(
            action_type="add_capacity",
            description="Add temporary capacity during high-demand periods",
            target_loss_category="lost_throughput_revenue",
            estimated_recovery_min=round(min_recovery, 2),
            estimated_recovery_max=round(max_recovery, 2),
            estimated_cost=action_cost,
            confidence=0.75,
            physics_basis=(
                f"When λ > μ (arrival rate exceeds service rate), queue grows unbounded. "
                f"Adding capacity ensures λ < total μ, capturing previously lost throughput."
            ),
            supporting_data={
                "location_id": location_id,
                "lost_throughput": loss.lost_throughput_count,
                "lost_revenue": loss.lost_throughput_revenue
            }
        )
    
    def _create_walkaway_action(
        self,
        location_id: str,
        loss: FinancialLoss
    ) -> ActionCandidate:
        """Create action for walkaway prevention."""
        # Virtual queue / notification system
        action_cost = 50  # Daily amortized cost
        
        # Reduces abandonment by providing certainty
        min_recovery = loss.walkaway_cost * 0.4
        max_recovery = loss.walkaway_cost * 0.6
        
        return ActionCandidate(
            action_type="queue_management",
            description="Implement virtual queue with wait time notifications",
            target_loss_category="walkaway_cost",
            estimated_recovery_min=round(min_recovery, 2),
            estimated_recovery_max=round(max_recovery, 2),
            estimated_cost=action_cost,
            confidence=0.7,
            physics_basis=(
                f"Erlang-A model: Customer abandonment rate is proportional to "
                f"perceived wait uncertainty. Providing accurate wait estimates "
                f"reduces abandonment by reducing uncertainty, not actual wait time."
            ),
            supporting_data={
                "location_id": location_id,
                "estimated_walkaways": loss.estimated_walkaways,
                "walkaway_cost": loss.walkaway_cost
            }
        )
    
    def _create_scheduling_action(
        self,
        location_id: str,
        loss: FinancialLoss,
        patterns: Dict[str, Any]
    ) -> ActionCandidate:
        """Create action for scheduling optimization."""
        predictability = patterns.get("predictability", "medium")
        
        # Free action - just reschedule
        action_cost = 0
        
        # Effectiveness depends on predictability
        if predictability == "high":
            factor = 0.5
        elif predictability == "medium":
            factor = 0.35
        else:
            factor = 0.2
        
        min_recovery = loss.idle_time_cost * factor * 0.7
        max_recovery = loss.idle_time_cost * factor * 1.0
        
        return ActionCandidate(
            action_type="schedule_optimization",
            description="Realign staff schedules to match demand patterns",
            target_loss_category="idle_time_cost",
            estimated_recovery_min=round(min_recovery, 2),
            estimated_recovery_max=round(max_recovery, 2),
            estimated_cost=action_cost,
            confidence=0.65 if predictability == "high" else 0.5,
            physics_basis=(
                f"Demand patterns show {predictability} predictability. "
                f"Matching capacity to demand reduces idle time (underutilization) "
                f"without affecting service quality. Zero cost, pure efficiency gain."
            ),
            supporting_data={
                "location_id": location_id,
                "idle_cost": loss.idle_time_cost,
                "predictability": predictability,
                "peak_hours": patterns.get("peak_hours", [])
            }
        )
    
    def _create_variability_action(
        self,
        location_id: str,
        loss: FinancialLoss,
        entropy
    ) -> ActionCandidate:
        """Create action for variability reduction."""
        # Appointment system or demand smoothing
        action_cost = 75  # Implementation cost
        
        # Reducing variability reduces the Kingman multiplier
        variance_impact = entropy.variance_impact_multiplier
        potential_reduction = (variance_impact - 1.0) / variance_impact
        
        min_recovery = loss.wait_time_cost * potential_reduction * 0.5
        max_recovery = loss.wait_time_cost * potential_reduction * 0.8
        
        return ActionCandidate(
            action_type="demand_smoothing",
            description="Implement appointment scheduling to reduce arrival variability",
            target_loss_category="wait_time_cost",
            estimated_recovery_min=round(min_recovery, 2),
            estimated_recovery_max=round(max_recovery, 2),
            estimated_cost=action_cost,
            confidence=0.7,
            physics_basis=(
                f"Kingman's Formula: Wq ∝ (Ca² + Cs²)/2. "
                f"Current arrival CV = {entropy.arrival_cv:.2f}, creating multiplier of {variance_impact:.2f}. "
                f"Reducing Ca towards 0 (scheduled arrivals) reduces this multiplier."
            ),
            supporting_data={
                "location_id": location_id,
                "arrival_cv": entropy.arrival_cv,
                "variance_impact": variance_impact,
                "wait_cost": loss.wait_time_cost
            }
        )
    
    def _create_default_recommendation(
        self,
        target_date: date,
        location_id: str
    ) -> ActionRecommendation:
        """Create default recommendation when no specific action identified."""
        return ActionRecommendation(
            recommendation_id=f"rec_{target_date.isoformat()}_{uuid.uuid4().hex[:8]}",
            date=target_date,
            location_id=location_id,
            action_description="Collect more operational data to enable specific recommendations",
            action_type="data_collection",
            min_recoverable_amount=0,
            max_recoverable_amount=0,
            action_cost=0,
            confidence_score=0.5,
            physics_justification="Insufficient data for physics-based recommendation",
            supporting_calculations={}
        )
    
    async def _store_recommendation(
        self,
        recommendation: ActionRecommendation
    ) -> None:
        """Store recommendation in database."""
        doc = ActionRecommendationDoc(
            recommendation_id=recommendation.recommendation_id,
            date=recommendation.date,
            location_id=recommendation.location_id,
            action_description=recommendation.action_description,
            action_type=recommendation.action_type,
            priority=1,
            min_recoverable_amount=recommendation.min_recoverable_amount,
            max_recoverable_amount=recommendation.max_recoverable_amount,
            action_cost=recommendation.action_cost,
            min_net_benefit=recommendation.min_net_benefit,
            roi_ratio=recommendation.roi_ratio,
            confidence_score=recommendation.confidence_score,
            physics_justification=recommendation.physics_justification,
            supporting_calculations=recommendation.supporting_calculations,
            status="pending",
            created_at=now_utc()
        )
        
        await doc.insert()
        logger.info(f"Stored recommendation {recommendation.recommendation_id}")


# Service instance factory
_recommender_service: Optional[ActionRecommenderService] = None


def get_action_recommender() -> ActionRecommenderService:
    """Get or create action recommender instance."""
    global _recommender_service
    if _recommender_service is None:
        _recommender_service = ActionRecommenderService()
    return _recommender_service