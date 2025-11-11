# TypeScript vs Python - Side-by-Side Comparison

This document shows side-by-side comparisons of the River library implementation in TypeScript and Python.

## Stream Creation

### TypeScript
```typescript
import { createRiverStream } from '@davis7dotsh/river-core';
import { z } from 'zod';

const chatStream = createRiverStream<string>()
  .input(z.object({
    prompt: z.string()
  }))
  .provider(redisProvider({
    redisUrl: 'redis://localhost:6379'
  }))
  .runner(async ({ input, stream }) => {
    stream.appendChunk('Hello');
    await stream.close();
  });
```

### Python
```python
from river_core import create_river_stream
from river_provider_redis import redis_provider
from pydantic import BaseModel

class ChatInput(BaseModel):
    prompt: str

chat_stream = (
    create_river_stream()
    .input_schema(ChatInput)
    .provider(redis_provider(
        redis_url='redis://localhost:6379'
    ))
    .runner(async lambda ctx: {
        await ctx.stream.append_chunk('Hello')
        await ctx.stream.close()
    })
)
```

## Router and Server Setup

### TypeScript (SvelteKit)
```typescript
import { createRiverRouter } from '@davis7dotsh/river-core';
import { riverEndpointHandler } from '@davis7dotsh/river-adapter-sveltekit';

const router = createRiverRouter({
  chat: chatStream,
});

export type AppRouter = typeof router;

// In +server.ts
export const { GET, POST } = riverEndpointHandler(router);
```

### Python (FastAPI)
```python
from river_core import create_river_router
from river_adapter_fastapi import river_endpoint_handler
from fastapi import FastAPI, Request

router = create_river_router({
    "chat": chat_stream,
})

AppRouter = type(router)  # Type alias

app = FastAPI()
handlers = river_endpoint_handler(router)

@app.post("/api/river")
async def start(request: Request):
    return await handlers["post"](request)

@app.get("/api/river")
async def resume(request: Request):
    return await handlers["get"](request)
```

## Client Usage

### TypeScript (Svelte)
```typescript
import { createRiverClient } from '@davis7dotsh/river-adapter-sveltekit';
import type { AppRouter } from './server';

const client = createRiverClient<AppRouter>('/api/river');

const { start, resume, abort } = client.chat({
  onChunk: (chunk) => console.log(chunk),
  onSuccess: () => console.log('Done'),
  onError: (error) => console.error(error),
});

start({ prompt: "Hello" });
```

### Python
```python
from river_adapter_fastapi import create_river_client

client = create_river_client('http://localhost:8000/api/river')

await client.chat.start(
    input_data={"prompt": "Hello"},
    on_chunk=lambda chunk: print(chunk),
    on_complete=lambda: print('Done'),
    on_error=lambda error: print(error),
)
```

## Type System

### TypeScript
```typescript
// Zod schema
const inputSchema = z.object({
  message: z.string(),
  count: z.number().optional(),
});

type Input = z.infer<typeof inputSchema>;

// Generic stream type
type MyStream = RiverStream<
  typeof inputSchema,
  string,
  true,
  RequestEvent
>;
```

### Python
```python
# Pydantic model
from pydantic import BaseModel
from typing import Optional

class Input(BaseModel):
    message: str
    count: Optional[int] = None

# Generic stream type
from typing import TypeVar
from river_core.types import RiverStream

InputT = TypeVar('InputT', bound=BaseModel)
ChunkT = TypeVar('ChunkT')

MyStream = RiverStream[Input, str, Request]
```

## Error Handling

### TypeScript
```typescript
import { RiverError, RiverErrorType } from '@davis7dotsh/river-core';
import { err, ok, Result } from 'neverthrow';

.runner(async ({ stream }) => {
  const result = await somethingThatMightFail();

  if (result.isErr()) {
    await stream.appendError(new RiverError(
      'Something failed',
      RiverErrorType.RUNNER_ERROR
    ));
    return;
  }

  // Or fatal error
  await stream.sendFatalErrorAndClose(new RiverError(...));
});
```

### Python
```python
from river_core.errors import RiverError, RiverErrorType

async def runner(ctx):
    try:
        result = await something_that_might_fail()
    except Exception as e:
        await ctx.stream.append_error(RiverError(
            'Something failed',
            RiverErrorType.RUNNER_ERROR
        ))
        return

    # Or fatal error
    await ctx.stream.send_fatal_error_and_close(
        RiverError(...)
    )
```

## Provider Implementation

