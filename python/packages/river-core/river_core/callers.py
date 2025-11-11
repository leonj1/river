"""Server and client-side caller implementations."""

from typing import Any, AsyncIterator, TypeVar
from pydantic import ValidationError
import base64
import json
from .types import (
    RiverRouter,
    RiverStream,
    StreamContext,
    CallerStreamItem,
    ResumptionToken,
    AbortSignal,
)
from .errors import RiverError, RiverErrorType

InputT = TypeVar("InputT")
AdapterRequestT = TypeVar("AdapterRequestT")


class StreamCaller:
    """Caller for a specific stream."""

    def __init__(self, stream: RiverStream[Any, Any, Any]):
        self._stream = stream

    async def start(
        self,
        input_data: dict[str, Any],
        adapter_request: Any,
    ) -> AsyncIterator[CallerStreamItem[Any]]:
        """
        Start a new stream.

        Args:
            input_data: Input data to validate against the stream's schema
            adapter_request: Framework-specific request object

        Yields:
            Stream items (chunks, special chunks, aborted)
        """
        # Validate input
        try:
            validated_input = self._stream.input_model(**input_data)
        except ValidationError as e:
            raise RiverError(
                message=f"Input validation failed: {e}",
                error_type=RiverErrorType.VALIDATION,
                details={"errors": e.errors()},
            )

        # Create context
        abort_signal = AbortSignal()
        context = StreamContext[Any, Any, Any]()
        context.input = validated_input
        context.adapter_request = adapter_request
        context.abort_signal = abort_signal

        # Start stream via provider
        async for item in self._stream.provider.start_stream(
            stream_storage_id=self._stream.stream_storage_id,
            runner=self._stream.runner,
            context=context,
        ):
            if abort_signal.aborted:
                yield {"type": "aborted"}
                break
            yield item

    async def resume(
        self, resume_key: str
    ) -> AsyncIterator[CallerStreamItem[Any]]:
        """
        Resume a stream from a resumption token.

        Args:
            resume_key: Base64-encoded resumption token

        Yields:
            Stream items from the point of resumption
        """
        # Decode resumption token
        try:
            token_data = json.loads(base64.b64decode(resume_key).decode("utf-8"))
            resumption_token = ResumptionToken(**token_data)  # type: ignore
        except Exception as e:
            raise RiverError(
                message=f"Invalid resumption token: {e}",
                error_type=RiverErrorType.INVALID_RESUMPTION_TOKEN,
            )

        # Resume via provider
        async for item in self._stream.provider.resume_stream(resumption_token):
            yield item


class ServerSideCaller:
    """Server-side caller with access to all streams in a router."""

    def __init__(self, router: RiverRouter):
        self._router = router
        self._callers = {
            key: StreamCaller(stream) for key, stream in router.items()
        }

    def __getattr__(self, name: str) -> StreamCaller:
        """Get caller for a specific stream."""
        if name in self._callers:
            return self._callers[name]
        raise AttributeError(f"Stream '{name}' not found in router")

    def get_stream(self, key: str) -> StreamCaller:
        """Get caller for a specific stream by key."""
        if key not in self._callers:
            raise RiverError(
                message=f"Stream '{key}' not found in router",
                error_type=RiverErrorType.STREAM_NOT_FOUND,
            )
        return self._callers[key]


def create_server_side_caller(router: RiverRouter) -> ServerSideCaller:
    """
    Create a server-side caller for a router.

    Args:
        router: The router containing stream definitions

    Returns:
        A caller that can start and resume streams

    Example:
        ```python
        caller = create_server_side_caller(router)

        # Start a stream
        async for item in caller.chat.start(
            input_data={"prompt": "Hello"},
            adapter_request=request,
        ):
            print(item)

        # Resume a stream
        async for item in caller.chat.resume(resume_key):
            print(item)
        ```
    """
    return ServerSideCaller(router)


def create_client_side_caller(endpoint: str) -> Any:
    """
    Create a client-side caller (placeholder for now).

    This would typically create an HTTP client that connects to
    a River endpoint and handles SSE streaming.

    Args:
        endpoint: The URL of the River endpoint

    Returns:
        A client caller object
    """
    # This is a placeholder - full implementation would be in the adapter
    raise NotImplementedError(
        "Client-side caller is implemented in framework adapters"
    )
