"""Integration tests for Redis provider."""

import pytest
import asyncio
from pydantic import BaseModel
from river_core import create_river_stream, create_river_router
from river_provider_redis import redis_provider
from river_core.types import StreamContext


class TestInput(BaseModel):
    """Test input model."""

    message: str
    count: int = 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_provider_start_stream(redis_url, clean_redis):
    """Test starting a stream with Redis provider."""

    async def test_runner(ctx: StreamContext):
        for i in range(ctx.input.count):
            await ctx.stream.append_chunk(f"{ctx.input.message}-{i}")
            await asyncio.sleep(0.01)
        await ctx.stream.close()

    provider = redis_provider(redis_url=redis_url, key_prefix="test:stream:")

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(provider)
        .runner(test_runner)
    )

    # Execute stream
    context = StreamContext()
    context.input = TestInput(message="test", count=3)

    chunks = []
    special_chunks = []
    resumption_token = None

    async for item in provider.start_stream(
        stream_storage_id=stream.stream_storage_id,
        runner=stream.runner,
        context=context,
    ):
        if item["type"] == "chunk":
            chunks.append(item["chunk"])
        elif item["type"] == "special":
            special = item["special"]
            special_chunks.append(special)
            if special["type"] == "stream_start":
                resumption_token = special.get("encoded_resumption_token")

    # Verify chunks
    assert len(chunks) == 3
    assert chunks == ["test-0", "test-1", "test-2"]

    # Verify special chunks
    assert len(special_chunks) == 2
    assert special_chunks[0]["type"] == "stream_start"
    assert special_chunks[1]["type"] == "stream_end"
    assert resumption_token is not None
    assert "stream_run_id" in special_chunks[0]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_provider_resume_stream(redis_url, clean_redis):
    """Test resuming a stream from Redis."""

    async def test_runner(ctx: StreamContext):
        for i in range(ctx.input.count):
            await ctx.stream.append_chunk(f"chunk-{i}")
            await asyncio.sleep(0.01)
        await ctx.stream.close()

    provider = redis_provider(redis_url=redis_url, key_prefix="test:resume:")

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(provider)
        .runner(test_runner)
    )

    # Start stream and collect resumption token
    context = StreamContext()
    context.input = TestInput(message="test", count=5)

    resumption_token = None
    start_chunks = []

    async for item in provider.start_stream(
        stream_storage_id=stream.stream_storage_id,
        runner=stream.runner,
        context=context,
    ):
        if item["type"] == "chunk":
            start_chunks.append(item["chunk"])
        elif item["type"] == "special":
            special = item["special"]
            if special["type"] == "stream_start":
                resumption_token = special.get("encoded_resumption_token")

    assert len(start_chunks) == 5
    assert resumption_token is not None

    # Decode token and resume
    from river_core.helpers import decode_resumption_token

    token = decode_resumption_token(resumption_token)

    # Wait a bit to ensure Redis write completes
    await asyncio.sleep(0.1)

    # Resume stream
    resume_chunks = []
    async for item in provider.resume_stream(token):
        if item["type"] == "chunk":
            resume_chunks.append(item["chunk"])

    # Should get all chunks again from Redis
    assert len(resume_chunks) == 5
    assert resume_chunks == start_chunks


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_provider_persistence(redis_url, redis_client, clean_redis):
    """Test that chunks are actually persisted to Redis."""

    async def test_runner(ctx: StreamContext):
        for i in range(3):
            await ctx.stream.append_chunk(f"data-{i}")
        await ctx.stream.close()

    provider = redis_provider(redis_url=redis_url, key_prefix="test:persist:")

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(provider)
        .runner(test_runner)
    )

    context = StreamContext()
    context.input = TestInput(message="test")

    # Start stream
    async for item in provider.start_stream(
        stream_storage_id=stream.stream_storage_id,
        runner=stream.runner,
        context=context,
    ):
        pass

    # Wait for Redis writes
    await asyncio.sleep(0.1)

    # Check Redis directly
    keys = await redis_client.keys("test:persist:*")
    assert len(keys) > 0

    # Verify stream exists and has data
    stream_key = keys[0]
    stream_length = await redis_client.xlen(stream_key)
    assert stream_length > 0  # Should have chunks + end marker


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_provider_error_handling(redis_url, clean_redis):
    """Test error handling in Redis provider."""
    from river_core.errors import RiverError, RiverErrorType

    async def error_runner(ctx: StreamContext):
        await ctx.stream.append_chunk("before-error")
        await ctx.stream.append_error(
            RiverError("Test error", RiverErrorType.RUNNER_ERROR)
        )
        await ctx.stream.append_chunk("after-error")
        await ctx.stream.close()

    provider = redis_provider(redis_url=redis_url, key_prefix="test:error:")

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(provider)
        .runner(error_runner)
    )

    context = StreamContext()
    context.input = TestInput(message="test")

    chunks = []
    errors = []

    async for item in provider.start_stream(
        stream_storage_id=stream.stream_storage_id,
        runner=stream.runner,
        context=context,
    ):
        if item["type"] == "chunk":
            chunks.append(item["chunk"])
        elif item["type"] == "special":
            if item["special"]["type"] == "stream_error":
                errors.append(item["special"]["error"])

    # Should have chunks before and after error
    assert len(chunks) == 2
    assert chunks == ["before-error", "after-error"]

    # Should have one error
    assert len(errors) == 1
    assert errors[0]["message"] == "Test error"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_provider_fatal_error(redis_url, clean_redis):
    """Test fatal error handling."""
    from river_core.errors import RiverError, RiverErrorType

    async def fatal_error_runner(ctx: StreamContext):
        await ctx.stream.append_chunk("before-fatal")
        await ctx.stream.send_fatal_error_and_close(
            RiverError("Fatal error", RiverErrorType.RUNNER_ERROR)
        )
        # This should not execute
        await ctx.stream.append_chunk("after-fatal")

    provider = redis_provider(redis_url=redis_url, key_prefix="test:fatal:")

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(provider)
        .runner(fatal_error_runner)
    )

    context = StreamContext()
    context.input = TestInput(message="test")

    chunks = []
    fatal_errors = []

    async for item in provider.start_stream(
        stream_storage_id=stream.stream_storage_id,
        runner=stream.runner,
        context=context,
    ):
        if item["type"] == "chunk":
            chunks.append(item["chunk"])
        elif item["type"] == "special":
            if item["special"]["type"] == "stream_fatal_error":
                fatal_errors.append(item["special"]["error"])

    # Should only have chunk before fatal error
    assert len(chunks) == 1
    assert chunks == ["before-fatal"]

    # Should have fatal error
    assert len(fatal_errors) == 1
    assert fatal_errors[0]["message"] == "Fatal error"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_provider_large_stream(redis_url, clean_redis):
    """Test streaming many chunks."""

    async def large_runner(ctx: StreamContext):
        for i in range(100):
            await ctx.stream.append_chunk(i)
        await ctx.stream.close()

    provider = redis_provider(redis_url=redis_url, key_prefix="test:large:")

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(provider)
        .runner(large_runner)
    )

    context = StreamContext()
    context.input = TestInput(message="test", count=100)

    chunks = []
    async for item in provider.start_stream(
        stream_storage_id=stream.stream_storage_id,
        runner=stream.runner,
        context=context,
    ):
        if item["type"] == "chunk":
            chunks.append(item["chunk"])

    assert len(chunks) == 100
    assert chunks == list(range(100))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_provider_concurrent_streams(redis_url, clean_redis):
    """Test multiple concurrent streams."""

    async def test_runner(ctx: StreamContext):
        for i in range(ctx.input.count):
            await ctx.stream.append_chunk(f"{ctx.input.message}-{i}")
        await ctx.stream.close()

    provider = redis_provider(redis_url=redis_url, key_prefix="test:concurrent:")

    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(provider)
        .runner(test_runner)
    )

    # Start 3 streams concurrently
    async def run_stream(message: str, count: int):
        context = StreamContext()
        context.input = TestInput(message=message, count=count)

        chunks = []
        async for item in provider.start_stream(
            stream_storage_id=stream.stream_storage_id,
            runner=stream.runner,
            context=context,
        ):
            if item["type"] == "chunk":
                chunks.append(item["chunk"])
        return chunks

    results = await asyncio.gather(
        run_stream("stream1", 3),
        run_stream("stream2", 4),
        run_stream("stream3", 2),
    )

    assert len(results[0]) == 3
    assert len(results[1]) == 4
    assert len(results[2]) == 2
