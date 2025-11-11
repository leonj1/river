"""Redis-backed resumable provider implementation."""

from typing import Any, Callable, AsyncIterator
import asyncio
import time
import uuid
import json
from redis import asyncio as aioredis
from river_core.types import (
    StreamContext,
    CallerStreamItem,
    ResumptionToken,
    StreamHelper,
    RiverSpecialChunk,
)
from river_core.errors import RiverError, RiverErrorType
from river_core.helpers import encode_resumption_token


class RedisStreamHelper(StreamHelper[Any]):
    """Redis-backed stream helper that dual-writes to Redis and live stream."""

    def __init__(
        self,
        queue: asyncio.Queue[CallerStreamItem[Any]],
        redis_client: aioredis.Redis,  # type: ignore
        stream_key: str,
    ):
        self._queue = queue
        self._redis = redis_client
        self._stream_key = stream_key

    async def _write_to_redis(self, item: CallerStreamItem[Any]) -> None:
        """Write item to Redis stream."""
        try:
            serialized = json.dumps({"item": item})
            await self._redis.xadd(self._stream_key, {"data": serialized})
        except Exception as e:
            # Log error but don't fail the stream
            print(f"Warning: Failed to write to Redis: {e}")

    async def append_chunk(self, chunk: Any) -> None:
        """Append a chunk to both Redis and the live stream."""
        item: CallerStreamItem[Any] = {"type": "chunk", "chunk": chunk}
        await self._write_to_redis(item)
        await self._queue.put(item)

    async def append_error(self, error: RiverError) -> None:
        """Append a recoverable error."""
        special: RiverSpecialChunk = {
            "type": "stream_error",
            "error": error.to_dict(),
        }
        item: CallerStreamItem[Any] = {"type": "special", "special": special}
        await self._write_to_redis(item)
        await self._queue.put(item)

    async def send_fatal_error_and_close(self, error: RiverError) -> None:
        """Send a fatal error and close the stream."""
        special: RiverSpecialChunk = {
            "type": "stream_fatal_error",
            "error": error.to_dict(),
        }
        item: CallerStreamItem[Any] = {"type": "special", "special": special}
        await self._write_to_redis(item)
        await self._queue.put(item)

        # Write end marker to Redis
        await self._redis.xadd(self._stream_key, {"end": "true"})
        await self._queue.put(None)  # type: ignore

    async def close(self) -> None:
        """Close the stream successfully."""
        # End marker will be sent by the provider
        pass


