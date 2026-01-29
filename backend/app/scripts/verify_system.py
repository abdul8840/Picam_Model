"""
PICAM System Verification Script

Verifies that all system components are working correctly.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import date, timedelta
from app.database import DatabaseManager
from app.models.mongodb_models import OperationalDataPoint, DailyInsight, ROILogEntry
from app.core import (
    LittlesLawCalculator,
    EntropyCalculator,
    LossCalculator,
    get_physics_engine
)
from app.services import (
    get_ingestion_service,
    get_video_processor,
    get_roi_tracker
)
from app.config import get_settings


class SystemVerifier:
    """Verifies all PICAM system components."""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def check(self, name: str, condition: bool, details: str = ""):
        """Record a check result."""
        status = "✓ PASS" if condition else "✗ FAIL"
        self.results.append({
            "name": name,
            "passed": condition,
            "details": details
        })
        if condition:
            self.passed += 1
        else:
            self.failed += 1
        print(f"  {status}: {name}" + (f" ({details})" if details else ""))
    
    async def verify_database(self):
        """Verify database connection and collections."""
        print("\n[Database Verification]")
        
        try:
            health = await DatabaseManager.health_check()
            self.check("MongoDB Connection", health["connected"])
            
            # Check collections exist
            db = DatabaseManager.get_database()
            collections = await db.list_collection_names()
            
            required = ['operational_data', 'daily_insights', 'roi_log', 
                       'action_recommendations', 'calculation_audit_log']
            
            for coll in required:
                exists = coll in collections
                self.check(f"Collection '{coll}'", exists)
                
        except Exception as e:
            self.check("Database Connection", False, str(e))
    
    async def verify_data(self):
        """Verify data exists and is valid."""
        print("\n[Data Verification]")
        
        try:
            # Check operational data
            count = await OperationalDataPoint.count()
            self.check("Operational Data Exists", count > 0, f"{count} records")
            
            # Check data structure
            sample = await OperationalDataPoint.find_one()
            if sample:
                has_required = all([
                    hasattr(sample, 'timestamp'),
                    hasattr(sample, 'location_id'),
                    hasattr(sample, 'arrival_count')
                ])
                self.check("Data Structure Valid", has_required)
            
            # Check insights
            insight_count = await DailyInsight.count()
            self.check("Daily Insights Exist", insight_count > 0, f"{insight_count} insights")
            
        except Exception as e:
            self.check("Data Verification", False, str(e))
    
    async def verify_physics_engine(self):
        """Verify physics calculations work correctly."""
        print("\n[Physics Engine Verification]")
        
        try:
            # Test Little's Law Calculator
            calc = LittlesLawCalculator()
            self.check("Little's Law Calculator Initialized", calc is not None)
            
            # Test Entropy Calculator
            entropy_calc = EntropyCalculator()
            self.check("Entropy Calculator Initialized", entropy_calc is not None)
            
            # Test Loss Calculator
            loss_calc = LossCalculator()
            self.check("Loss Calculator Initialized", loss_calc is not None)
            
            # Test Physics Engine
            engine = get_physics_engine()
            self.check("Physics Engine Initialized", engine is not None)
            
            # Test determinism
            from app.models.domain import FlowMeasurement, LocationType
            from datetime import datetime
            
            measurements = [
                FlowMeasurement(
                    timestamp=datetime(2024, 1, 15, 10, i * 5),
                    location_id="test",
                    location_type=LocationType.FRONT_DESK,
                    arrival_count=10,
                    departure_count=10,
                    queue_length=5,
                    in_service_count=2,
                    observation_period_seconds=300
                )
                for i in range(20)
            ]
            
            result1 = calc.calculate(measurements)
            result2 = calc.calculate(measurements)
            
            is_deterministic = (
                result1 is not None and 
                result2 is not None and
                result1.L == result2.L and
                result1.W == result2.W
            )
            self.check("Calculations Are Deterministic", is_deterministic)
            
        except Exception as e:
            self.check("Physics Engine", False, str(e))
    
    async def verify_services(self):
        """Verify services are operational."""
        print("\n[Services Verification]")
        
        try:
            # Data Ingestion Service
            ingestion = get_ingestion_service()
            self.check("Data Ingestion Service", ingestion is not None)
            
            # Video Processor
            video = get_video_processor()
            privacy = video.verify_privacy_compliance()
            self.check("Video Processor Privacy Compliant", privacy.is_compliant)
            
            # ROI Tracker
            roi = get_roi_tracker()
            chain_valid = await roi.verify_chain_integrity()
            self.check("ROI Chain Integrity", chain_valid)
            
        except Exception as e:
            self.check("Services", False, str(e))
    
    async def verify_configuration(self):
        """Verify system configuration."""
        print("\n[Configuration Verification]")
        
        try:
            settings = get_settings()
            
            self.check("Settings Loaded", settings is not None)
            self.check("Confidence Level Valid", 
                      0.5 <= settings.confidence_level <= 0.99,
                      f"{settings.confidence_level}")
            self.check("Video Retention = 0 (Privacy)", 
                      settings.video_retention_seconds == 0)
            self.check("Front Desk Stations > 0",
                      settings.front_desk_stations > 0,
                      f"{settings.front_desk_stations}")
            
        except Exception as e:
            self.check("Configuration", False, str(e))
    
    def print_summary(self):
        """Print verification summary."""
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"  Total Checks: {self.passed + self.failed}")
        print(f"  Passed: {self.passed}")
        print(f"  Failed: {self.failed}")
        print()
        
        if self.failed == 0:
            print("✓ ALL CHECKS PASSED - System is ready!")
        else:
            print("✗ SOME CHECKS FAILED - Review issues above")
            print("\nFailed checks:")
            for r in self.results:
                if not r["passed"]:
                    print(f"  - {r['name']}: {r['details']}")
        
        print()
        return self.failed == 0


async def main():
    """Run system verification."""
    print("=" * 60)
    print("PICAM System Verification")
    print("=" * 60)
    
    # Connect to database
    print("\nConnecting to MongoDB...")
    await DatabaseManager.connect()
    
    verifier = SystemVerifier()
    
    try:
        await verifier.verify_database()
        await verifier.verify_data()
        await verifier.verify_physics_engine()
        await verifier.verify_services()
        await verifier.verify_configuration()
        
        success = verifier.print_summary()
        return 0 if success else 1
        
    finally:
        await DatabaseManager.disconnect()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)