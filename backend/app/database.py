"""
PICAM Database Connection and Initialization
MongoDB with Motor async driver
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from beanie import init_beanie
from typing import Optional
import logging

from app.config import get_settings
from app.models.mongodb_models import (
    OperationalDataPoint,
    DailyInsight,
    ROILogEntry,
    ActionRecommendation,
    SystemConfiguration,
    CalculationAuditLog
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages MongoDB connection lifecycle.
    Ensures all data operations are auditable.
    """
    
    _client: Optional[AsyncIOMotorClient] = None
    _database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls) -> None:
        """
        Initialize MongoDB connection and Beanie ODM.
        """
        settings = get_settings()
        
        logger.info(f"Connecting to MongoDB: {settings.mongodb_url}")
        
        cls._client = AsyncIOMotorClient(
            settings.mongodb_url,
            maxPoolSize=50,
            minPoolSize=10,
            serverSelectionTimeoutMS=5000
        )
        
        cls._database = cls._client[settings.mongodb_database]
        
        # Initialize Beanie with all document models
        await init_beanie(
            database=cls._database,
            document_models=[
                OperationalDataPoint,
                DailyInsight,
                ROILogEntry,
                ActionRecommendation,
                SystemConfiguration,
                CalculationAuditLog
            ]
        )
        
        # Create indexes for performance
        await cls._create_indexes()
        
        logger.info("MongoDB connection established successfully")
    
    @classmethod
    async def _create_indexes(cls) -> None:
        """
        Create database indexes for query performance.
        """
        # Operational data: query by timestamp and location
        await OperationalDataPoint.get_motor_collection().create_index(
            [("timestamp", -1), ("location_id", 1)]
        )
        await OperationalDataPoint.get_motor_collection().create_index(
            [("date", -1)]
        )
        
        # Daily insights: query by date
        await DailyInsight.get_motor_collection().create_index(
            [("date", -1)],
            unique=True
        )
        
        # ROI log: immutable, indexed by timestamp and hash
        await ROILogEntry.get_motor_collection().create_index(
            [("timestamp", -1)]
        )
        await ROILogEntry.get_motor_collection().create_index(
            [("entry_hash", 1)],
            unique=True
        )
        
        # Audit log: query by calculation type and timestamp
        await CalculationAuditLog.get_motor_collection().create_index(
            [("calculation_type", 1), ("timestamp", -1)]
        )
    
    @classmethod
    async def disconnect(cls) -> None:
        """
        Close MongoDB connection gracefully.
        """
        if cls._client:
            cls._client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """
        Get database instance for direct operations.
        """
        if cls._database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls._database
    
    @classmethod
    async def health_check(cls) -> dict:
        """
        Check database health status.
        """
        try:
            await cls._client.admin.command('ping')
            return {
                "status": "healthy",
                "database": get_settings().mongodb_database,
                "connected": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False
            }


# Convenience functions
async def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency injection for database access.
    """
    return DatabaseManager.get_database()