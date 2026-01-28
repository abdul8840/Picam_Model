"""
PICAM Domain Models
Pure Python dataclasses representing core business concepts.
Physics-based, deterministic, fully traceable.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum
import hashlib
import json


class LocationType(str, Enum):
    """Types of operational locations in a hotel."""
    FRONT_DESK = "front_desk"
    RESTAURANT = "restaurant"
    LOBBY = "lobby"
    HOUSEKEEPING = "housekeeping"
    CONCIERGE = "concierge"
    VALET = "valet"
    SPA = "spa"
    GYM = "gym"


class MetricType(str, Enum):
    """Types of operational metrics captured."""
    ARRIVAL_COUNT = "arrival_count"
    DEPARTURE_COUNT = "departure_count"
    QUEUE_LENGTH = "queue_length"
    SERVICE_DURATION = "service_duration"
    WAIT_TIME = "wait_time"
    UTILIZATION = "utilization"
    DENSITY = "density"


@dataclass(frozen=True)
class CapacityConstraint:
    """
    Fixed capacity constraint for a service point.
    Immutable - represents physical reality.
    """
    location_type: LocationType
    max_servers: int  # Number of service points (e.g., front desk stations)
    max_queue_capacity: int  # Physical queue limit
    target_utilization: float = 0.85  # Target utilization before stress
    
    def __post_init__(self):
        assert 0 < self.max_servers, "Must have at least 1 server"
        assert 0 < self.max_queue_capacity, "Must have queue capacity"
        assert 0 < self.target_utilization <= 1.0, "Utilization must be (0, 1]"


@dataclass
class FlowMeasurement:
    """
    Single measurement of flow at a point in time.
    Represents observed, factual data.
    """
    timestamp: datetime
    location_id: str
    location_type: LocationType
    
    # Core measurements
    arrival_count: int = 0  # λ - arrivals in period
    departure_count: int = 0  # μ - departures in period
    queue_length: int = 0  # L - people waiting
    in_service_count: int = 0  # Currently being served
    
    # Duration measurements (seconds)
    avg_service_duration: Optional[float] = None  # 1/μ
    avg_wait_time: Optional[float] = None  # W_q
    
    # Period for rate calculations
    observation_period_seconds: float = 300  # 5-minute default
    
    @property
    def arrival_rate(self) -> float:
        """λ - arrivals per second"""
        if self.observation_period_seconds <= 0:
            return 0.0
        return self.arrival_count / self.observation_period_seconds
    
    @property
    def departure_rate(self) -> float:
        """μ - departures per second"""
        if self.observation_period_seconds <= 0:
            return 0.0
        return self.departure_count / self.observation_period_seconds
    
    @property
    def total_in_system(self) -> int:
        """L - total in system (queue + service)"""
        return self.queue_length + self.in_service_count


@dataclass
class LittlesLawResult:
    """
    Result of Little's Law calculation: L = λW
    
    L = average number in system
    λ = arrival rate
    W = average time in system
    """
    timestamp: datetime
    location_id: str
    
    # Little's Law components
    L: float  # Average number in system
    lambda_rate: float  # Arrival rate (per second)
    W: float  # Average time in system (seconds)
    
    # Queue-specific (L_q = λW_q)
    L_q: float  # Average queue length
    W_q: float  # Average wait time (seconds)
    
    # Service-specific
    rho: float  # Utilization (ρ = λ / μ)
    
    # Calculation metadata
    data_points_used: int
    confidence_interval_lower: float
    confidence_interval_upper: float
    
    @property
    def is_valid(self) -> bool:
        """Check if calculation meets minimum requirements."""
        return self.data_points_used >= 10 and self.lambda_rate > 0
    
    @property
    def is_unstable(self) -> bool:
        """System is unstable when utilization >= 1"""
        return self.rho >= 1.0
    
    def to_audit_dict(self) -> dict:
        """Create auditable dictionary for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "location_id": self.location_id,
            "L": round(self.L, 4),
            "lambda_rate": round(self.lambda_rate, 6),
            "W": round(self.W, 2),
            "L_q": round(self.L_q, 4),
            "W_q": round(self.W_q, 2),
            "rho": round(self.rho, 4),
            "data_points_used": self.data_points_used,
            "confidence_interval": [
                round(self.confidence_interval_lower, 4),
                round(self.confidence_interval_upper, 4)
            ],
            "is_valid": self.is_valid,
            "is_unstable": self.is_unstable
        }


@dataclass
class EntropyMeasurement:
    """
    Operational entropy (variability/unpredictability).
    Higher entropy = higher cost due to variability.
    Based on coefficient of variation and distribution analysis.
    """
    timestamp: datetime
    location_id: str
    
    # Variability measures
    arrival_cv: float  # Coefficient of variation in arrivals
    service_cv: float  # Coefficient of variation in service time
    
    # Entropy score (0-1, higher = more disorder)
    entropy_score: float
    
    # Impact factors
    variance_impact_multiplier: float  # How much variability increases wait
    
    @property
    def cost_multiplier(self) -> float:
        """
        Kingman's formula influence: 
        Wait time ∝ (Ca² + Cs²) / 2
        """
        return (self.arrival_cv**2 + self.service_cv**2) / 2


