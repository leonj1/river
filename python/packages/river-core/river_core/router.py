"""Router implementation."""

from typing import Any
from .types import RiverRouter, RiverStream


def create_river_router(streams: dict[str, RiverStream[Any, Any, Any]]) -> RiverRouter:
    """
    Create a router from a collection of streams.

    Args:
        streams: Dictionary mapping stream names to stream definitions

    Returns:
        A RiverRouter that can be used with adapters and callers

    Example:
        ```python
        router = create_river_router({
            "chat": chat_stream,
            "completion": completion_stream,
        })
        ```
    """
    return RiverRouter(streams)
