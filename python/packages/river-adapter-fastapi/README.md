# River Adapter - FastAPI

FastAPI adapter for River that provides SSE (Server-Sent Events) streaming endpoints.

## Installation

```bash
pip install river-adapter-fastapi
```

## Features

- **SSE Protocol**: Standards-based Server-Sent Events for streaming
- **FastAPI Integration**: Drop-in endpoint handlers
- **Type-Safe Client**: Python client with async/await support
- **Automatic Serialization**: JSON encoding/decoding handled automatically

## Quick Start

### Server Side

```python
from fastapi import FastAPI, Request
from river_core import create_river_stream, create_river_router
from river_provider_redis import redis_provider
from river_adapter_fastapi import river_endpoint_handler
from pydantic import BaseModel

app = FastAPI()

# Define your stream
class ChatInput(BaseModel):
    prompt: str

async def chat_runner(ctx):
    await ctx.stream.append_chunk(f"Response: {ctx.input.prompt}")
    await ctx.stream.close()

chat_stream = (
    create_river_stream()
    .input_schema(ChatInput)
    .provider(redis_provider())
    .runner(chat_runner)
)

router = create_river_router({"chat": chat_stream})

# Create endpoint handlers
handlers = river_endpoint_handler(router)

@app.post("/api/river")
async def start_stream(request: Request):
    return await handlers["post"](request)

@app.get("/api/river")
async def resume_stream(request: Request):
    return await handlers["get"](request)
```

### Client Side

```python
from river_adapter_fastapi import create_river_client
import asyncio

client = create_river_client("http://localhost:8000/api/river")

async def main():
    # Start a stream
    await client.chat.start(
        input_data={"prompt": "Hello"},
        on_chunk=lambda chunk: print(f"Chunk: {chunk}"),
        on_special=lambda special: print(f"Special: {special}"),
        on_complete=lambda: print("Done!"),
        on_error=lambda error: print(f"Error: {error}"),
    )

asyncio.run(main())
```

## API Reference

### Server Side

#### `river_endpoint_handler(router)`

Creates FastAPI endpoint handlers for a River router.

**Parameters:**
- `router`: A River router created with `create_river_router()`

**Returns:**
- Dict with `"post"` and `"get"` handler functions

**POST Endpoint** - Start a new stream:
- Request body: `{"router_stream_key": "stream_name", "input": {...}}`
- Response: SSE stream

**GET Endpoint** - Resume a stream:
- Query param: `?resumeKey=<token>`
- Response: SSE stream from resumption point

### Client Side

#### `create_river_client(endpoint)`

Creates a client for connecting to a River endpoint.

**Parameters:**
- `endpoint`: URL of the River endpoint

**Returns:**
- Client object with stream methods

#### Stream Methods

**`await client.<stream_name>.start(input_data, callbacks...)`**

Start a new stream.

**Parameters:**
- `input_data`: Dict matching the stream's input schema
- `on_chunk`: Callback for regular chunks
- `on_special`: Callback for special chunks (start, end, errors)
- `on_error`: Callback for network/client errors
- `on_complete`: Callback when stream completes

**`await client.<stream_name>.resume(resume_key, callbacks...)`**

Resume an existing stream.

**Parameters:**
- `resume_key`: Resumption token from stream start
- Same callbacks as `start()`

**`client.<stream_name>.abort()`**

Abort the current stream.

## SSE Protocol

The adapter uses Server-Sent Events with JSON payloads:

```
data: {"type": "special", "special": {"type": "stream_start", "stream_run_id": "...", "encoded_resumption_token": "..."}}

data: {"type": "chunk", "chunk": "Hello"}

data: {"type": "chunk", "chunk": "World"}

data: {"type": "special", "special": {"type": "stream_end", "total_chunks": 2, "total_time_ms": 123.45}}
```

## Error Handling

### Server Errors

```python
from river_core.errors import RiverError, RiverErrorType

async def my_runner(ctx):
    try:
        # Your logic
        pass
    except Exception as e:
        # Send recoverable error (stream continues)
        await ctx.stream.append_error(
            RiverError(str(e), RiverErrorType.RUNNER_ERROR)
        )

        # OR send fatal error (stream ends)
        await ctx.stream.send_fatal_error_and_close(
            RiverError(str(e), RiverErrorType.RUNNER_ERROR)
        )
```

### Client Errors

```python
await client.chat.start(
    input_data={"prompt": "Hello"},
    on_error=lambda error: print(f"Error occurred: {error}"),
)
```

## Complete Example

```python
# server.py
from fastapi import FastAPI, Request
from river_core import create_river_stream, create_river_router
from river_provider_redis import redis_provider
from river_adapter_fastapi import river_endpoint_handler
from pydantic import BaseModel
import asyncio

app = FastAPI()

class CountInput(BaseModel):
    max: int

async def count_runner(ctx):
    for i in range(ctx.input.max):
        await ctx.stream.append_chunk(i)
        await asyncio.sleep(0.5)
    await ctx.stream.close()

router = create_river_router({
    "count": (
        create_river_stream()
        .input_schema(CountInput)
        .provider(redis_provider("redis://localhost:6379"))
        .runner(count_runner)
    )
})

handlers = river_endpoint_handler(router)

@app.post("/api/river")
async def start(request: Request):
    return await handlers["post"](request)

@app.get("/api/river")
async def resume(request: Request):
    return await handlers["get"](request)

# Run with: uvicorn server:app
```

```python
# client.py
from river_adapter_fastapi import create_river_client
import asyncio

async def main():
    client = create_river_client("http://localhost:8000/api/river")

    resume_token = None

    def save_token(special):
        nonlocal resume_token
        if special.get("type") == "stream_start":
            resume_token = special.get("encoded_resumption_token")
            print(f"Got resume token: {resume_token}")

    await client.count.start(
        input_data={"max": 10},
        on_chunk=lambda chunk: print(f"Count: {chunk}"),
        on_special=save_token,
        on_complete=lambda: print("Stream complete!"),
    )

asyncio.run(main())
```

## Requirements

- Python 3.10+
- FastAPI
- sse-starlette
- httpx (for client)

## License

MIT
