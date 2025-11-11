# River - Python Port

A Python port of the River library for creating durable, resumable streams backed by Redis.

## Overview

River is a library for building durable streaming applications. It provides:

- **Resumable Streams**: Streams that can be paused and resumed from where they left off
- **Type Safety**: Full type hints and Pydantic validation
- **Framework Adapters**: FastAPI support (more coming soon)
- **Provider System**: Pluggable storage backends (Redis included)
- **Error Handling**: Graceful error handling with recoverable and fatal errors

## Project Structure

```
python/
├── packages/
│   ├── river-core/          # Core abstractions and types
│   ├── river-provider-redis/  # Redis-backed resumable streams
│   └── river-adapter-fastapi/ # FastAPI framework adapter
└── examples/                  # Example applications
```

## Installation

Each package can be installed independently:

```bash
# Core library
pip install river-core

# Redis provider
pip install river-provider-redis

# FastAPI adapter
pip install river-adapter-fastapi
```

## Quick Start

```python
from river_core import create_river_stream, create_river_router
from river_provider_redis import redis_provider
from pydantic import BaseModel

class ChatInput(BaseModel):
    prompt: str

# Define a stream
chat_stream = (
    create_river_stream()
    .input_schema(ChatInput)
    .provider(redis_provider(redis_url="redis://localhost:6379"))
    .runner(async lambda ctx: {
        # Your streaming logic here
        await ctx.stream.append_chunk(f"Hello {ctx.input.prompt}")
        await ctx.stream.close()
    })
)

# Create a router
router = create_river_router({
    "chat": chat_stream
})
```

## Requirements

- Python 3.10+
- Redis (for resumable streams)

## License

MIT
