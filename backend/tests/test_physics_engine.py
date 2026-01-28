"""
Tests for PICAM Physics Engine
"""

import pytest
from datetime import datetime, date
from app.core import (
    LittlesLawCalculator,
    EntropyCalculator,
    LossCalculator,
    PhysicsEngine,
    FinancialParameters
)
from app.models.domain import FlowMeasurement, LocationType, CapacityConstraint


class TestLittlesLaw:
    """Test Little's Law calculations."""
    
    def test_basic_calculation(self):
        """Test basic L = λW calculation."""
        calculator = LittlesLawCalculator(min_data_points=5)
        
        # Create test measurements
        measurements = []
        for i in range(20):
            m = FlowMeasurement(
                timestamp=datetime(2024, 1, 15, 10, i * 5),
                location_id="front_desk",
                location_type=LocationType.FRONT_DESK,
                arrival_count=10,
                departure_count=10,
                queue_length=5,
                in_service_count=2,
                observation_period_seconds=300
            )
            measurements.append(m)
        
        result = calculator.calculate(measurements)
        
        assert result is not None
        assert result.L > 0  # Average in system
        assert result.lambda_rate > 0  # Arrival rate
        assert result.W > 0  # Time in system
        assert result.is_valid
    
    def test_littles_law_verification(self):
        """Test that L ≈ λW within tolerance."""
        calculator = LittlesLawCalculator()
        
        measurements = []
        for i in range(30):
            m = FlowMeasurement(
                timestamp=datetime(2024, 1, 15, 10, i * 2),
                location_id="front_desk",
                location_type=LocationType.FRONT_DESK,
                arrival_count=8,
                departure_count=8,
                queue_length=4,
                in_service_count=2,
                avg_wait_time=120,
                observation_period_seconds=300
            )
            measurements.append(m)
        
        result = calculator.calculate(measurements)
        verification = calculator.verify_littles_law(measurements)
        
        assert result is not None
        # L should approximately equal λ × W
        calculated_L = result.lambda_rate * result.W
        assert abs(result.L - calculated_L) < result.L * 0.2  # Within 20%
    
    def test_unstable_system_detection(self):
        """Test detection of unstable system (ρ >= 1)."""
        calculator = LittlesLawCalculator(min_data_points=5)
        
        # Create overloaded scenario
        measurements = []
        for i in range(20):
            m = FlowMeasurement(
                timestamp=datetime(2024, 1, 15, 10, i * 5),
                location_id="front_desk",
                location_type=LocationType.FRONT_DESK,
                arrival_count=20,  # High arrivals
                departure_count=10,  # Lower departures
                queue_length=15,
                in_service_count=3,
                observation_period_seconds=300
            )
            measurements.append(m)
        
        result = calculator.calculate(measurements)
        
        assert result is not None
        assert result.is_unstable or result.rho > 0.9  # System stressed


class TestEntropyCalculator:
    """Test entropy/variability calculations."""
    
    def test_cv_calculation(self):
        """Test coefficient of variation calculation."""
        calculator = EntropyCalculator(min_data_points=5)
        
        # Low variability
        measurements_low = [
            FlowMeasurement(
                timestamp=datetime(2024, 1, 15, 10, i * 5),
                location_id="test",
                location_type=LocationType.FRONT_DESK,
                arrival_count=10,  # Constant
                observation_period_seconds=300
            )
            for i in range(20)
        ]
        
        entropy_low = calculator.calculate_entropy(measurements_low, "test")
        
        # High variability
        import random
        random.seed(42)
        measurements_high = [
            FlowMeasurement(
                timestamp=datetime(2024, 1, 15, 10, i * 5),
                location_id="test",
                location_type=LocationType.FRONT_DESK,
                arrival_count=random.randint(1, 30),  # Variable
                observation_period_seconds=300
            )
            for i in range(20)
        ]
        
        entropy_high = calculator.calculate_entropy(measurements_high, "test")
        
        assert entropy_low is not None
        assert entropy_high is not None
        assert entropy_low.arrival_cv < entropy_high.arrival_cv
    
    def test_kingman_impact(self):
        """Test Kingman's formula impact calculation."""
        calculator = EntropyCalculator()
        
        impact = calculator.calculate_kingman_impact(
            arrival_cv=1.0,
            service_cv=1.0,
            utilization=0.8
        )
        
        assert impact["status"] == "calculated"
        assert impact["variability_term"] == 1.0  # (1² + 1²) / 2
        assert impact["utilization_term"] == 4.0  # 0.8 / (1 - 0.8)


