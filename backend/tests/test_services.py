"""
Tests for PICAM Services
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.data_ingestion import DataIngestionService, IngestionResult
from app.services.video_processor import VideoProcessorService, PrivacyCompliance
from app.services.roi_tracker import ROITrackerService, ROIVerificationResult
from app.services.action_recommender import ActionRecommenderService, ActionCandidate
from app.services.insight_generator import InsightGeneratorService
from app.models.schemas import OperationalDataInput, LocationTypeEnum


class TestDataIngestionService:
    """Tests for data ingestion service."""
    
    @pytest.fixture
    def service(self):
        return DataIngestionService()
    
    def test_validate_observation_period(self, service):
        """Test observation period validation."""
        assert service._validate_observation_period(300) is True
        assert service._validate_observation_period(60) is True
        assert service._validate_observation_period(3600) is True
        assert service._validate_observation_period(30) is False  # Too short
        assert service._validate_observation_period(7200) is False  # Too long
    
    def test_calculate_confidence(self, service):
        """Test confidence calculation."""
        # Full data
        full_data = OperationalDataInput(
            timestamp=datetime.now(),
            location_id="test",
            location_type=LocationTypeEnum.FRONT_DESK,
            arrival_count=10,
            departure_count=10,
            queue_length=5,
            in_service_count=2,
            avg_service_duration_seconds=180,
            avg_wait_time_seconds=120
        )
        assert service._calculate_confidence(full_data) == 1.0
        
        # Missing optional fields
        partial_data = OperationalDataInput(
            timestamp=datetime.now(),
            location_id="test",
            location_type=LocationTypeEnum.FRONT_DESK,
            arrival_count=10,
            departure_count=10,
            queue_length=5,
            in_service_count=2
        )
        assert service._calculate_confidence(partial_data) == 0.8  # -0.1 for each missing


class TestVideoProcessorService:
    """Tests for video processor service."""
    
    @pytest.fixture
    def service(self):
        return VideoProcessorService()
    
    def test_privacy_compliance(self, service):
        """Test that privacy compliance is always true."""
        compliance = service.verify_privacy_compliance()
        
        assert compliance.is_compliant is True
        assert compliance.frames_stored is False
        assert compliance.personal_data_extracted is False
        assert compliance.raw_video_retained is False
        assert compliance.only_counts_saved is True
    
    def test_no_retention_enforcement(self):
        """Test that retention settings are enforced."""
        # This should work with default settings
        service = VideoProcessorService()
        assert service.settings.video_retention_seconds == 0


class TestActionRecommenderService:
    """Tests for action recommender service."""
    
    def test_action_candidate_properties(self):
        """Test ActionCandidate computed properties."""
        candidate = ActionCandidate(
            action_type="add_staff",
            description="Add 1 staff",
            target_loss_category="wait_time",
            estimated_recovery_min=100,
            estimated_recovery_max=150,
            estimated_cost=50,
            confidence=0.8,
            physics_basis="Test",
            supporting_data={}
        )
        
        assert candidate.net_benefit == 50
        assert candidate.roi_ratio == 2.0
    
    def test_zero_cost_action(self):
        """Test ROI calculation for zero-cost action."""
        candidate = ActionCandidate(
            action_type="schedule",
            description="Reschedule",
            target_loss_category="idle_time",
            estimated_recovery_min=100,
            estimated_recovery_max=150,
            estimated_cost=0,
            confidence=0.7,
            physics_basis="Test",
            supporting_data={}
        )
        
        assert candidate.net_benefit == 100
        assert candidate.roi_ratio == float('inf')


class TestROIVerification:
    """Tests for ROI verification logic."""
    
    def test_verification_result_properties(self):
        """Test ROIVerificationResult."""
        result = ROIVerificationResult(
            is_valid=True,
            before_loss=1000,
            after_loss=700,
            loss_reduction=300,
            improvement_percentage=30.0,
            confidence=0.85,
            physics_verified=True,
            notes="Test verification"
        )
        
        assert result.is_valid is True
        assert result.loss_reduction == 300
        assert result.improvement_percentage == 30.0


class TestPrivacyPrinciples:
    """Tests for privacy principles across services."""
    
    def test_video_processor_never_stores_frames(self):
        """Verify video processor never stores frames."""
        service = VideoProcessorService()
        
        # The class should have no attributes that store frames
        assert not hasattr(service, 'stored_frames')
        assert not hasattr(service, 'frame_buffer')
        assert not hasattr(service, 'frame_cache')
    
    def test_data_ingestion_no_personal_data(self):
        """Verify data ingestion doesn't accept personal data."""
        # The OperationalDataInput schema should not have personal data fields
        from app.models.schemas import OperationalDataInput
        
        fields = OperationalDataInput.model_fields.keys()
        personal_fields = ['name', 'email', 'phone', 'face', 'id_number', 'guest_id']
        
        for field in personal_fields:
            assert field not in fields, f"Personal data field '{field}' found in schema"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])