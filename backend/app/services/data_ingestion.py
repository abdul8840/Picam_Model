"""
PICAM Data Ingestion Service

Handles all operational data input:
- Manual data entry
- Batch imports
- Sensor data
- Video-derived counts (from VideoProcessorService)

Privacy Principle: Only accepts aggregate counts and durations.
No personal data, no individual tracking.
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import asyncio

from app.models.mongodb_models import (
    OperationalDataPoint,
    CalculationAuditLog,
    SystemConfiguration
)
from app.models.domain import FlowMeasurement, LocationType
from app.models.schemas import OperationalDataInput, BatchOperationalDataInput
from app.utils import now_utc, to_utc, create_deterministic_hash, get_date_range
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of data ingestion operation."""
    success: bool
    records_processed: int
    records_failed: int
    errors: List[str]
    data_point_ids: List[str]


@dataclass
class DataQualityReport:
    """Report on data quality for a period."""
    start_date: date
    end_date: date
    total_records: int
    completeness_score: float  # 0-1
    consistency_score: float  # 0-1
    issues: List[str]


class DataIngestionService:
    """
    Service for ingesting operational data into PICAM.
    
    Responsibilities:
    - Validate incoming data
    - Calculate derived metrics (rates)
    - Store in MongoDB
    - Maintain audit trail
    - Ensure data quality
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.min_observation_period = 60  # Minimum 1 minute
        self.max_observation_period = 3600  # Maximum 1 hour
    
    async def ingest_single(
        self,
        data: OperationalDataInput,
        source: str = "api"
    ) -> IngestionResult:
        """
        Ingest a single operational data point.
        
        Args:
            data: Validated input data
            source: Data source identifier
            
        Returns:
            IngestionResult with status and IDs
        """
        try:
            # Validate observation period
            if not self._validate_observation_period(data.observation_period_seconds):
                return IngestionResult(
                    success=False,
                    records_processed=0,
                    records_failed=1,
                    errors=["Invalid observation period"],
                    data_point_ids=[]
                )
            
            # Calculate rates
            arrival_rate = data.arrival_count / data.observation_period_seconds
            departure_rate = data.departure_count / data.observation_period_seconds
            
            # Create document
            doc = OperationalDataPoint(
                timestamp=to_utc(data.timestamp),
                date=to_utc(data.timestamp).date(),
                location_id=data.location_id,
                location_type=data.location_type.value,
                arrival_count=data.arrival_count,
                departure_count=data.departure_count,
                queue_length=data.queue_length,
                in_service_count=data.in_service_count,
                avg_service_duration=data.avg_service_duration_seconds,
                avg_wait_time=data.avg_wait_time_seconds,
                observation_period_seconds=data.observation_period_seconds,
                arrival_rate=arrival_rate,
                departure_rate=departure_rate,
                data_source=source,
                confidence_score=self._calculate_confidence(data),
                created_at=now_utc()
            )
            
            await doc.insert()
            
            # Create audit log
            await self._create_audit_log(
                operation="ingest_single",
                data_point_id=str(doc.id),
                location_id=data.location_id,
                source=source
            )
            
            logger.info(f"Ingested data point {doc.id} for {data.location_id}")
            
            return IngestionResult(
                success=True,
                records_processed=1,
                records_failed=0,
                errors=[],
                data_point_ids=[str(doc.id)]
            )
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return IngestionResult(
                success=False,
                records_processed=0,
                records_failed=1,
                errors=[str(e)],
                data_point_ids=[]
            )
    
    async def ingest_batch(
        self,
        data: BatchOperationalDataInput,
        source: str = "api_batch"
    ) -> IngestionResult:
        """
        Ingest multiple operational data points in batch.
        
        Args:
            data: Batch of validated input data
            source: Data source identifier
            
        Returns:
            IngestionResult with status and IDs
        """
        docs = []
        errors = []
        
        for i, dp in enumerate(data.data_points):
            try:
                if not self._validate_observation_period(dp.observation_period_seconds):
                    errors.append(f"Record {i}: Invalid observation period")
                    continue
                
                arrival_rate = dp.arrival_count / dp.observation_period_seconds
                departure_rate = dp.departure_count / dp.observation_period_seconds
                
                doc = OperationalDataPoint(
                    timestamp=to_utc(dp.timestamp),
                    date=to_utc(dp.timestamp).date(),
                    location_id=dp.location_id,
                    location_type=dp.location_type.value,
                    arrival_count=dp.arrival_count,
                    departure_count=dp.departure_count,
                    queue_length=dp.queue_length,
                    in_service_count=dp.in_service_count,
                    avg_service_duration=dp.avg_service_duration_seconds,
                    avg_wait_time=dp.avg_wait_time_seconds,
                    observation_period_seconds=dp.observation_period_seconds,
                    arrival_rate=arrival_rate,
                    departure_rate=departure_rate,
                    data_source=source,
                    confidence_score=self._calculate_confidence(dp),
                    created_at=now_utc()
                )
                docs.append(doc)
                
            except Exception as e:
                errors.append(f"Record {i}: {str(e)}")
        
        if docs:
            try:
                await OperationalDataPoint.insert_many(docs)
                
                # Create audit log for batch
                await self._create_audit_log(
                    operation="ingest_batch",
                    data_point_id=f"batch_{len(docs)}",
                    location_id="multiple",
                    source=source
                )
                
                logger.info(f"Batch ingested {len(docs)} records")
                
            except Exception as e:
                errors.append(f"Batch insert failed: {str(e)}")
                return IngestionResult(
                    success=False,
                    records_processed=0,
                    records_failed=len(data.data_points),
                    errors=errors,
                    data_point_ids=[]
                )
        
        return IngestionResult(
            success=len(errors) == 0,
            records_processed=len(docs),
            records_failed=len(errors),
            errors=errors,
            data_point_ids=[str(doc.id) for doc in docs]
        )
    
    async def ingest_from_video_count(
        self,
        location_id: str,
        location_type: str,
        timestamp: datetime,
        person_count: int,
        observation_period_seconds: float,
        processing_id: str
    ) -> IngestionResult:
        """
        Ingest data derived from video processing.
        
        Called by VideoProcessorService after in-memory processing.
        Video frames are never stored.
        """
        # Create a minimal data point from video count
        # We can only determine queue length/density from video
        
        try:
            doc = OperationalDataPoint(
                timestamp=to_utc(timestamp),
                date=to_utc(timestamp).date(),
                location_id=location_id,
                location_type=location_type,
                arrival_count=0,  # Unknown from single frame
                departure_count=0,  # Unknown from single frame
                queue_length=person_count,  # This is what we detected
                in_service_count=0,  # Unknown without tracking
                observation_period_seconds=observation_period_seconds,
                data_source=f"video:{processing_id}",
                confidence_score=0.8,  # Video-derived has slightly lower confidence
                created_at=now_utc()
            )
            
            await doc.insert()
            
            return IngestionResult(
                success=True,
                records_processed=1,
                records_failed=0,
                errors=[],
                data_point_ids=[str(doc.id)]
            )
            
        except Exception as e:
            logger.error(f"Video ingestion failed: {e}")
            return IngestionResult(
                success=False,
                records_processed=0,
                records_failed=1,
                errors=[str(e)],
                data_point_ids=[]
            )
    
    async def get_data_for_analysis(
        self,
        target_date: date,
        location_id: Optional[str] = None
    ) -> List[FlowMeasurement]:
        """
        Retrieve data for physics analysis.
        
        Args:
            target_date: Date to retrieve
            location_id: Optional location filter
            
        Returns:
            List of FlowMeasurement domain objects
        """
        query = {"date": target_date}
        if location_id:
            query["location_id"] = location_id
        
        data_points = await OperationalDataPoint.find(query).sort("timestamp").to_list()
        
        measurements = []
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
            measurements.append(m)
        
        return measurements
    
    async def get_data_grouped_by_location(
        self,
        target_date: date
    ) -> Dict[str, List[FlowMeasurement]]:
        """
        Retrieve data grouped by location for daily analysis.
        """
        data_points = await OperationalDataPoint.find(
            {"date": target_date}
        ).sort("timestamp").to_list()
        
        grouped: Dict[str, List[FlowMeasurement]] = {}
        
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
            
            if dp.location_id not in grouped:
                grouped[dp.location_id] = []
            grouped[dp.location_id].append(m)
        
        return grouped
    
    async def check_data_quality(
        self,
        start_date: date,
        end_date: date,
        location_id: Optional[str] = None
    ) -> DataQualityReport:
        """
        Generate data quality report for a period.
        """
        query = {
            "date": {"$gte": start_date, "$lte": end_date}
        }
        if location_id:
            query["location_id"] = location_id
        
        data_points = await OperationalDataPoint.find(query).to_list()
        
        if not data_points:
            return DataQualityReport(
                start_date=start_date,
                end_date=end_date,
                total_records=0,
                completeness_score=0,
                consistency_score=0,
                issues=["No data found for period"]
            )
        
        issues = []
        
        # Check completeness
        days = (end_date - start_date).days + 1
        expected_records_per_day = 288  # 5-min intervals
        expected_total = days * expected_records_per_day
        completeness = min(1.0, len(data_points) / expected_total)
        
        if completeness < 0.5:
            issues.append(f"Low data completeness: {completeness:.1%}")
        
        # Check consistency
        consistency_issues = 0
        for dp in data_points:
            # Check for logical issues
            if dp.departure_count > dp.arrival_count * 2:
                consistency_issues += 1
            if dp.queue_length < 0 or dp.in_service_count < 0:
                consistency_issues += 1
        
        consistency = 1.0 - (consistency_issues / len(data_points))
        
        if consistency < 0.9:
            issues.append(f"Data consistency issues found: {consistency_issues} records")
        
        return DataQualityReport(
            start_date=start_date,
            end_date=end_date,
            total_records=len(data_points),
            completeness_score=round(completeness, 4),
            consistency_score=round(consistency, 4),
            issues=issues
        )
    
    async def get_locations(self) -> List[str]:
        """Get all unique location IDs."""
        return await OperationalDataPoint.distinct("location_id")
    
    async def get_date_range_with_data(self) -> Tuple[Optional[date], Optional[date]]:
        """Get the date range that has data."""
        first = await OperationalDataPoint.find_one(
            sort=[("date", 1)]
        )
        last = await OperationalDataPoint.find_one(
            sort=[("date", -1)]
        )
        
        if first and last:
            return (first.date, last.date)
        return (None, None)
    
    def _validate_observation_period(self, seconds: float) -> bool:
        """Validate observation period is within acceptable range."""
        return self.min_observation_period <= seconds <= self.max_observation_period
    
    def _calculate_confidence(self, data: OperationalDataInput) -> float:
        """
        Calculate confidence score for a data point.
        
        Based on:
        - Completeness of fields
        - Logical consistency
        """
        score = 1.0
        
        # Reduce if missing optional fields
        if data.avg_service_duration_seconds is None:
            score -= 0.1
        if data.avg_wait_time_seconds is None:
            score -= 0.1
        
        # Reduce if logical issues
        if data.departure_count > data.arrival_count * 2:
            score -= 0.2
        
        return max(0.0, score)
    
    async def _create_audit_log(
        self,
        operation: str,
        data_point_id: str,
        location_id: str,
        source: str
    ) -> None:
        """Create audit log entry for data operation."""
        try:
            log_entry = CalculationAuditLog(
                calculation_id=f"ingest_{data_point_id}",
                calculation_type="data_ingestion",
                timestamp=now_utc(),
                input_data={
                    "operation": operation,
                    "data_point_id": data_point_id,
                    "location_id": location_id,
                    "source": source
                },
                input_hash=create_deterministic_hash({
                    "operation": operation,
                    "data_point_id": data_point_id
                }),
                configuration_snapshot={},
                output_data={"status": "ingested"},
                output_hash="",
                formula_used="N/A - Data ingestion",
                assumptions=["Data provided is accurate", "Timestamps are correct"],
                is_deterministic=True,
                is_reproducible=True
            )
            await log_entry.insert()
        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")


# Service instance factory
_ingestion_service: Optional[DataIngestionService] = None


def get_ingestion_service() -> DataIngestionService:
    """Get or create ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = DataIngestionService()
    return _ingestion_service