### TypeScript (Redis)
```typescript
export const redisProvider = <ChunkType>(config: {
  redisUrl: string;
}): RiverProvider<ChunkType, true> => ({
  providerId: 'redis',
  isResumable: true,

  async startStream({ stream, runner, context }) {
    const redis = new Redis(config.redisUrl);

    // Dual write to Redis and stream
    for await (const chunk of runner(context)) {
      await redis.xadd(streamKey, '*', 'data', JSON.stringify(chunk));
      stream.appendChunk(chunk);
    }
  },

  async resumeStream({ token }) {
    // Read from Redis
  }
});
```

### Python (Redis)
```python
from redis import asyncio as aioredis

class RedisRiverProvider:
    provider_id = 'redis'
    is_resumable = True

    def __init__(self, redis_url: str):
        self._redis_url = redis_url

    async def start_stream(self, stream_storage_id, runner, context):
        redis = await aioredis.from_url(self._redis_url)

        # Dual write to Redis and stream
        async def run():
            await runner(context)

        asyncio.create_task(run())

        # Yield chunks from queue
        async for item in queue:
            await redis.xadd(stream_key, {'data': json.dumps(item)})
            yield item

    async def resume_stream(self, resumption_token):
        # Read from Redis
        pass

def redis_provider(redis_url: str):
    return RedisRiverProvider(redis_url)
```

## Streaming Primitives

### TypeScript
```typescript
// ReadableStream
const stream = new ReadableStream({
  async start(controller) {
    controller.enqueue(chunk);
    controller.close();
  }
});

// Async iteration
for await (const chunk of stream) {
  console.log(chunk);
}
```

### Python
```python
# AsyncIterator
async def stream_generator():
    yield chunk
    # Auto closes when function ends

# Async iteration
async for chunk in stream_generator():
    print(chunk)
```

## Testing

### TypeScript (Vitest)
```typescript
import { describe, it, expect } from 'vitest';

describe('Stream', () => {
  it('should create stream', async () => {
    const stream = createRiverStream()
      .input(z.object({ test: z.string() }))
      .provider(defaultProvider())
      .runner(async ({ stream }) => {
        await stream.close();
      });

    expect(stream).toBeDefined();
  });
});
```

### Python (pytest)
```python
import pytest

@pytest.mark.asyncio
async def test_create_stream():
    stream = (
        create_river_stream()
        .input_schema(TestInput)
        .provider(default_river_provider())
        .runner(async lambda ctx: await ctx.stream.close())
    )

    assert stream is not None
```

## Package Structure

### TypeScript
```
packages/
├── core/
│   └── src/
│       ├── index.ts
│       ├── stream.ts
│       ├── router.ts
│       └── types.ts
├── provider-redis/
│   └── src/
│       └── redisProvider.ts
└── adapter-sveltekit/
    └── src/
        ├── lib/server.ts
        └── lib/client.svelte.ts
```

### Python
```
packages/
├── river-core/
│   └── river_core/
│       ├── __init__.py
│       ├── stream.py
│       ├── router.py
│       └── types.py
├── river-provider-redis/
│   └── river_provider_redis/
│       └── provider.py
└── river-adapter-fastapi/
    └── river_adapter_fastapi/
        ├── server.py
        └── client.py
```

## Key Differences Summary

| Aspect | TypeScript | Python |
|--------|-----------|--------|
| **Validation** | Zod schemas | Pydantic models |
| **Streams** | ReadableStream | AsyncIterator/AsyncGenerator |
| **Type System** | TypeScript generics | Python Generic[T], Protocol |
| **Errors** | neverthrow Result | Direct exceptions |
| **Async** | Promise, async/await | Coroutine, async/await |
| **Framework** | SvelteKit, TanStack | FastAPI |
| **Testing** | Vitest | pytest |
| **Package Manager** | bun, npm | pip |
| **Build Tool** | tsdown, vite | hatch, setuptools |

## Similarities

Both implementations share:
- Builder pattern for streams
- Provider abstraction
- Router pattern
- Dual-write for Redis
- SSE protocol
- Resumption token design
- Special chunks (start, end, error)
- Server-side callers
- Type safety
- Framework adapters

## Performance Characteristics

### TypeScript
- V8/Bun JavaScript engine
- Single-threaded event loop
- Fast startup
- Good for I/O-bound tasks
- Excellent for frontend integration

### Python
- CPython interpreter (or PyPy)
- asyncio event loop
- Slower startup
- Good for I/O-bound tasks
- Excellent for backend integration
- Better for CPU-intensive tasks (with multiprocessing)

## When to Use Which

### Use TypeScript Version When:
- Building full-stack applications with Svelte/React
- Need seamless frontend/backend integration
- Team expertise in TypeScript
- Using Bun for edge deployment
- Need React Server Components

### Use Python Version When:
- Building backend APIs with FastAPI
- Team expertise in Python
- Integrating with Python ML/AI libraries
- Need data processing capabilities
- Existing Python infrastructure

Both versions are production-ready and offer the same core capabilities!
