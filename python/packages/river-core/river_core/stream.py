"""Stream builder implementation."""

from typing import TypeVar, Generic, Callable, Any, cast
from pydantic import BaseModel
from .types import RiverStream, RiverProvider, StreamContext
import uuid

InputT = TypeVar("InputT", bound=BaseModel)
ChunkT = TypeVar("ChunkT")
AdapterRequestT = TypeVar("AdapterRequestT")


class StreamBuilderStep1(Generic[ChunkT]):
    """First step: define input schema."""

    def input_schema(
        self, model: type[InputT]
    ) -> "StreamBuilderStep2[InputT, ChunkT]":
        """Define the input validation schema using Pydantic."""
        return StreamBuilderStep2(input_model=model)


class StreamBuilderStep2(Generic[InputT, ChunkT]):
    """Second step: choose provider."""

    def __init__(self, input_model: type[InputT]):
        self._input_model = input_model

    def provider(
        self, provider: RiverProvider[ChunkT]
    ) -> "StreamBuilderStep3[InputT, ChunkT]":
        """Set the stream provider (e.g., Redis, in-memory)."""
        return StreamBuilderStep3(
            input_model=self._input_model,
            provider=provider,
        )


class StreamBuilderStep3(Generic[InputT, ChunkT]):
    """Third step: define runner."""

    def __init__(
        self,
        input_model: type[InputT],
        provider: RiverProvider[ChunkT],
    ):
        self._input_model = input_model
        self._provider = provider

    def runner(
        self,
        runner_fn: Callable[[StreamContext[InputT, ChunkT, AdapterRequestT]], Any],
        stream_storage_id: str | None = None,
    ) -> RiverStream[InputT, ChunkT, AdapterRequestT]:
        """
        Define the stream execution logic.

        Args:
            runner_fn: Async function that implements the stream logic
            stream_storage_id: Optional custom storage ID (auto-generated if not provided)
        """
        storage_id = stream_storage_id or str(uuid.uuid4())

        return RiverStream(
            input_model=self._input_model,
            provider=self._provider,
            runner=runner_fn,
            stream_storage_id=storage_id,
        )


def create_river_stream() -> StreamBuilderStep1[Any]:
    """
    Create a new River stream with a fluent builder API.

    Example:
        ```python
        from river_core import create_river_stream
        from pydantic import BaseModel

        class MyInput(BaseModel):
            prompt: str

        stream = (
            create_river_stream()
            .input_schema(MyInput)
            .provider(my_provider)
            .runner(async lambda ctx: {
                await ctx.stream.append_chunk("Hello")
                await ctx.stream.close()
            })
        )
        ```
    """
    return StreamBuilderStep1()
