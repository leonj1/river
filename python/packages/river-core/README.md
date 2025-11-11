# River Core

Core library for building durable, resumable streaming applications in Python.

## Installation

```bash
pip install river-core
```

## Features

- **Type-Safe Stream Definitions**: Full type hints with Pydantic validation
- **Builder Pattern**: Fluent API for creating streams
- **Provider System**: Pluggable storage backends for resumability
- **Error Handling**: Graceful error handling with recoverable and fatal errors
- **Framework Agnostic**: Core library works with any Python async framework

## Quick Start

```python
from river_core import create_river_stream, create_river_router, default_river_provider
from pydantic import BaseModel

class ChatInput(BaseModel):
    prompt: str

# Define a stream
async def chat_runner(ctx):
    # Your streaming logic
    await ctx.stream.append_chunk(f"Response to: {ctx.input.prompt}")
    await ctx.stream.close()

chat_stream = (
    create_river_stream()
    .input_schema(ChatInput)
    .provider(default_river_provider())
    .runner(chat_runner)
)

# Create a router
router = create_river_router({
    "chat": chat_stream
})

# Use with server-side caller
from river_core import create_server_side_caller

caller = create_server_side_caller(router)

async for item in caller.chat.start(
    input_data={"prompt": "Hello"},
    adapter_request=None,
):
    if item["type"] == "chunk":
        print(item["chunk"])
```

## Concepts

### Streams

A stream is defined using the builder pattern:

```python
stream = (
    create_river_stream()
    .input_schema(MyInputModel)  # Pydantic model for validation
    .provider(my_provider)        # Storage/resumption provider
    .runner(my_runner_function)   # Async function that generates chunks
)
```

### Providers

Providers handle stream storage and resumption:

- **DefaultProvider**: In-memory, non-resumable (included in core)
- **RedisProvider**: Redis-backed, resumable (separate package)

### Routers

Routers group multiple streams:

```python
router = create_river_router({
    "stream1": stream1,
    "stream2": stream2,
})
```

### Stream Context

Your runner function receives a context object:

```python
async def my_runner(ctx):
    # ctx.input - Validated input data
    # ctx.stream - Stream helper methods
    # ctx.adapter_request - Framework-specific request object
    # ctx.abort_signal - Signal for handling aborts

    await ctx.stream.append_chunk("data")
    await ctx.stream.append_error(error)  # Recoverable
    await ctx.stream.send_fatal_error_and_close(error)  # Fatal
    await ctx.stream.close()  # Success
```

## API Reference

### `create_river_stream()`

Creates a new stream builder.

### `create_river_router(streams)`

Creates a router from a dict of streams.

### `create_server_side_caller(router)`

Creates a server-side caller for executing streams.

### `default_river_provider()`

Returns the default in-memory provider.

## Type Safety

River Core uses generic types to provide end-to-end type safety:

```python
from typing import TypedDict

class MyChunk(TypedDict):
    message: str
    timestamp: float

# Type is preserved throughout the stream
stream = create_river_stream[MyChunk](...)
```

## License

MIT
