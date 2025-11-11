"""Pytest configuration for redis provider tests."""

import pytest
import os
from redis import asyncio as aioredis


@pytest.fixture
def redis_url():
    """Get Redis URL from environment or use default."""
    return os.getenv("REDIS_URL", "redis://localhost:6380")


@pytest.fixture
async def redis_client(redis_url):
    """Create a Redis client for testing."""
    client = await aioredis.from_url(redis_url)
    yield client
    await client.close()


@pytest.fixture
async def clean_redis(redis_client):
    """Clean Redis before and after tests."""
    # Clean before test
    await redis_client.flushdb()
    yield
    # Clean after test
    await redis_client.flushdb()
