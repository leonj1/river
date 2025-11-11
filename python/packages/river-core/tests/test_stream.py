"""Tests for River stream creation and execution."""

import pytest
from pydantic import BaseModel
from river_core import create_river_stream, default_river_provider
from river_core.types import StreamContext


class TestInput(BaseModel):
    """Test input model."""

    message: str


@pytest.mark.asyncio
async def test_create_stream():
    """Test stream creation with builder pattern."""

    async def test_runner(ctx: StreamContext):
        await ctx.stream.append_chunk(f"Echo: {ctx.input.message}")
        await ctx.stream.close()

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(default_river_provider())
        .runner(test_runner)
    )

    assert stream is not None
    assert stream.input_model == TestInput
    assert stream.provider.provider_id == "default"
    assert stream.runner == test_runner


@pytest.mark.asyncio
async def test_stream_execution():
    """Test executing a stream."""

    chunks = []

    async def test_runner(ctx: StreamContext):
        for i in range(3):
            await ctx.stream.append_chunk(i)
        await ctx.stream.close()

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(default_river_provider())
        .runner(test_runner)
    )

    # Execute stream via provider
    context = StreamContext()
    context.input = TestInput(message="test")

    async for item in stream.provider.start_stream(
        stream_storage_id=stream.stream_storage_id,
        runner=stream.runner,
        context=context,
    ):
        if item["type"] == "chunk":
            chunks.append(item["chunk"])

    assert chunks == [0, 1, 2]


@pytest.mark.asyncio
async def test_stream_special_chunks():
    """Test that special chunks are emitted."""

    special_chunks = []

    async def test_runner(ctx: StreamContext):
        await ctx.stream.append_chunk("data")
        await ctx.stream.close()

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(default_river_provider())
        .runner(test_runner)
    )

    context = StreamContext()
    context.input = TestInput(message="test")

    async for item in stream.provider.start_stream(
        stream_storage_id=stream.stream_storage_id,
        runner=stream.runner,
        context=context,
    ):
        if item["type"] == "special":
            special_chunks.append(item["special"])

    # Should have stream_start and stream_end
    assert len(special_chunks) == 2
    assert special_chunks[0]["type"] == "stream_start"
    assert special_chunks[1]["type"] == "stream_end"
    assert "stream_run_id" in special_chunks[0]
    assert "total_chunks" in special_chunks[1]