class RedisRiverProvider:
    """
    Redis-backed provider that enables resumable streams.

    Streams are persisted to Redis Streams, allowing clients to
    disconnect and resume from where they left off.
    """

    provider_id: str = "redis"
    is_resumable: bool = True

    def __init__(self, redis_url: str, key_prefix: str = "river:stream:"):
        """
        Initialize Redis provider.

        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379")
            key_prefix: Prefix for Redis keys
        """
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._redis_client: aioredis.Redis | None = None  # type: ignore

    async def _get_redis(self) -> aioredis.Redis:  # type: ignore
        """Get or create Redis client."""
        if self._redis_client is None:
            self._redis_client = await aioredis.from_url(self._redis_url)
        return self._redis_client

    def _make_stream_key(self, stream_storage_id: str, stream_run_id: str) -> str:
        """Generate Redis stream key."""
        return f"{self._key_prefix}{stream_storage_id}:{stream_run_id}"

    async def start_stream(
        self,
        stream_storage_id: str,
        runner: Callable[[StreamContext[Any, Any, Any]], Any],
        context: StreamContext[Any, Any, Any],
    ) -> AsyncIterator[CallerStreamItem[Any]]:
        """Start a new resumable stream."""
        redis = await self._get_redis()
        queue: asyncio.Queue[CallerStreamItem[Any] | None] = asyncio.Queue()
        stream_run_id = str(uuid.uuid4())
        stream_key = self._make_stream_key(stream_storage_id, stream_run_id)
        start_time = time.time()
        chunk_count = 0

        # Create resumption token
        resumption_token = ResumptionToken(
            provider_id=self.provider_id,
            router_stream_key="",  # Will be set by adapter
            stream_storage_id=stream_storage_id,
            stream_run_id=stream_run_id,
        )
        encoded_token = encode_resumption_token(resumption_token)

        # Create Redis-backed stream helper
        helper = RedisStreamHelper(queue, redis, stream_key)
        context.stream = helper

        # Send stream start with resumption token
        start_chunk: RiverSpecialChunk = {
            "type": "stream_start",
            "stream_run_id": stream_run_id,
            "encoded_resumption_token": encoded_token,
        }
        yield {"type": "special", "special": start_chunk}

        # Run the stream in background
        async def run_stream() -> None:
            try:
                await runner(context)

                # Send stream end
                end_time = time.time()
                end_chunk: RiverSpecialChunk = {
                    "type": "stream_end",
                    "total_chunks": chunk_count,
                    "total_time_ms": (end_time - start_time) * 1000,
                }
                item: CallerStreamItem[Any] = {"type": "special", "special": end_chunk}
                await helper._write_to_redis(item)
                await queue.put(item)

                # Write end marker to Redis
                await redis.xadd(stream_key, {"end": "true"})
            except Exception as e:
                # Send fatal error
                error = RiverError(
                    message=str(e),
                    error_type=RiverErrorType.RUNNER_ERROR,
                )
                fatal_chunk: RiverSpecialChunk = {
                    "type": "stream_fatal_error",
                    "error": error.to_dict(),
                }
                item = {"type": "special", "special": fatal_chunk}
                await helper._write_to_redis(item)
                await queue.put(item)

                # Write end marker
                await redis.xadd(stream_key, {"end": "true"})
            finally:
                await queue.put(None)  # Signal completion

        # Start runner task (non-blocking)
        asyncio.create_task(run_stream())

        # Yield chunks from queue
        while True:
            item = await queue.get()
            if item is None:
                break

            # Count regular chunks
            if item["type"] == "chunk":
                chunk_count += 1

            yield item

    async def resume_stream(
        self, resumption_token: ResumptionToken
    ) -> AsyncIterator[CallerStreamItem[Any]]:
        """Resume a stream from Redis."""
        redis = await self._get_redis()
        stream_key = self._make_stream_key(
            resumption_token["stream_storage_id"],
            resumption_token["stream_run_id"],
        )

        # Check if stream exists
        exists = await redis.exists(stream_key)
        if not exists:
            raise RiverError(
                message="Stream not found or has expired",
                error_type=RiverErrorType.STREAM_NOT_FOUND,
            )

        # Read from Redis stream
        last_id = "0-0"  # Start from beginning
        max_attempts = 1000
        attempts = 0

        while attempts < max_attempts:
            attempts += 1

            # Read with blocking
            result = await redis.xread({stream_key: last_id}, block=10, count=10)

            if not result:
                # No new data, check if stream ended
                # In a production system, you'd have better end detection
                await asyncio.sleep(0.01)
                continue

            # Process messages
            for _stream_key, messages in result:
                for msg_id, fields in messages:
                    last_id = msg_id.decode() if isinstance(msg_id, bytes) else msg_id

                    # Check for end marker
                    if b"end" in fields or "end" in fields:
                        return

                    # Parse and yield item
                    data_field = fields.get(b"data") or fields.get("data")
                    if data_field:
                        data_str = (
                            data_field.decode()
                            if isinstance(data_field, bytes)
                            else data_field
                        )
                        data = json.loads(data_str)
                        item = data["item"]
                        yield item

                        # Check if this was a fatal error (stream should end)
                        if item.get("type") == "special":
                            special = item.get("special", {})
                            if special.get("type") in [
                                "stream_fatal_error",
                                "stream_end",
                            ]:
                                return

        # Safety limit reached
        raise RiverError(
            message="Resume safety limit reached",
            error_type=RiverErrorType.PROVIDER,
        )


def redis_provider(
    redis_url: str = "redis://localhost:6379",
    key_prefix: str = "river:stream:",
) -> RedisRiverProvider:
    """
    Create a Redis provider for resumable streams.

    Args:
        redis_url: Redis connection URL
        key_prefix: Prefix for Redis stream keys

    Returns:
        A configured Redis provider

    Example:
        ```python
        provider = redis_provider(redis_url="redis://localhost:6379")

        stream = (
            create_river_stream()
            .input_schema(MyInput)
            .provider(provider)
            .runner(my_runner)
        )
        ```
    """
    return RedisRiverProvider(redis_url=redis_url, key_prefix=key_prefix)
