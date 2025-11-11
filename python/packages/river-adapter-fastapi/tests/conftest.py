"""Pytest configuration for FastAPI adapter tests."""

import pytest
import os


@pytest.fixture
def redis_url():
    """Get Redis URL from environment or use default."""
    return os.getenv("REDIS_URL", "redis://localhost:6380")