@dataclass
class FinancialLoss:
    """
    Calculated financial loss - conservative lower bound.
    Every field is traceable to physics calculations.
    """
    timestamp: datetime
    location_id: str
    calculation_date: date
    
    # Time-based losses
    total_wait_time_seconds: float  # Sum of all customer wait time
    wait_time_cost: float  # Monetary value of wait time
    
    # Capacity-based losses
    lost_throughput_count: int  # Customers who couldn't be served
    lost_throughput_revenue: float  # Revenue from lost throughput
    
    # Walk-away losses
    estimated_walkaways: int  # Customers who left queue
    walkaway_cost: float  # Direct + future lost revenue
    
    # Inefficiency losses
    idle_time_seconds: float  # Server idle time
    idle_time_cost: float  # Cost of idle labor
    
    # Overtime/stress losses
    overtime_hours: float
    overtime_cost: float
    
    @property
    def total_loss(self) -> float:
        """Total conservative lower-bound loss."""
        return (
            self.wait_time_cost +
            self.lost_throughput_revenue +
            self.walkaway_cost +
            self.idle_time_cost +
            self.overtime_cost
        )
    
    @property
    def loss_breakdown(self) -> dict:
        """Breakdown by category for reporting."""
        return {
            "wait_time_cost": round(self.wait_time_cost, 2),
            "lost_throughput_revenue": round(self.lost_throughput_revenue, 2),
            "walkaway_cost": round(self.walkaway_cost, 2),
            "idle_time_cost": round(self.idle_time_cost, 2),
            "overtime_cost": round(self.overtime_cost, 2),
            "total_loss": round(self.total_loss, 2)
        }
    
    def create_hash(self) -> str:
        """Create deterministic hash for audit trail."""
        data = json.dumps({
            "timestamp": self.timestamp.isoformat(),
            "location_id": self.location_id,
            "calculation_date": self.calculation_date.isoformat(),
            "total_wait_time_seconds": self.total_wait_time_seconds,
            "lost_throughput_count": self.lost_throughput_count,
            "estimated_walkaways": self.estimated_walkaways,
            "total_loss": self.total_loss
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class ActionRecommendation:
    """
    Single smallest action to recover most money.
    Based on physics calculations, not predictions.
    """
    recommendation_id: str
    date: date
    location_id: str
    
    # The action
    action_description: str
    action_type: str  # "add_staff", "extend_hours", "redistribute", etc.
    
    # Expected recovery (conservative)
    min_recoverable_amount: float  # Conservative lower bound
    max_recoverable_amount: float  # Upper estimate
    
    # Cost of action
    action_cost: float
    
    # Net benefit
    @property
    def min_net_benefit(self) -> float:
        return self.min_recoverable_amount - self.action_cost
    
    @property
    def roi_ratio(self) -> float:
        if self.action_cost <= 0:
            return float('inf') if self.min_recoverable_amount > 0 else 0
        return self.min_recoverable_amount / self.action_cost
    
    # Provability score (0-1)
    confidence_score: float
    
    # Physics basis
    physics_justification: str
    supporting_calculations: dict = field(default_factory=dict)


@dataclass
class ROILogEntry:
    """
    Immutable ROI log entry.
    Records verified before/after measurements.
    """
    entry_id: str
    timestamp: datetime
    
    # The action taken
    action_id: str
    action_description: str
    
    # Before measurements (from historical data)
    before_date: date
    before_loss: float
    before_metrics: dict
    
    # After measurements (from new data)
    after_date: date
    after_loss: float
    after_metrics: dict
    
    # Verified improvement
    @property
    def loss_reduction(self) -> float:
        return self.before_loss - self.after_loss
    
    @property
    def improvement_percentage(self) -> float:
        if self.before_loss <= 0:
            return 0.0
        return (self.loss_reduction / self.before_loss) * 100
    
    # Immutability hash
    entry_hash: str = ""
    previous_entry_hash: str = ""  # Chain for immutability
    
    def calculate_hash(self) -> str:
        """Calculate hash for this entry."""
        data = json.dumps({
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "action_id": self.action_id,
            "before_date": self.before_date.isoformat(),
            "before_loss": self.before_loss,
            "after_date": self.after_date.isoformat(),
            "after_loss": self.after_loss,
            "previous_entry_hash": self.previous_entry_hash
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class DailyInsight:
    """
    Daily summary with single most provable loss point.
    """
    date: date
    generated_at: datetime
    
    # Most provable loss point
    top_loss_location: str
    top_loss_amount: float
    top_loss_cause: str
    
    # Recommended action
    recommended_action: ActionRecommendation
    
    # Daily totals
    total_calculated_loss: float
    total_observations: int
    
    # Breakdown by location
    loss_by_location: dict  # location_id -> loss amount
    
    # Quality metrics
    data_completeness: float  # 0-1
    calculation_confidence: float  # 0-1
    
    def to_summary_dict(self) -> dict:
        """Create summary for dashboard display."""
        return {
            "date": self.date.isoformat(),
            "top_loss": {
                "location": self.top_loss_location,
                "amount": round(self.top_loss_amount, 2),
                "cause": self.top_loss_cause
            },
            "recommended_action": {
                "description": self.recommended_action.action_description,
                "potential_recovery": round(
                    self.recommended_action.min_recoverable_amount, 2
                ),
                "confidence": round(
                    self.recommended_action.confidence_score, 2
                )
            },
            "total_loss": round(self.total_calculated_loss, 2),
            "data_quality": round(self.data_completeness, 2)
        }