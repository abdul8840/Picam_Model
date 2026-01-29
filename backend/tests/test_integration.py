"""
PICAM Integration Tests

Tests the complete flow from data ingestion to insights generation.
"""

import pytest
from datetime import datetime, date, timedelta
from httpx import AsyncClient
import asyncio

from app.main import app
from app.database import DatabaseManager
from app.models.mongodb_models import OperationalDataPoint, DailyInsight


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="module", autouse=True)
async def setup_database():
    """Setup and teardown database for tests."""
    await DatabaseManager.connect()
    yield
    # Cleanup test data
    await OperationalDataPoint.find({"data_source": "test"}).delete()
    await DatabaseManager.disconnect()


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health endpoint returns 200."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint returns system info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["system"] == "PICAM"
        assert "principles" in data


class TestDataIngestion:
    """Test data ingestion endpoints."""
    
    @pytest.mark.asyncio
    async def test_ingest_single_data_point(self, client):
        """Test ingesting a single data point."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "location_id": "test_front_desk",
            "location_type": "front_desk",
            "arrival_count": 10,
            "departure_count": 9,
            "queue_length": 3,
            "in_service_count": 2,
            "avg_service_duration_seconds": 180,
            "avg_wait_time_seconds": 120,
            "observation_period_seconds": 300
        }
        
        response = await client.post("/api/v1/data/ingest", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_ingest_batch_data(self, client):
        """Test batch data ingestion."""
        base_time = datetime.utcnow()
        data_points = []
        
        for i in range(5):
            data_points.append({
                "timestamp": (base_time - timedelta(minutes=i*5)).isoformat(),
                "location_id": "test_front_desk",
                "location_type": "front_desk",
                "arrival_count": 8 + i,
                "departure_count": 7 + i,
                "queue_length": 2 + i,
                "in_service_count": 2,
                "observation_period_seconds": 300
            })
        
        response = await client.post(
            "/api/v1/data/ingest/batch",
            json={"data_points": data_points}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["processed"] == 5
    
    @pytest.mark.asyncio
    async def test_get_locations(self, client):
        """Test getting location list."""
        response = await client.get("/api/v1/data/locations")
        assert response.status_code == 200
        locations = response.json()
        assert isinstance(locations, list)


class TestMetricsEndpoints:
    """Test metrics calculation endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_summary(self, client):
        """Test getting metrics summary."""
        today = date.today().isoformat()
        response = await client.get(f"/api/v1/metrics/summary/{today}")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_hourly(self, client):
        """Test getting hourly metrics."""
        today = date.today().isoformat()
        response = await client.get(f"/api/v1/metrics/hourly/{today}")
        assert response.status_code == 200


class TestInsightsEndpoints:
    """Test insights endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_weekly_summary(self, client):
        """Test getting weekly summary."""
        response = await client.get("/api/v1/insights/weekly")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_trends(self, client):
        """Test getting trend analysis."""
        response = await client.get("/api/v1/insights/trends?days=7")
        assert response.status_code == 200


class TestROIEndpoints:
    """Test ROI tracking endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_roi_log(self, client):
        """Test getting ROI log."""
        response = await client.get("/api/v1/roi/log")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
    
    @pytest.mark.asyncio
    async def test_get_roi_summary(self, client):
        """Test getting ROI summary."""
        response = await client.get("/api/v1/roi/summary")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_verify_chain_integrity(self, client):
        """Test chain integrity verification."""
        response = await client.get("/api/v1/roi/chain-integrity")
        assert response.status_code == 200
        data = response.json()
        assert "chain_status" in data


class TestPrivacyCompliance:
    """Test privacy compliance."""
    
    @pytest.mark.asyncio
    async def test_privacy_endpoint(self, client):
        """Test privacy compliance endpoint."""
        response = await client.get("/api/v1/data/privacy-compliance")
        assert response.status_code == 200
        data = response.json()
        assert data["compliant"] == True
        assert data["details"]["frames_stored"] == False
        assert data["details"]["personal_data_extracted"] == False


class TestPhysicsCalculations:
    """Test physics calculations are deterministic."""
    
    @pytest.mark.asyncio
    async def test_deterministic_calculations(self, client):
        """Test that same input produces same output."""
        today = date.today().isoformat()
        
        response1 = await client.get(f"/api/v1/metrics/analysis/{today}")
        response2 = await client.get(f"/api/v1/metrics/analysis/{today}")
        
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            
            # If we have queue metrics, they should be identical
            if data1.get("queue_metrics") and data2.get("queue_metrics"):
                assert data1["queue_metrics"]["L"] == data2["queue_metrics"]["L"]
                assert data1["queue_metrics"]["lambda_rate"] == data2["queue_metrics"]["lambda_rate"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])