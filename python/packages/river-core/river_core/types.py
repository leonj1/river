"""Core types for River."""

from typing import (
    Any,
    TypeVar,
    Generic,
    Protocol,
    Callable,
    AsyncIterator,
    TypedDict,
    Literal,
    Union,
)
from typing_extensions import NotRequired
from pydantic import BaseModel
from abc import ABC, abstractmethod

# Type variables
InputT = TypeVar("InputT", bound=BaseModel)
ChunkT = TypeVar("ChunkT")
AdapterRequestT = TypeVar("AdapterRequestT")


class ResumptionToken(TypedDict):
    """Token used to resume a stream."""

    provider_id: str
    router_stream_key: str
    stream_storage_id: str
    stream_run_id: str


class StreamHelper(Generic[ChunkT]):
    """Helper methods available in the stream runner."""

    @abstractmethod
    async def append_chunk(self, chunk: ChunkT) -> None:
        """Append a chunk to the stream."""
        ...

    @abstractmethod
    async def append_error(self, error: "RiverError") -> None:
        """Append a recoverable error to the stream."""
        ...

    @abstractmethod
    async def send_fatal_error_and_close(self, error: "RiverError") -> None:
        """Send a fatal error and close the stream."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the stream successfully."""
        ...


class StreamContext(Generic[InputT, ChunkT, AdapterRequestT]):
    """Context provided to stream runner."""

    input: InputT
    stream: StreamHelper[ChunkT]
    adapter_request: AdapterRequestT
    abort_signal: "AbortSignal"


class AbortSignal:
    """Signal to abort stream execution."""

    def __init__(self) -> None:
        self._aborted = False
        self._callbacks: list[Callable[[], None]] = []

    @property
    def aborted(self) -> bool:
        """Check if stream has been aborted."""
        return self._aborted

    def abort(self) -> None:
        """Abort the stream."""
        self._aborted = True
        for callback in self._callbacks:
            callback()

    def on_abort(self, callback: Callable[[], None]) -> None:
        """Register callback for abort event."""
        self._callbacks.append(callback)


class RiverSpecialChunkType:
    """Special chunk type markers."""

    STREAM_START = "stream_start"
    STREAM_END = "stream_end"
    STREAM_ERROR = "stream_error"
    STREAM_FATAL_ERROR = "stream_fatal_error"


class StreamStartChunk(TypedDict):
    """Stream start special chunk."""

    type: Literal["stream_start"]
    stream_run_id: str
    encoded_resumption_token: NotRequired[str]


class StreamEndChunk(TypedDict):
    """Stream end special chunk."""

    type: Literal["stream_end"]
    total_chunks: int
    total_time_ms: float


class StreamErrorChunk(TypedDict):
    """Stream error (recoverable) special chunk."""

    type: Literal["stream_error"]
    error: dict[str, Any]  # Serialized RiverError


class StreamFatalErrorChunk(TypedDict):
    """Stream fatal error special chunk."""

    type: Literal["stream_fatal_error"]
    error: dict[str, Any]  # Serialized RiverError


RiverSpecialChunk = Union[
    StreamStartChunk, StreamEndChunk, StreamErrorChunk, StreamFatalErrorChunk
]


class ChunkItem(TypedDict, Generic[ChunkT]):
    """Regular chunk item."""

    type: Literal["chunk"]
    chunk: ChunkT


class SpecialItem(TypedDict):
    """Special chunk item."""

    type: Literal["special"]
    special: RiverSpecialChunk


class AbortedItem(TypedDict):
    """Aborted item."""

    type: Literal["aborted"]


CallerStreamItem = Union[ChunkItem[ChunkT], SpecialItem, AbortedItem]


class RiverProvider(Protocol[ChunkT]):
    """Provider protocol for stream storage/resumption."""

    provider_id: str
    is_resumable: bool

    async def start_stream(
        self,
        stream_storage_id: str,
        runner: Callable[[StreamContext[Any, ChunkT, Any]], Any],
        context: StreamContext[Any, ChunkT, Any],
    ) -> AsyncIterator[CallerStreamItem[ChunkT]]:
        """Start a new stream."""
        ...

    async def resume_stream(
        self, resumption_token: ResumptionToken
    ) -> AsyncIterator[CallerStreamItem[ChunkT]]:
        """Resume an existing stream."""
        ...


class RiverStream(Generic[InputT, ChunkT, AdapterRequestT]):
    """A River stream definition."""

    def __init__(
        self,
        input_model: type[InputT],
        provider: RiverProvider[ChunkT],
        runner: Callable[[StreamContext[InputT, ChunkT, AdapterRequestT]], Any],
        stream_storage_id: str,
    ):
        self.input_model = input_model
        self.provider = provider
        self.runner = runner
        self.stream_storage_id = stream_storage_id


class RiverRouter(dict[str, RiverStream[Any, Any, Any]]):
    """A collection of named streams."""

    pass


# Import here to avoid circular dependency
from .errors import RiverError  # noqa: E402

# Update forward references
StreamErrorChunk.__annotations__["error"] = dict[str, Any]
StreamFatalErrorChunk.__annotations__["error"] = dict[str, Any]
