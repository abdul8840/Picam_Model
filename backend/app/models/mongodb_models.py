"""
PICAM MongoDB Document Models (Beanie ODM)
"""

from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


class LocationType(str, Enum):
    FRONT_DESK = "front_desk"
    RESTAURANT = "restaurant"
    LOBBY = "lobby"
    HOUSEKEEPING = "housekeeping"
    CONCIERGE = "concierge"
    VALET = "valet"
    SPA = "spa"
    GYM = "gym"


class OperationalDataPoint(Document):
    """
    Single operational measurement.
    No personal data stored - only counts and durations.
    """
    
    # Timing
    timestamp: Indexed(datetime)
    date: Indexed(date)  # Denormalized for efficient queries
    
    # Location
    location_id: Indexed(str)
    location_type: LocationType
    
    # Flow measurements
    arrival_count: int = 0
    departure_count: int = 0
    queue_length: int = 0
    in_service_count: int = 0
    
    # Duration measurements (seconds)
    avg_service_duration: Optional[float] = None
    avg_wait_time: Optional[float] = None
    
    # Observation period
    observation_period_seconds: float = 300
    
    # Calculated rates (stored for efficiency)
    arrival_rate: Optional[float] = None
    departure_rate: Optional[float] = None
    
    # Data quality
    data_source: str = "manual"  # "manual", "video", "sensor"
    confidence_score: float = 1.0
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "operational_data"
        use_state_management = True


class DailyInsight(Document):
    """
    Daily aggregated insights with top loss point.
    One document per day.
    """
    
    date: Indexed(date, unique=True)
    generated_at: datetime
    
    # Top loss identification
    top_loss_location: str
    top_loss_amount: float
    top_loss_cause: str
    
    # Recommended action
    recommended_action_id: str
    recommended_action_description: str
    recommended_action_potential_recovery: float
    
    # Aggregates
    total_calculated_loss: float
    total_observations: int
    
    # Breakdown
    loss_by_location: Dict[str, float]
    
    # Supporting calculations
    littles_law_results: Dict[str, Any]
    entropy_scores: Dict[str, float]
    
    # Quality metrics
    data_completeness: float
    calculation_confidence: float
    
    # Audit
    calculation_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "daily_insights"


class ROILogEntry(Document):
    """
    Immutable ROI log with hash chain.
    Records verified before/after improvements.
    """
    
    entry_id: Indexed(str, unique=True)
    timestamp: Indexed(datetime)
    
    # Action reference
    action_id: str
    action_description: str
    action_type: str
    action_cost: float
    
    # Before state
    before_date: date
    before_loss: float
    before_metrics: Dict[str, Any]
    before_calculation_hash: str
    
    # After state
    after_date: date
    after_loss: float
    after_metrics: Dict[str, Any]
    after_calculation_hash: str
    
    # Results
    loss_reduction: float
    improvement_percentage: float
    net_benefit: float
    
    # Hash chain for immutability
    entry_hash: Indexed(str, unique=True)
    previous_entry_hash: str
    sequence_number: int
    
    # Verification
    is_verified: bool = True
    verification_notes: Optional[str] = None
    
    class Settings:
        name = "roi_log"


class ActionRecommendation(Document):
    """
    Recommended actions based on physics calculations.
    """
    
    recommendation_id: Indexed(str, unique=True)
    date: Indexed(date)
    location_id: str
    
    # Action details
    action_description: str
    action_type: str
    priority: int = 1  # 1 = highest priority
    
    # Financial projections (conservative)
    min_recoverable_amount: float
    max_recoverable_amount: float
    action_cost: float
    min_net_benefit: float
    roi_ratio: float
    
    # Provability
    confidence_score: float
    physics_justification: str
    supporting_calculations: Dict[str, Any]
    
    # Status
    status: str = "pending"  # "pending", "implemented", "verified", "rejected"
    implemented_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "action_recommendations"


class SystemConfiguration(Document):
    """
    System configuration with audit trail.
    """
    
    config_key: Indexed(str, unique=True)
    config_value: Any
    
    # Capacity constraints
    description: str
    unit: Optional[str] = None
    
    # Audit
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = "system"
    previous_value: Optional[Any] = None
    
    class Settings:
        name = "system_configuration"


class CalculationAuditLog(Document):
    """
    Audit log for all calculations.
    Enables full traceability and reproducibility.
    """
    
    calculation_id: Indexed(str)
    calculation_type: Indexed(str)  # "littles_law", "loss", "entropy"
    timestamp: Indexed(datetime)
    
    # Inputs (complete for reproducibility)
    input_data: Dict[str, Any]
    input_hash: str
    
    # Configuration at time of calculation
    configuration_snapshot: Dict[str, Any]
    
    # Outputs
    output_data: Dict[str, Any]
    output_hash: str
    
    # Formula/method documentation
    formula_used: str
    assumptions: List[str]
    
    # Quality
    is_deterministic: bool = True
    is_reproducible: bool = True
    
    # Error handling
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    class Settings:
        name = "calculation_audit_log"


class VideoProcessingLog(Document):
    """
    Log of video processing events.
    NO video data stored - only metadata about processing.
    """
    
    processing_id: Indexed(str)
    timestamp: Indexed(datetime)
    
    # Source info (no identifiable data)
    camera_id: str
    location_id: str
    
    # Processing details
    frames_processed: int
    processing_duration_ms: float
    
    # Extracted counts only
    detected_count: int
    confidence_score: float
    
    # Privacy confirmation
    frames_discarded: bool = True
    no_personal_data_stored: bool = True
    
    # Output
    output_data_point_id: Optional[str] = None
    
    class Settings:
        name = "video_processing_log"