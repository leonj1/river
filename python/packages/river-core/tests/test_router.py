"""Tests for River router."""

import pytest
from pydantic import BaseModel
from river_core import create_river_stream, create_river_router, default_river_provider


class TestInput(BaseModel):
    """Test input model."""

    value: int


@pytest.mark.asyncio
async def test_create_router():
    """Test router creation."""

    async def runner1(ctx):
        await ctx.stream.append_chunk(ctx.input.value * 2)
        await ctx.stream.close()

    async def runner2(ctx):
        await ctx.stream.append_chunk(ctx.input.value * 3)
        await ctx.stream.close()

    stream1 = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(default_river_provider())
        .runner(runner1)
    )

    stream2 = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(default_river_provider())
        .runner(runner2)
    )

    router = create_river_router({"double": stream1, "triple": stream2})

    assert "double" in router
    assert "triple" in router
    assert len(router) == 2


@pytest.mark.asyncio
async def test_router_stream_access():
    """Test accessing streams from router."""

    async def test_runner(ctx):
        await ctx.stream.close()

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(default_river_provider())
        .runner(test_runner)
    )

    router = create_river_router({"test": stream})

    assert router["test"] == stream
    assert router.get("test") == stream
    assert router.get("nonexistent") is None
