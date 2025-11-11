# River Provider - Redis

Redis-backed provider for River that enables resumable streams.

## Installation

```bash
pip install river-provider-redis
```

## Features

- **Resumable Streams**: Streams persist to Redis and can be resumed after disconnection
- **Dual-Write Pattern**: Chunks written to both live stream and Redis
- **Production Ready**: Uses Redis Streams for efficient data storage
- **Configurable**: Customizable Redis connection and key prefixes

## Quick Start

```python
from river_core import create_river_stream, create_river_router
from river_provider_redis import redis_provider
from pydantic import BaseModel

class ChatInput(BaseModel):
    prompt: str

# Create Redis provider
provider = redis_provider(
    redis_url="redis://localhost:6379",
    key_prefix="myapp:stream:"
)

# Define a resumable stream
async def chat_runner(ctx):
    for i in range(10):
        await ctx.stream.append_chunk(f"Message {i}")
    await ctx.stream.close()

chat_stream = (
    create_river_stream()
    .input_schema(ChatInput)
    .provider(provider)  # Use Redis provider
    .runner(chat_runner)
)

router = create_river_router({"chat": chat_stream})
```

## How It Works

### Starting a Stream

When you start a stream with the Redis provider:

1. A unique stream run ID is generated
2. A resumption token is created and sent to the client
3. The stream runner executes in the background
4. Each chunk is written to:
   - Redis (for persistence)
   - The live response stream (for real-time delivery)
5. An end marker is written to Redis when complete

### Resuming a Stream

When you resume a stream:

1. The resumption token is decoded
2. Redis is queried for the stream data
3. Chunks are read from Redis and yielded
4. Reading continues until the end marker is reached

## Configuration

### Redis URL

Standard Redis connection URLs are supported:

```python
# Local Redis
provider = redis_provider("redis://localhost:6379")

# Remote Redis with auth
provider = redis_provider("redis://:password@host:6379/0")

# Redis with SSL
provider = redis_provider("rediss://host:6379")
```

### Key Prefix

Customize the Redis key prefix:

```python
provider = redis_provider(
    redis_url="redis://localhost:6379",
    key_prefix="myapp:streams:"
)

# Keys will be: myapp:streams:{storage_id}:{run_id}
```

## Architecture

### Dual-Write Pattern

The Redis provider implements a dual-write pattern:

```
User Runner Function
        ↓
   append_chunk()
        ↓
    ┌───┴───┐
    ↓       ↓
  Redis   Live Stream
    ↓       ↓
  Disk   Client
```

This ensures:
- Live clients get real-time chunks
- Resuming clients get persisted chunks
- No data loss on disconnection

### Redis Streams

The provider uses [Redis Streams](https://redis.io/topics/streams-intro):

- Efficient append-only log structure
- Supports blocking reads with `XREAD`
- Natural fit for stream data
- Built-in message IDs for resumption

## Best Practices

### Stream Cleanup

Redis streams persist indefinitely. Consider implementing cleanup:

```python
import asyncio
from redis import asyncio as aioredis

async def cleanup_old_streams():
    redis = await aioredis.from_url("redis://localhost:6379")

    # Delete streams older than 1 hour
    # Implementation depends on your use case

    await redis.close()
```

### Error Handling

Handle Redis connection errors gracefully:

```python
async def my_runner(ctx):
    try:
        # Your logic
        await ctx.stream.append_chunk("data")
    except Exception as e:
        # Send fatal error if critical
        await ctx.stream.send_fatal_error_and_close(
            RiverError(str(e), RiverErrorType.RUNNER_ERROR)
        )
```

### Performance

For high-throughput streams:

- Use Redis Cluster for horizontal scaling
- Consider shorter TTLs for streams
- Batch chunks when possible
- Monitor Redis memory usage

## Requirements

- Python 3.10+
- Redis 5.0+ (for Redis Streams support)
- `redis-py` library

## License

MIT
