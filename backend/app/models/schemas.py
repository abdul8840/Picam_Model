"""
PICAM API Schemas (Pydantic models for request/response)
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


# ============== Enums ==============

class LocationTypeEnum(str, Enum):
    FRONT_DESK = "front_desk"
    RESTAURANT = "restaurant"
    LOBBY = "lobby"
    HOUSEKEEPING = "housekeeping"
    CONCIERGE = "concierge"
    VALET = "valet"
    SPA = "spa"
    GYM = "gym"


# ============== Request Schemas ==============

class OperationalDataInput(BaseModel):
    """Input schema for operational data ingestion."""
    
    timestamp: datetime
    location_id: str = Field(..., min_length=1, max_length=100)
    location_type: LocationTypeEnum
    
    arrival_count: int = Field(ge=0, default=0)
    departure_count: int = Field(ge=0, default=0)
    queue_length: int = Field(ge=0, default=0)
    in_service_count: int = Field(ge=0, default=0)
    
    avg_service_duration_seconds: Optional[float] = Field(ge=0, default=None)
    avg_wait_time_seconds: Optional[float] = Field(ge=0, default=None)
    
    observation_period_seconds: float = Field(ge=1, default=300)
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-01-15T14:30:00Z",
                "location_id": "front_desk_main",
                "location_type": "front_desk",
                "arrival_count": 12,
                "departure_count": 10,
                "queue_length": 5,
                "in_service_count": 3,
                "avg_service_duration_seconds": 180,
                "avg_wait_time_seconds": 240,
                "observation_period_seconds": 300
            }
        }


class BatchOperationalDataInput(BaseModel):
    """Batch input for multiple data points."""
    data_points: List[OperationalDataInput] = Field(..., min_length=1)


class DateRangeQuery(BaseModel):
    """Query parameters for date range."""
    start_date: date
    end_date: date
    location_id: Optional[str] = None
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be >= start_date')
        return v


class ActionCompletionInput(BaseModel):
    """Input when marking an action as completed."""
    action_id: str
    completion_timestamp: datetime
    actual_cost: Optional[float] = Field(ge=0, default=None)
    notes: Optional[str] = None


# ============== Response Schemas ==============

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database_status: str
    timestamp: datetime


class LittlesLawResultResponse(BaseModel):
    """Response for Little's Law calculation."""
    timestamp: datetime
    location_id: str
    
    # Core metrics
    L: float = Field(..., description="Average number in system")
    lambda_rate: float = Field(..., description="Arrival rate per second")
    W: float = Field(..., description="Average time in system (seconds)")
    
    # Queue metrics
    L_q: float = Field(..., description="Average queue length")
    W_q: float = Field(..., description="Average wait time (seconds)")
    
    # Utilization
    rho: float = Field(..., description="System utilization (0-1+)")
    
    # Quality indicators
    data_points_used: int
    is_valid: bool
    is_unstable: bool
    confidence_interval: List[float]


class FinancialLossResponse(BaseModel):
    """Response for financial loss calculation."""
    timestamp: datetime
    location_id: str
    calculation_date: date
    
    # Loss breakdown
    wait_time_cost: float
    lost_throughput_revenue: float
    walkaway_cost: float
    idle_time_cost: float
    overtime_cost: float
    total_loss: float
    
    # Supporting data
    total_wait_time_seconds: float
    lost_throughput_count: int
    estimated_walkaways: int
    
    # Traceability
    calculation_hash: str


class DailyInsightResponse(BaseModel):
    """Response for daily insights."""
    date: date
    generated_at: datetime
    
    # Top loss point
    top_loss_location: str
    top_loss_amount: float
    top_loss_cause: str
    
    # Recommended action
    recommended_action: Dict[str, Any]
    
    # Totals
    total_calculated_loss: float
    total_observations: int
    
    # Breakdown
    loss_by_location: Dict[str, float]
    
    # Quality
    data_completeness: float
    calculation_confidence: float


class ActionRecommendationResponse(BaseModel):
    """Response for action recommendation."""
    recommendation_id: str
    date: date
    location_id: str
    
    action_description: str
    action_type: str
    
    min_recoverable_amount: float
    max_recoverable_amount: float
    action_cost: float
    min_net_benefit: float
    roi_ratio: float
    
    confidence_score: float
    physics_justification: str


class ROILogEntryResponse(BaseModel):
    """Response for ROI log entry."""
    entry_id: str
    timestamp: datetime
    
    action_id: str
    action_description: str
    
    before_date: date
    before_loss: float
    after_date: date
    after_loss: float
    
    loss_reduction: float
    improvement_percentage: float
    
    entry_hash: str
    previous_entry_hash: str
    is_verified: bool = True


class ROILogListResponse(BaseModel):
    """Response for list of ROI log entries."""
    entries: List[ROILogEntryResponse]
    total_entries: int
    total_verified_savings: float
    chain_valid: bool  # Hash chain integrity


class MetricsSummaryResponse(BaseModel):
    """Summary metrics for dashboard."""
    date: date
    
    # Flow metrics
    total_arrivals: int
    total_departures: int
    avg_queue_length: float
    max_queue_length: int
    
    # Time metrics
    avg_wait_time_seconds: float
    max_wait_time_seconds: float
    avg_service_time_seconds: float
    
    # Utilization
    avg_utilization: float
    peak_utilization: float
    
    # Loss metrics
    total_loss: float
    loss_per_customer: float
    
    # By location
    metrics_by_location: Dict[str, Dict[str, float]]


class CalculationAuditResponse(BaseModel):
    """Audit trail for a calculation."""
    calculation_id: str
    calculation_type: str
    timestamp: datetime
    
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    formula_used: str
    
    is_deterministic: bool = True
    is_reproducible: bool = True


# ============== Pagination ==============

class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int