"""Default provider implementation."""

from typing import Any, Callable, AsyncIterator
import asyncio
import time
import uuid
from .types import (
    RiverProvider,
    StreamContext,
    CallerStreamItem,
    ResumptionToken,
    StreamHelper,
    RiverSpecialChunk,
)
from .errors import RiverError, RiverErrorType


class DefaultStreamHelper(StreamHelper[Any]):
    """Default implementation of StreamHelper."""

    def __init__(self, queue: asyncio.Queue[CallerStreamItem[Any]]):
        self._queue = queue

    async def append_chunk(self, chunk: Any) -> None:
        """Append a chunk to the stream."""
        await self._queue.put({"type": "chunk", "chunk": chunk})

    async def append_error(self, error: RiverError) -> None:
        """Append a recoverable error to the stream."""
        special: RiverSpecialChunk = {
            "type": "stream_error",
            "error": error.to_dict(),
        }
        await self._queue.put({"type": "special", "special": special})

    async def send_fatal_error_and_close(self, error: RiverError) -> None:
        """Send a fatal error and close the stream."""
        special: RiverSpecialChunk = {
            "type": "stream_fatal_error",
            "error": error.to_dict(),
        }
        await self._queue.put({"type": "special", "special": special})
        # Signal end of stream
        await self._queue.put(None)  # type: ignore

    async def close(self) -> None:
        """Close the stream successfully."""
        # End marker will be sent by the provider
        pass


class DefaultRiverProvider:
    """
    Default non-resumable provider.

    Streams run in-memory and cannot be resumed.
    """

    provider_id: str = "default"
    is_resumable: bool = False

    async def start_stream(
        self,
        stream_storage_id: str,
        runner: Callable[[StreamContext[Any, Any, Any]], Any],
        context: StreamContext[Any, Any, Any],
    ) -> AsyncIterator[CallerStreamItem[Any]]:
        """Start a new stream."""
        queue: asyncio.Queue[CallerStreamItem[Any] | None] = asyncio.Queue()
        stream_run_id = str(uuid.uuid4())
        start_time = time.time()
        chunk_count = 0

        # Create stream helper
        helper = DefaultStreamHelper(queue)
        context.stream = helper

        # Send stream start
        start_chunk: RiverSpecialChunk = {
            "type": "stream_start",
            "stream_run_id": stream_run_id,
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
                await queue.put({"type": "special", "special": end_chunk})
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
                await queue.put({"type": "special", "special": fatal_chunk})
            finally:
                await queue.put(None)  # Signal completion

        # Start runner task
        runner_task = asyncio.create_task(run_stream())

        # Yield chunks from queue
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break

                # Count regular chunks
                if item["type"] == "chunk":
                    chunk_count += 1

                yield item
        finally:
            # Ensure task completes
            if not runner_task.done():
                runner_task.cancel()
                try:
                    await runner_task
                except asyncio.CancelledError:
                    pass

    async def resume_stream(
        self, resumption_token: ResumptionToken
    ) -> AsyncIterator[CallerStreamItem[Any]]:
        """Resume stream - not supported by default provider."""
        raise RiverError(
            message="Default provider does not support resumption",
            error_type=RiverErrorType.PROVIDER,
        )


def default_river_provider() -> DefaultRiverProvider:
    """Create the default non-resumable provider."""
    return DefaultRiverProvider()