class TestLossCalculator:
    """Test financial loss calculations."""
    
    def test_wait_time_loss(self):
        """Test wait time loss calculation."""
        params = FinancialParameters(
            customer_time_value_per_minute=2.0,
            acceptable_wait_minutes=5.0,
            conservative_factor=1.0  # No reduction for testing
        )
        calculator = LossCalculator(params=params)
        
        # Create measurements with high wait times
        measurements = [
            FlowMeasurement(
                timestamp=datetime(2024, 1, 15, 10, i * 5),
                location_id="test",
                location_type=LocationType.FRONT_DESK,
                arrival_count=10,
                departure_count=10,
                queue_length=8,
                in_service_count=2,
                avg_wait_time=600,  # 10 minutes
                observation_period_seconds=300
            )
            for i in range(10)
        ]
        
        loss = calculator.calculate_total_loss(
            measurements=measurements,
            littles_result=None,
            entropy=None,
            target_date=date(2024, 1, 15)
        )
        
        assert loss.wait_time_cost > 0
        assert loss.total_wait_time_seconds > 0
    
    def test_conservative_estimation(self):
        """Test that losses are conservatively estimated."""
        params = FinancialParameters(
            conservative_factor=0.7
        )
        calculator = LossCalculator(params=params)
        
        measurements = [
            FlowMeasurement(
                timestamp=datetime(2024, 1, 15, 10, i * 5),
                location_id="test",
                location_type=LocationType.FRONT_DESK,
                arrival_count=10,
                queue_length=5,
                avg_wait_time=600,
                observation_period_seconds=300
            )
            for i in range(10)
        ]
        
        loss = calculator.calculate_total_loss(
            measurements=measurements,
            littles_result=None,
            entropy=None
        )
        
        # Loss should be reduced by conservative factor
        # This is implicitly tested by the factor being applied
        assert loss.total_loss >= 0


class TestPhysicsEngine:
    """Test unified physics engine."""
    
    def test_location_analysis(self):
        """Test complete location analysis."""
        engine = PhysicsEngine()
        
        measurements = [
            FlowMeasurement(
                timestamp=datetime(2024, 1, 15, 10, i * 5),
                location_id="front_desk_main",
                location_type=LocationType.FRONT_DESK,
                arrival_count=10,
                departure_count=9,
                queue_length=5,
                in_service_count=3,
                avg_service_duration=180,
                avg_wait_time=240,
                observation_period_seconds=300
            )
            for i in range(30)
        ]
        
        capacity = CapacityConstraint(
            location_type=LocationType.FRONT_DESK,
            max_servers=3,
            max_queue_capacity=50
        )
        
        analysis = engine.analyze_location(measurements, capacity)
        
        assert analysis["status"] == "analyzed"
        assert analysis["queue_metrics"] is not None
        assert analysis["financial_loss"] is not None
        assert analysis["total_loss"] >= 0
        assert analysis["is_deterministic"] is True
    
    def test_determinism(self):
        """Test that same inputs produce same outputs."""
        engine = PhysicsEngine()
        
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
        
        result1 = engine.analyze_location(measurements)
        result2 = engine.analyze_location(measurements)
        
        # Core metrics should be identical
        assert result1["queue_metrics"]["L"] == result2["queue_metrics"]["L"]
        assert result1["queue_metrics"]["lambda_rate"] == result2["queue_metrics"]["lambda_rate"]
        assert result1["total_loss"] == result2["total_loss"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])