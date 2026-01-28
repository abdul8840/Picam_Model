"""
PICAM Sample Data Generator

Generates realistic sample operational data for testing and demonstration.
"""

import random
from datetime import datetime, date, timedelta
from typing import List, Optional
import asyncio

from app.models.schemas import OperationalDataInput, BatchOperationalDataInput, LocationTypeEnum
from app.services.data_ingestion import get_ingestion_service


class SampleDataGenerator:
    """
    Generates realistic hotel operational data.
    
    Patterns modeled:
    - Check-in peaks (2-6 PM)
    - Check-out peaks (10 AM - 12 PM)
    - Restaurant peaks (breakfast, lunch, dinner)
    - Weekend vs weekday variations
    """
    
    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)
    
    def generate_day_data(
        self,
        target_date: date,
        locations: List[str] = None
    ) -> List[OperationalDataInput]:
        """
        Generate a full day of operational data.
        """
        if locations is None:
            locations = [
                ("front_desk_main", LocationTypeEnum.FRONT_DESK),
                ("restaurant_main", LocationTypeEnum.RESTAURANT),
                ("lobby_entrance", LocationTypeEnum.LOBBY)
            ]
        
        data_points = []
        
        # Generate data for each 5-minute interval
        for hour in range(24):
            for minute in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
                timestamp = datetime.combine(
                    target_date,
                    datetime.min.time()
                ).replace(hour=hour, minute=minute)
                
                for loc_id, loc_type in locations:
                    dp = self._generate_data_point(
                        timestamp, loc_id, loc_type, target_date.weekday()
                    )
                    data_points.append(dp)
        
        return data_points
    
    def _generate_data_point(
        self,
        timestamp: datetime,
        location_id: str,
        location_type: LocationTypeEnum,
        weekday: int
    ) -> OperationalDataInput:
        """
        Generate a single data point based on patterns.
        """
        hour = timestamp.hour
        is_weekend = weekday >= 5
        
        # Get base rates based on location and time
        if location_type == LocationTypeEnum.FRONT_DESK:
            arrivals = self._front_desk_arrivals(hour, is_weekend)
            service_time = random.gauss(180, 30)  # ~3 min avg
        elif location_type == LocationTypeEnum.RESTAURANT:
            arrivals = self._restaurant_arrivals(hour, is_weekend)
            service_time = random.gauss(1800, 300)  # ~30 min avg
        else:
            arrivals = self._lobby_traffic(hour, is_weekend)
            service_time = random.gauss(60, 20)  # ~1 min avg
        
        # Add some randomness
        arrivals = max(0, int(arrivals * random.uniform(0.7, 1.3)))
        
        # Calculate derived metrics
        # Departures slightly lag arrivals
        departures = max(0, int(arrivals * random.uniform(0.8, 1.0)))
        
        # Queue builds when arrivals > departures
        queue_length = max(0, int(random.gauss(arrivals * 0.3, 2)))
        
        # In-service based on capacity
        in_service = min(3, max(0, int(random.gauss(2, 0.5))))
        
        # Wait time increases with queue
        if queue_length > 0:
            wait_time = queue_length * service_time / 3 + random.gauss(30, 10)
        else:
            wait_time = random.gauss(30, 10)
        
        return OperationalDataInput(
            timestamp=timestamp,
            location_id=location_id,
            location_type=location_type,
            arrival_count=arrivals,
            departure_count=departures,
            queue_length=queue_length,
            in_service_count=in_service,
            avg_service_duration_seconds=max(30, service_time),
            avg_wait_time_seconds=max(0, wait_time),
            observation_period_seconds=300
        )
    
    def _front_desk_arrivals(self, hour: int, is_weekend: bool) -> float:
        """Front desk arrival pattern."""
        # Check-in peak 2-6 PM, check-out 10 AM - 12 PM
        if 14 <= hour <= 18:  # Check-in peak
            base = 12 if is_weekend else 10
        elif 10 <= hour <= 12:  # Check-out
            base = 8
        elif 8 <= hour <= 22:  # Normal hours
            base = 3
        else:  # Night
            base = 1
        
        return base * (1.2 if is_weekend else 1.0)
    
    def _restaurant_arrivals(self, hour: int, is_weekend: bool) -> float:
        """Restaurant arrival pattern."""
        if 7 <= hour <= 9:  # Breakfast
            base = 15
        elif 12 <= hour <= 14:  # Lunch
            base = 20
        elif 18 <= hour <= 21:  # Dinner
            base = 25
        else:
            base = 2
        
        return base * (1.3 if is_weekend else 1.0)
    
    def _lobby_traffic(self, hour: int, is_weekend: bool) -> float:
        """Lobby traffic pattern."""
        if 8 <= hour <= 22:
            base = 8
        else:
            base = 2
        return base


async def generate_sample_data(
    start_date: date,
    end_date: date,
    seed: Optional[int] = 42
) -> dict:
    """
    Generate and ingest sample data for a date range.
    """
    generator = SampleDataGenerator(seed=seed)
    service = get_ingestion_service()
    
    current = start_date
    total_records = 0
    
    while current <= end_date:
        data_points = generator.generate_day_data(current)
        
        batch = BatchOperationalDataInput(data_points=data_points)
        result = await service.ingest_batch(batch, source="sample_generator")
        
        total_records += result.records_processed
        current += timedelta(days=1)
    
    return {
        "status": "complete",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_records": total_records
    }