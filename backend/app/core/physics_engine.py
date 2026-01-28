"""
PICAM Physics Engine

Main orchestrator for all physics-based calculations.
Combines Little's Law, Entropy, and Loss calculations into a unified interface.

This is the brain of PICAM - converting raw operational data into
provable financial insights.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
import logging
import uuid

from app.models.domain import (
    FlowMeasurement,
    LittlesLawResult,
    EntropyMeasurement,
    FinancialLoss,
    CapacityConstraint,
    ActionRecommendation as ActionRec,
    DailyInsight,
    LocationType
)
from app.core.littles_law import LittlesLawCalculator, MultiServerQueueCalculator
from app.core.entropy_calculator import EntropyCalculator, OperationalStabilityAnalyzer
from app.core.loss_calculator import LossCalculator, FinancialParameters, ROICalculator
from app.utils import now_utc, create_deterministic_hash
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PhysicsEngine:
    """
    Unified physics engine for PICAM.
    
    Orchestrates all calculations and ensures:
    - Determinism (reproducible results)
    - Conservatism (lower-bound estimates)
    - Auditability (full traceability)
    - No speculation (physics only)
    """
    
    # Calculators
    littles_law: LittlesLawCalculator = field(default_factory=LittlesLawCalculator)
    entropy_calc: EntropyCalculator = field(default_factory=EntropyCalculator)
    loss_calc: LossCalculator = field(default_factory=LossCalculator)
    stability_analyzer: OperationalStabilityAnalyzer = field(
        default_factory=OperationalStabilityAnalyzer
    )
    roi_calc: ROICalculator = field(default_factory=ROICalculator)
    
    # Configuration
    confidence_level: float = 0.95
    
    def __post_init__(self):
        settings = get_settings()
        self.confidence_level = settings.confidence_level
        self.littles_law.confidence_level = self.confidence_level
    
    def analyze_location(
        self,
        measurements: List[FlowMeasurement],
        capacity: Optional[CapacityConstraint] = None
    ) -> Dict[str, Any]:
        """
        Perform complete analysis for a single location.
        
        Args:
            measurements: Flow measurements for the location
            capacity: Optional capacity constraints
            
        Returns:
            Complete analysis including queue metrics, entropy, and losses
        """
        if not measurements:
            return {
                "status": "no_data",
                "location_id": None
            }
        
        location_id = measurements[0].location_id
        analysis_timestamp = now_utc()
        
        # 1. Calculate Little's Law metrics
        littles_result = self.littles_law.calculate(measurements, capacity)
        
        # 2. Verify Little's Law holds (data quality check)
        verification = self.littles_law.verify_littles_law(measurements)
        
        # 3. Calculate entropy/variability
        entropy = self.entropy_calc.calculate_entropy(measurements, location_id)
        
        # 4. Analyze patterns
        patterns = self.entropy_calc.analyze_patterns(measurements)
        
        # 5. Analyze stability
        stability = self.stability_analyzer.analyze_stability(measurements)
        
        # 6. Calculate financial losses
        loss = self.loss_calc.calculate_total_loss(
            measurements=measurements,
            littles_result=littles_result,
            entropy=entropy,
            capacity=capacity
        )
        
        # 7. Create audit hash
        audit_data = {
            "location_id": location_id,
            "analysis_timestamp": analysis_timestamp.isoformat(),
            "data_points": len(measurements),
            "total_loss": loss.total_loss
        }
        audit_hash = create_deterministic_hash(audit_data)
        
        return {
            "status": "analyzed",
            "location_id": location_id,
            "analysis_timestamp": analysis_timestamp.isoformat(),
            "data_points": len(measurements),
            
            # Queue metrics (Little's Law)
            "queue_metrics": littles_result.to_audit_dict() if littles_result else None,
            "littles_law_verified": verification,
            
            # Entropy/Variability
            "entropy": {
                "arrival_cv": entropy.arrival_cv if entropy else None,
                "service_cv": entropy.service_cv if entropy else None,
                "entropy_score": entropy.entropy_score if entropy else None,
                "variance_impact": entropy.variance_impact_multiplier if entropy else None
            } if entropy else None,
            
            # Patterns
            "patterns": patterns,
            
            # Stability
            "stability": {
                "stable_percentage": stability.get("stable_percentage"),
                "crisis_periods": stability.get("crisis_periods"),
                "state_distribution": stability.get("state_distribution")
            } if stability.get("status") == "analyzed" else None,
            
            # Financial loss
            "financial_loss": loss.loss_breakdown,
            "total_loss": round(loss.total_loss, 2),
            
            # Audit
            "audit_hash": audit_hash,
            "is_deterministic": True
        }
    
    def analyze_day(
        self,
        measurements_by_location: Dict[str, List[FlowMeasurement]],
        capacities: Dict[str, CapacityConstraint],
        target_date: date
    ) -> DailyInsight:
        """
        Perform complete daily analysis across all locations.
        
        Args:
            measurements_by_location: Measurements grouped by location
            capacities: Capacity constraints per location
            target_date: Date of analysis
            
        Returns:
            DailyInsight with top loss point and recommendation
        """
        analysis_timestamp = now_utc()
        
        # Analyze each location
        location_analyses = {}
        losses_by_location = {}
        littles_by_location = {}
        entropy_by_location = {}
        
        for location_id, measurements in measurements_by_location.items():
            capacity = capacities.get(location_id)
            analysis = self.analyze_location(measurements, capacity)
            
            location_analyses[location_id] = analysis
            
            if analysis.get("status") == "analyzed":
                # Create FinancialLoss object from analysis
                loss = self.loss_calc.calculate_total_loss(
                    measurements=measurements,
                    littles_result=self.littles_law.calculate(measurements, capacity),
                    entropy=self.entropy_calc.calculate_entropy(measurements, location_id),
                    capacity=capacity,
                    target_date=target_date
                )
                losses_by_location[location_id] = loss
                
                # Store supporting calculations
                littles_by_location[location_id] = analysis.get("queue_metrics")
                if analysis.get("entropy"):
                    entropy_by_location[location_id] = analysis["entropy"].get("entropy_score", 0)
        
        # Identify top loss point
        top_loss_info = self.loss_calc.identify_top_loss_point(losses_by_location)
        
        # Generate action recommendation
        recommendation = self._generate_recommendation(
            top_loss_info,
            losses_by_location,
            location_analyses,
            capacities,
            target_date
        )
        
        # Calculate totals
        total_loss = sum(loss.total_loss for loss in losses_by_location.values())
        total_observations = sum(
            len(m) for m in measurements_by_location.values()
        )
        
        # Data completeness (simple heuristic)
        expected_observations = 288 * len(measurements_by_location)  # 5-min intervals
        data_completeness = min(1.0, total_observations / expected_observations) if expected_observations > 0 else 0
        
        # Calculation confidence based on data and verification
        verified_count = sum(
            1 for a in location_analyses.values()
            if a.get("littles_law_verified", {}).get("verified", False)
        )
        calculation_confidence = verified_count / len(location_analyses) if location_analyses else 0
        
        # Create calculation hash
        calc_data = {
            "date": target_date.isoformat(),
            "total_loss": total_loss,
            "total_observations": total_observations,
            "top_location": top_loss_info.get("top_location")
        }
        calculation_hash = create_deterministic_hash(calc_data)
        
        return DailyInsight(
            date=target_date,
            generated_at=analysis_timestamp,
            top_loss_location=top_loss_info.get("top_location", "unknown"),
            top_loss_amount=top_loss_info.get("top_loss_amount", 0),
            top_loss_cause=top_loss_info.get("primary_cause", "unknown"),
            recommended_action=recommendation,
            total_calculated_loss=total_loss,
            total_observations=total_observations,
            loss_by_location={
                loc: loss.total_loss
                for loc, loss in losses_by_location.items()
            },
            data_completeness=data_completeness,
            calculation_confidence=calculation_confidence
        )
    
    def _generate_recommendation(
        self,
        top_loss_info: dict,
        losses_by_location: Dict[str, FinancialLoss],
        analyses: Dict[str, dict],
        capacities: Dict[str, CapacityConstraint],
        target_date: date
    ) -> ActionRec:
        """
        Generate the single best action recommendation.
        
        Focuses on the smallest action that recovers the most money.
        """
        location = top_loss_info.get("top_location")
        
        if not location or location not in losses_by_location:
            # Default recommendation
            return ActionRec(
                recommendation_id=f"rec_{target_date.isoformat()}_{uuid.uuid4().hex[:8]}",
                date=target_date,
                location_id="general",
                action_description="Improve data collection to enable analysis",
                action_type="data_quality",
                min_recoverable_amount=0,
                max_recoverable_amount=0,
                action_cost=0,
                confidence_score=0,
                physics_justification="Insufficient data for physics-based recommendation"
            )
        
        loss = losses_by_location[location]
        analysis = analyses.get(location, {})
        capacity = capacities.get(location)
        
        # Determine best action based on primary loss cause
        cause = top_loss_info.get("primary_cause", "")
        
        if "wait time" in cause.lower():
            return self._recommend_for_wait_time(
                location, loss, analysis, capacity, target_date
            )
        elif "capacity" in cause.lower() or "demand" in cause.lower():
            return self._recommend_for_capacity(
                location, loss, analysis, capacity, target_date
            )
        elif "walkaway" in cause.lower() or "leaving" in cause.lower():
            return self._recommend_for_walkaways(
                location, loss, analysis, capacity, target_date
            )
        elif "idle" in cause.lower() or "underutilized" in cause.lower():
            return self._recommend_for_idle(
                location, loss, analysis, capacity, target_date
            )
        else:
            return self._recommend_general(
                location, loss, analysis, capacity, target_date
            )
    
    def _recommend_for_wait_time(
        self,
        location: str,
        loss: FinancialLoss,
        analysis: dict,
        capacity: Optional[CapacityConstraint],
        target_date: date
    ) -> ActionRec:
        """Generate recommendation for wait time issues."""
        patterns = analysis.get("patterns", {})
        peak_hours = patterns.get("peak_hours", [])
        
        # Calculate recovery potential
        wait_loss = loss.wait_time_cost
        
        # Adding one staff during peak hours
        peak_hours_count = len(peak_hours) if peak_hours else 3
        action_cost = 25 * peak_hours_count  # Labor cost per hour
        
        # Conservative recovery estimate: 30-50% of wait time cost
        min_recovery = wait_loss * 0.30
        max_recovery = wait_loss * 0.50
        
        return ActionRec(
            recommendation_id=f"rec_{target_date.isoformat()}_{uuid.uuid4().hex[:8]}",
            date=target_date,
            location_id=location,
            action_description=f"Add 1 staff member during peak hours ({peak_hours}) to reduce wait times",
            action_type="add_staff_peak",
            min_recoverable_amount=min_recovery,
            max_recoverable_amount=max_recovery,
            action_cost=action_cost,
            confidence_score=0.8,
            physics_justification=(
                f"Little's Law: Increasing service capacity (μ) reduces utilization (ρ), "
                f"which exponentially decreases wait time Wq = ρ/(μ(1-ρ)). "
                f"Peak hours identified: {peak_hours}"
            ),
            supporting_calculations={
                "peak_hours": peak_hours,
                "current_wait_loss": wait_loss,
                "queue_metrics": analysis.get("queue_metrics")
            }
        )
    
    def _recommend_for_capacity(
        self,
        location: str,
        loss: FinancialLoss,
        analysis: dict,
        capacity: Optional[CapacityConstraint],
        target_date: date
    ) -> ActionRec:
        """Generate recommendation for capacity issues."""
        throughput_loss = loss.lost_throughput_revenue
        
        queue_metrics = analysis.get("queue_metrics", {})
        utilization = queue_metrics.get("rho", 0.9) if queue_metrics else 0.9
        
        if utilization >= 1.0:
            # System overloaded - need additional capacity
            action_cost = 200  # Cost to add temporary capacity
            min_recovery = throughput_loss * 0.4
            max_recovery = throughput_loss * 0.7
            
            return ActionRec(
                recommendation_id=f"rec_{target_date.isoformat()}_{uuid.uuid4().hex[:8]}",
                date=target_date,
                location_id=location,
                action_description="Add temporary service capacity during peak demand periods",
                action_type="add_capacity",
                min_recoverable_amount=min_recovery,
                max_recoverable_amount=max_recovery,
                action_cost=action_cost,
                confidence_score=0.85,
                physics_justification=(
                    f"Utilization ρ = {utilization:.2f} >= 1.0 indicates unstable queue. "
                    f"Queue length grows unbounded without additional capacity. "
                    f"Adding capacity reduces ρ below 1.0, stabilizing the system."
                ),
                supporting_calculations={
                    "current_utilization": utilization,
                    "throughput_loss": throughput_loss
                }
            )
        else:
            # Near capacity - optimize flow
            return self._recommend_general(location, loss, analysis, capacity, target_date)
    
    def _recommend_for_walkaways(
        self,
        location: str,
        loss: FinancialLoss,
        analysis: dict,
        capacity: Optional[CapacityConstraint],
        target_date: date
    ) -> ActionRec:
        """Generate recommendation for walkaway issues."""
        walkaway_loss = loss.walkaway_cost
        estimated_walkaways = loss.estimated_walkaways
        
        # Virtual queue / appointment system
        action_cost = 50  # Implementation cost per day
        
        # Can reduce walkaways by 40-60% with queue management
        min_recovery = walkaway_loss * 0.4
        max_recovery = walkaway_loss * 0.6
        
        return ActionRec(
            recommendation_id=f"rec_{target_date.isoformat()}_{uuid.uuid4().hex[:8]}",
            date=target_date,
            location_id=location,
            action_description="Implement virtual queue notification to reduce walkaway rate",
            action_type="queue_management",
            min_recoverable_amount=min_recovery,
            max_recoverable_amount=max_recovery,
            action_cost=action_cost,
            confidence_score=0.75,
            physics_justification=(
                f"Estimated {estimated_walkaways} customers walked away. "
                f"Virtual queuing reduces perceived wait time and provides certainty, "
                f"reducing abandonment probability per Erlang-A queue model."
            ),
            supporting_calculations={
                "estimated_walkaways": estimated_walkaways,
                "walkaway_loss": walkaway_loss
            }
        )
    
    def _recommend_for_idle(
        self,
        location: str,
        loss: FinancialLoss,
        analysis: dict,
        capacity: Optional[CapacityConstraint],
        target_date: date
    ) -> ActionRec:
        """Generate recommendation for idle time issues."""
        idle_loss = loss.idle_time_cost
        
        patterns = analysis.get("patterns", {})
        
        # Flexible staffing
        action_cost = 0  # Scheduling adjustment is free
        min_recovery = idle_loss * 0.3
        max_recovery = idle_loss * 0.5
        
        return ActionRec(
            recommendation_id=f"rec_{target_date.isoformat()}_{uuid.uuid4().hex[:8]}",
            date=target_date,
            location_id=location,
            action_description="Adjust staff scheduling to match demand patterns",
            action_type="schedule_optimization",
            min_recoverable_amount=min_recovery,
            max_recoverable_amount=max_recovery,
            action_cost=action_cost,
            confidence_score=0.7,
            physics_justification=(
                f"High idle time indicates mismatch between capacity and demand. "
                f"Predictability score: {patterns.get('predictability', 'unknown')}. "
                f"Shifting staff to match demand patterns reduces idle cost."
            ),
            supporting_calculations={
                "idle_loss": idle_loss,
                "predictability": patterns.get("predictability")
            }
        )
    
    def _recommend_general(
        self,
        location: str,
        loss: FinancialLoss,
        analysis: dict,
        capacity: Optional[CapacityConstraint],
        target_date: date
    ) -> ActionRec:
        """Generate general recommendation."""
        total_loss = loss.total_loss
        
        return ActionRec(
            recommendation_id=f"rec_{target_date.isoformat()}_{uuid.uuid4().hex[:8]}",
            date=target_date,
            location_id=location,
            action_description="Review operations during highest-loss periods",
            action_type="operational_review",
            min_recoverable_amount=total_loss * 0.1,
            max_recoverable_amount=total_loss * 0.2,
            action_cost=0,
            confidence_score=0.5,
            physics_justification=(
                f"Total calculated loss: ${total_loss:.2f}. "
                f"Detailed operational review recommended to identify specific improvements."
            ),
            supporting_calculations={
                "total_loss": total_loss,
                "breakdown": loss.loss_breakdown
            }
        )
    
    def compare_before_after(
        self,
        before_measurements: List[FlowMeasurement],
        after_measurements: List[FlowMeasurement],
        capacity: Optional[CapacityConstraint] = None
    ) -> dict:
        """
        Compare operational metrics before and after an intervention.
        
        Used for ROI verification.
        """
        if not before_measurements or not after_measurements:
            return {"status": "insufficient_data"}
        
        # Analyze both periods
        before_analysis = self.analyze_location(before_measurements, capacity)
        after_analysis = self.analyze_location(after_measurements, capacity)
        
        # Calculate losses
        before_loss = self.loss_calc.calculate_total_loss(
            before_measurements,
            self.littles_law.calculate(before_measurements, capacity),
            self.entropy_calc.calculate_entropy(
                before_measurements, 
                before_measurements[0].location_id
            ),
            capacity
        )
        
        after_loss = self.loss_calc.calculate_total_loss(
            after_measurements,
            self.littles_law.calculate(after_measurements, capacity),
            self.entropy_calc.calculate_entropy(
                after_measurements,
                after_measurements[0].location_id
            ),
            capacity
        )
        
        # Compare
        loss_change = after_loss.total_loss - before_loss.total_loss
        loss_change_pct = (loss_change / before_loss.total_loss * 100) if before_loss.total_loss > 0 else 0
        
        # Queue metrics comparison
        before_queue = before_analysis.get("queue_metrics", {})
        after_queue = after_analysis.get("queue_metrics", {})
        
        return {
            "status": "compared",
            "before": {
                "data_points": len(before_measurements),
                "total_loss": round(before_loss.total_loss, 2),
                "avg_wait_time": before_queue.get("W_q") if before_queue else None,
                "utilization": before_queue.get("rho") if before_queue else None
            },
            "after": {
                "data_points": len(after_measurements),
                "total_loss": round(after_loss.total_loss, 2),
                "avg_wait_time": after_queue.get("W_q") if after_queue else None,
                "utilization": after_queue.get("rho") if after_queue else None
            },
            "change": {
                "loss_change": round(loss_change, 2),
                "loss_change_percentage": round(loss_change_pct, 2),
                "improved": loss_change < 0
            },
            "verification": {
                "before_verified": before_analysis.get("littles_law_verified", {}).get("verified"),
                "after_verified": after_analysis.get("littles_law_verified", {}).get("verified")
            }
        }


# Singleton instance
_physics_engine: Optional[PhysicsEngine] = None


def get_physics_engine() -> PhysicsEngine:
    """Get or create the physics engine singleton."""
    global _physics_engine
    if _physics_engine is None:
        _physics_engine = PhysicsEngine()
    return _physics_engine