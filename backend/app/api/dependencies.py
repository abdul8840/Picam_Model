"""
PICAM API Dependencies
Dependency injection for routes
"""

from fastapi import Depends, HTTPException, Header
from typing import Optional

from app.config import get_settings, Settings
from app.database import get_database


async def get_api_settings() -> Settings:
    """
    Dependency to get application settings.
    """
    return get_settings()


async def verify_api_access(
    x_api_key: Optional[str] = Header(None)
) -> bool:
    """
    Optional API key verification.
    For production, implement proper authentication.
    """
    # Currently open - implement as needed
    return True


async def get_db_session():
    """
    Dependency to get database session.
    """
    return await get_database()