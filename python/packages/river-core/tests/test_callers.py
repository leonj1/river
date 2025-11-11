"""Tests for server-side callers."""

import pytest
from pydantic import BaseModel, ValidationError
from river_core import (
    create_river_stream,
    create_river_router,
    create_server_side_caller,
    default_river_provider,
)
from river_core.errors import RiverError


class TestInput(BaseModel):
    """Test input model."""

    value: int


@pytest.mark.asyncio
async def test_server_caller_start():
    """Test starting a stream via server caller."""

    async def test_runner(ctx):
        await ctx.stream.append_chunk(ctx.input.value * 2)
        await ctx.stream.close()

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(default_river_provider())
        .runner(test_runner)
    )

    router = create_river_router({"test": stream})
    caller = create_server_side_caller(router)

    chunks = []
    async for item in caller.test.start(
        input_data={"value": 5},
        adapter_request=None,
    ):
        if item["type"] == "chunk":
            chunks.append(item["chunk"])

    assert chunks == [10]


@pytest.mark.asyncio
async def test_server_caller_validation_error():
    """Test that validation errors are caught."""

    async def test_runner(ctx):
        await ctx.stream.close()

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(default_river_provider())
        .runner(test_runner)
    )

    router = create_river_router({"test": stream})
    caller = create_server_side_caller(router)

    with pytest.raises(RiverError) as exc_info:
        async for _ in caller.test.start(
            input_data={"value": "not_an_int"},  # Invalid type
            adapter_request=None,
        ):
            pass

    assert "validation" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_server_caller_stream_not_found():
    """Test error when stream not found."""

    router = create_river_router({})
    caller = create_server_side_caller(router)

    with pytest.raises(RiverError) as exc_info:
        caller.get_stream("nonexistent")

    assert "not found" in str(exc_info.value).lower()
