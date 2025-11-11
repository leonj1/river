"""Integration tests for FastAPI adapter."""

import pytest
import asyncio
import httpx
import json
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel
from river_core import create_river_stream, create_river_router
from river_provider_redis import redis_provider
from river_adapter_fastapi import river_endpoint_handler
from river_core.types import StreamContext


class ChatInput(BaseModel):
    """Test input model."""

    prompt: str
    count: int = 3


@pytest.fixture
def create_test_app(redis_url):
    """Factory for creating test FastAPI apps."""

    def _create_app(runner_fn):
        app = FastAPI()

        stream = (
            create_river_stream()
            .input_schema(ChatInput)
            .provider(redis_provider(redis_url=redis_url, key_prefix="test:fastapi:"))
            .runner(runner_fn)
        )

        router = create_river_router({"chat": stream})
        handlers = river_endpoint_handler(router)

        @app.post("/api/river")
        async def start(request: Request):
            return await handlers["post"](request)

        @app.get("/api/river")
        async def resume(request: Request):
            return await handlers["get"](request)

        return app

    return _create_app


async def parse_sse_stream(response):
    """Parse SSE stream from response."""
    chunks = []
    special_chunks = []

    async for line in response.aiter_lines():
        if line.startswith("data: "):
            data_str = line[6:]  # Remove "data: " prefix
            try:
                data = json.loads(data_str)
                if data["type"] == "chunk":
                    chunks.append(data["chunk"])
                elif data["type"] == "special":
                    special_chunks.append(data["special"])
            except json.JSONDecodeError:
                pass

    return chunks, special_chunks


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fastapi_start_stream(create_test_app):
    """Test starting a stream via FastAPI endpoint."""

    async def test_runner(ctx: StreamContext):
        for i in range(ctx.input.count):
            await ctx.stream.append_chunk(f"chunk-{i}")
        await ctx.stream.close()

    app = create_test_app(test_runner)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/river",
            json={"router_stream_key": "chat", "input": {"prompt": "test", "count": 3}},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            chunks, special_chunks = await parse_sse_stream(response)

            assert len(chunks) == 3
            assert chunks == ["chunk-0", "chunk-1", "chunk-2"]
            assert len(special_chunks) >= 2  # stream_start and stream_end


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fastapi_validation_error(create_test_app):
    """Test validation error handling."""

    async def test_runner(ctx: StreamContext):
        await ctx.stream.close()

    app = create_test_app(test_runner)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Send invalid input (missing required field)
        response = await client.post(
            "/api/river",
            json={"router_stream_key": "chat", "input": {}},
            headers={"Accept": "text/event-stream"},
        )

        # Should return 400 for validation error
        assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fastapi_stream_not_found(create_test_app):
    """Test error when stream key not found."""

    async def test_runner(ctx: StreamContext):
        await ctx.stream.close()

    app = create_test_app(test_runner)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/river",
            json={
                "router_stream_key": "nonexistent",
                "input": {"prompt": "test"},
            },
            headers={"Accept": "text/event-stream"},
        )

        # Should return 404
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fastapi_resume_stream(create_test_app):
    """Test resuming a stream via GET endpoint."""

    async def test_runner(ctx: StreamContext):
        for i in range(5):
            await ctx.stream.append_chunk(f"data-{i}")
            await asyncio.sleep(0.01)
        await ctx.stream.close()

    app = create_test_app(test_runner)
    transport = httpx.ASGITransport(app=app)

    # First, start a stream and get resumption token
    resumption_token = None

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/river",
            json={"router_stream_key": "chat", "input": {"prompt": "test", "count": 5}},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            # Extract resumption token from stream_start
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if (
                        data["type"] == "special"
                        and data["special"]["type"] == "stream_start"
                    ):
                        resumption_token = data["special"].get(
                            "encoded_resumption_token"
                        )
                        break

        assert resumption_token is not None

        # Wait for stream to complete and be written to Redis
        await asyncio.sleep(0.2)

        # Now resume the stream
        async with client.stream(
            "GET",
            f"/api/river?resumeKey={resumption_token}",
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            # Parse resumed chunks
            chunks, _ = await parse_sse_stream(response)

            # Should get all 5 chunks from Redis
            assert len(chunks) == 5
            assert chunks == ["data-0", "data-1", "data-2", "data-3", "data-4"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fastapi_error_in_stream(create_test_app):
    """Test error handling during stream execution."""
    from river_core.errors import RiverError, RiverErrorType

    async def error_runner(ctx: StreamContext):
        await ctx.stream.append_chunk("before")
        await ctx.stream.append_error(
            RiverError("Test error", RiverErrorType.RUNNER_ERROR)
        )
        await ctx.stream.append_chunk("after")
        await ctx.stream.close()

    app = create_test_app(error_runner)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/river",
            json={"router_stream_key": "chat", "input": {"prompt": "test"}},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            chunks = []
            errors = []

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data["type"] == "chunk":
                        chunks.append(data["chunk"])
                    elif data["type"] == "special":
                        if data["special"]["type"] == "stream_error":
                            errors.append(data["special"]["error"])

            assert len(chunks) == 2
            assert chunks == ["before", "after"]
            assert len(errors) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fastapi_concurrent_requests(create_test_app):
    """Test handling multiple concurrent requests."""

    async def test_runner(ctx: StreamContext):
        for i in range(ctx.input.count):
            await ctx.stream.append_chunk(f"{ctx.input.prompt}-{i}")
        await ctx.stream.close()

    app = create_test_app(test_runner)
    transport = httpx.ASGITransport(app=app)

    async def make_request(prompt: str, count: int):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/api/river",
                json={
                    "router_stream_key": "chat",
                    "input": {"prompt": prompt, "count": count},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                return response.status_code

    # Make 3 concurrent requests
    results = await asyncio.gather(
        make_request("req1", 2), make_request("req2", 3), make_request("req3", 4)
    )

    # All should succeed
    assert all(status == 200 for status in results)
