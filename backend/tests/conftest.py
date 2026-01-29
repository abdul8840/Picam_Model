"""
Pytest Configuration and Fixtures
"""

import pytest
import asyncio
from datetime import datetime, date
from typing import Generator

from app.config import get_settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def settings():
    """Get test settings."""
    return get_settings()


@pytest.fixture
def sample_timestamp():
    """Sample timestamp for tests."""
    return datetime(2024, 1, 15, 10, 30, 0)


@pytest.fixture
def sample_date():
    """Sample date for tests."""
    return date(2024, 1, 15)