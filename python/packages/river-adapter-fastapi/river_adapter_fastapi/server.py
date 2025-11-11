"""FastAPI server-side adapter for River streams."""

from typing import Any
import json
from fastapi import Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, ValidationError
from river_core import create_server_side_caller, RiverRouter
from river_core.errors import RiverError


class StartStreamRequest(BaseModel):
    """Request body for starting a stream."""

    router_stream_key: str
    input: dict[str, Any]


async def _sse_generator(items_iter: Any) -> Any:
    """
    Convert stream items to SSE format.

    Args:
        items_iter: Async iterator of stream items

    Yields:
        SSE-formatted data
    """
    async for item in items_iter:
        # Serialize item to JSON
        json_data = json.dumps(item)
        # Yield in SSE format: "data: {json}\n\n"
        yield {"data": json_data}


def river_endpoint_handler(router: RiverRouter) -> dict[str, Any]:
    """
    Create FastAPI endpoint handlers for a River router.

    Returns a dict with POST and GET handlers for starting and resuming streams.

    Args:
        router: The River router containing stream definitions

    Returns:
        Dict with 'post' and 'get' handler functions

    Example:
        ```python
        from fastapi import FastAPI
        from river_adapter_fastapi import river_endpoint_handler

        app = FastAPI()
        handlers = river_endpoint_handler(router)

        @app.post("/api/river")
        async def start_stream(request: Request):
            return await handlers["post"](request)

        @app.get("/api/river")
        async def resume_stream(request: Request):
            return await handlers["get"](request)
        ```
    """
    caller = create_server_side_caller(router)

    async def post_handler(request: Request) -> Response:
        """Handle POST requests to start a new stream."""
        try:
            # Parse request body
            body = await request.json()
            start_request = StartStreamRequest(**body)

            # Get the stream caller
            try:
                stream_caller = caller.get_stream(start_request.router_stream_key)
            except RiverError as e:
                raise HTTPException(status_code=404, detail=str(e))

            # Start the stream
            items_iter = stream_caller.start(
                input_data=start_request.input,
                adapter_request=request,
            )

            # Return SSE response
            return EventSourceResponse(_sse_generator(items_iter))

        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RiverError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_handler(request: Request) -> Response:
        """Handle GET requests to resume a stream."""
        try:
            # Get resume key from query params
            resume_key = request.query_params.get("resumeKey")
            if not resume_key:
                raise HTTPException(
                    status_code=400, detail="Missing resumeKey parameter"
                )

            # Decode resumption token to get stream key
            from river_core.helpers import decode_resumption_token

            try:
                token = decode_resumption_token(resume_key)
                router_stream_key = token["router_stream_key"]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            # Get the stream caller
            try:
                stream_caller = caller.get_stream(router_stream_key)
            except RiverError as e:
                raise HTTPException(status_code=404, detail=str(e))

            # Resume the stream
            items_iter = stream_caller.resume(resume_key)

            # Return SSE response
            return EventSourceResponse(_sse_generator(items_iter))

        except HTTPException:
            raise
        except RiverError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return {
        "post": post_handler,
        "get": get_handler,
    }
