"""
PICAM Configuration Management
All system settings with environment variable support
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """
    PICAM System Configuration
    
    All settings are deterministic and auditable.
    No ML/AI prediction settings - physics-based only.
    """
    
    # Application
    app_name: str = "PICAM"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # MongoDB Connection
    mongodb_url: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string"
    )
    mongodb_database: str = Field(
        default="picam",
        description="Database name"
    )
    
    # Hotel Configuration (Fixed Capacity)
    hotel_name: str = "Default Hotel"
    
    # Service Points Configuration
    front_desk_stations: int = Field(
        default=3,
        description="Number of front desk check-in stations",
        ge=1
    )
    restaurant_capacity: int = Field(
        default=100,
        description="Maximum restaurant seating capacity",
        ge=1
    )
    housekeeping_staff: int = Field(
        default=20,
        description="Number of housekeeping staff",
        ge=1
    )
    
    # Financial Parameters (for loss calculation)
    avg_room_rate: float = Field(
        default=150.0,
        description="Average room rate in currency",
        ge=0
    )
    labor_cost_per_hour: float = Field(
        default=25.0,
        description="Average labor cost per hour",
        ge=0
    )
    customer_time_value_per_minute: float = Field(
        default=2.0,
        description="Conservative value of customer time per minute",
        ge=0
    )
    walkaway_loss_multiplier: float = Field(
        default=3.0,
        description="Multiplier for lost future revenue when customer walks away",
        ge=1
    )
    
    # Physics Engine Settings
    confidence_level: float = Field(
        default=0.95,
        description="Conservative confidence level for calculations",
        ge=0.5,
        le=0.99
    )
    min_data_points_for_calculation: int = Field(
        default=10,
        description="Minimum observations needed for valid calculation",
        ge=5
    )
    
    # Video Processing (Privacy-First)
    video_retention_seconds: int = Field(
        default=0,
        description="Video frame retention - 0 means immediate discard after count",
        ge=0,
        le=0  # Enforce no retention
    )
    
    # API Settings
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Settings are immutable once loaded for determinism.
    """
    return Settings()