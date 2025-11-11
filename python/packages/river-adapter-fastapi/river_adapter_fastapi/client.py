"""FastAPI client-side adapter for River streams."""

from typing import Any, Callable, TypeVar
import json
import asyncio
import httpx

RouterT = TypeVar("RouterT")


class StreamClient:
    """Client for a specific stream."""

    def __init__(self, endpoint: str, stream_key: str):
        self._endpoint = endpoint
        self._stream_key = stream_key
        self._abort_controller: asyncio.Event | None = None

    async def start(
        self,
        input_data: dict[str, Any],
        on_chunk: Callable[[Any], None] | None = None,
        on_special: Callable[[Any], None] | None = None,
        on_error: Callable[[Any], None] | None = None,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """
        Start a new stream.

        Args:
            input_data: Input data for the stream
            on_chunk: Callback for regular chunks
            on_special: Callback for special chunks
            on_error: Callback for errors
            on_complete: Callback for stream completion
        """
        self._abort_controller = asyncio.Event()

        async with httpx.AsyncClient() as client:
            request_body = {
                "router_stream_key": self._stream_key,
                "input": input_data,
            }

            try:
                async with client.stream(
                    "POST",
                    self._endpoint,
                    json=request_body,
                    headers={"Accept": "text/event-stream"},
                    timeout=None,
                ) as response:
                    response.raise_for_status()

                    # Process SSE stream
                    buffer = ""
                    async for chunk in response.aiter_text():
                        if self._abort_controller.is_set():
                            break

                        buffer += chunk

                        # Process complete SSE messages
                        while "\n\n" in buffer:
                            message, buffer = buffer.split("\n\n", 1)

                            # Parse SSE message
                            if message.startswith("data: "):
                                data_str = message[6:]  # Remove "data: " prefix
                                try:
                                    item = json.loads(data_str)

                                    # Handle different item types
                                    if item["type"] == "chunk":
                                        if on_chunk:
                                            on_chunk(item["chunk"])
                                    elif item["type"] == "special":
                                        if on_special:
                                            on_special(item["special"])
                                    elif item["type"] == "aborted":
                                        break

                                except json.JSONDecodeError:
                                    pass

                    # Stream completed
                    if on_complete:
                        on_complete()

            except httpx.HTTPError as e:
                if on_error:
                    on_error({"message": str(e), "type": "network"})
            except Exception as e:
                if on_error:
                    on_error({"message": str(e), "type": "unknown"})

    async def resume(
        self,
        resume_key: str,
        on_chunk: Callable[[Any], None] | None = None,
        on_special: Callable[[Any], None] | None = None,
        on_error: Callable[[Any], None] | None = None,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """
        Resume a stream from a resumption token.

        Args:
            resume_key: The resumption token
            on_chunk: Callback for regular chunks
            on_special: Callback for special chunks
            on_error: Callback for errors
            on_complete: Callback for stream completion
        """
        self._abort_controller = asyncio.Event()

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "GET",
                    f"{self._endpoint}?resumeKey={resume_key}",
                    headers={"Accept": "text/event-stream"},
                    timeout=None,
                ) as response:
                    response.raise_for_status()

                    # Process SSE stream (same as start)
                    buffer = ""
                    async for chunk in response.aiter_text():
                        if self._abort_controller.is_set():
                            break

                        buffer += chunk

                        while "\n\n" in buffer:
                            message, buffer = buffer.split("\n\n", 1)

                            if message.startswith("data: "):
                                data_str = message[6:]
                                try:
                                    item = json.loads(data_str)

                                    if item["type"] == "chunk":
                                        if on_chunk:
                                            on_chunk(item["chunk"])
                                    elif item["type"] == "special":
                                        if on_special:
                                            on_special(item["special"])
                                    elif item["type"] == "aborted":
                                        break

                                except json.JSONDecodeError:
                                    pass

                    if on_complete:
                        on_complete()

            except httpx.HTTPError as e:
                if on_error:
                    on_error({"message": str(e), "type": "network"})
            except Exception as e:
                if on_error:
                    on_error({"message": str(e), "type": "unknown"})

    def abort(self) -> None:
        """Abort the current stream."""
        if self._abort_controller:
            self._abort_controller.set()


class RiverClient:
    """Client for a River router."""

    def __init__(self, endpoint: str):
        self._endpoint = endpoint
        self._streams: dict[str, StreamClient] = {}

    def __getattr__(self, name: str) -> StreamClient:
        """Get client for a specific stream."""
        if name not in self._streams:
            self._streams[name] = StreamClient(self._endpoint, name)
        return self._streams[name]


def create_river_client(endpoint: str) -> RiverClient:
    """
    Create a River client for a FastAPI endpoint.

    Args:
        endpoint: The URL of the River endpoint (e.g., "http://localhost:8000/api/river")

    Returns:
        A client that can start and resume streams

    Example:
        ```python
        client = create_river_client("http://localhost:8000/api/river")

        # Start a stream
        await client.chat.start(
            input_data={"prompt": "Hello"},
            on_chunk=lambda chunk: print(chunk),
            on_complete=lambda: print("Done"),
        )

        # Resume a stream
        await client.chat.resume(
            resume_key=token,
            on_chunk=lambda chunk: print(chunk),
        )
        ```
    """
    return RiverClient(endpoint)
