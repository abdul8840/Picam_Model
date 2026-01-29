"""
PICAM Data Seeder

Seeds the database with sample operational data for testing and demonstration.
"""

import asyncio
import os
import sys
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import DatabaseManager
from app.services.sample_data_generator import generate_sample_data
from app.services.insight_generator import get_insight_generator
from app.config import get_settings


async def seed_database():
    """
    Main seeding function.
    """
    settings = get_settings()
    seed_days = int(os.environ.get('SEED_DAYS', 7))
    
    print("=" * 60)
    print("PICAM Data Seeder")
    print("=" * 60)
    print(f"Hotel: {settings.hotel_name}")
    print(f"Days to seed: {seed_days}")
    print()
    
    # Connect to database
    print("Connecting to MongoDB...")
    await DatabaseManager.connect()
    print("Connected!")
    print()
    
    try:
        # Generate sample data
        print(f"Generating {seed_days} days of sample data...")
        end_date = date.today()
        start_date = end_date - timedelta(days=seed_days - 1)
        
        result = await generate_sample_data(start_date, end_date, seed=42)
        
        print(f"✓ Generated {result['total_records']} operational data points")
        print(f"  Date range: {result['start_date']} to {result['end_date']}")
        print()
        
        # Generate insights for each day
        print("Generating daily insights...")
        insight_generator = get_insight_generator()
        
        current = start_date
        insights_generated = 0
        
        while current <= end_date:
            try:
                await insight_generator.generate_daily_insight(current)
                insights_generated += 1
                print(f"  ✓ Generated insight for {current}")
            except Exception as e:
                print(f"  ✗ Failed for {current}: {e}")
            
            current += timedelta(days=1)
        
        print(f"\n✓ Generated {insights_generated} daily insights")
        print()
        
        # Print summary
        print("=" * 60)
        print("SEEDING COMPLETE")
        print("=" * 60)
        print()
        print("You can now access:")
        print("  - Dashboard: http://localhost:3000")
        print("  - API Docs:  http://localhost:8000/api/docs")
        print()
        
    finally:
        await DatabaseManager.disconnect()
        print("Database connection closed.")


def main():
    """Entry point."""
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()