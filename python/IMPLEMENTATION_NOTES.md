# River Python Port - Implementation Notes

This document describes the Python port of the River library, created from the original TypeScript implementation.

## Overview

River Python is a faithful port of the River library for building durable, resumable streams. The port maintains the same architecture and design patterns while adapting to Python's idioms and type system.

## Architecture

### Core Components

#### 1. **river-core** - Core Abstractions

**Key Files:**
- `types.py` - Core types and protocols
- `stream.py` - Stream builder implementation
- `router.py` - Router for grouping streams
- `provider.py` - Default in-memory provider
- `callers.py` - Server-side caller implementation
- `errors.py` - Error types and handling
- `helpers.py` - Utility functions

**Type System:**
- Uses Python generics (`Generic[T]`) for type safety
- Pydantic for input validation (replaces Zod)
- Protocol classes for provider interface
- TypedDict for structured data

**Builder Pattern:**
```python
stream = (
    create_river_stream()
    .input_schema(MyInputModel)
    .provider(my_provider)
    .runner(my_runner)
)
```

#### 2. **river-provider-redis** - Redis Resumable Streams

**Key Files:**
- `provider.py` - Redis-backed provider implementation

**Features:**
- Dual-write pattern (live stream + Redis persistence)
- Uses Redis Streams (`XADD`, `XREAD`)
- Blocking reads for efficiency
- Resumption from any point

**Differences from TypeScript:**
- Uses `redis-py` async client instead of `ioredis`
- AsyncIterator instead of ReadableStream
- Python async/await patterns

#### 3. **river-adapter-fastapi** - FastAPI Integration

**Key Files:**
- `server.py` - Endpoint handlers for FastAPI
- `client.py` - Python HTTP client

**Features:**
- SSE (Server-Sent Events) protocol
- POST for starting streams
- GET for resuming streams
- Callback-based client API

**Differences from TypeScript:**
- Uses FastAPI instead of SvelteKit
- `sse-starlette` for SSE responses
- `httpx` for async HTTP client
- Callback pattern instead of reactive state

## TypeScript to Python Mappings

### Type System

| TypeScript | Python |
|------------|--------|
| `interface` | `Protocol` or `TypedDict` |
| Zod schemas | Pydantic models |
| `type T = ...` | `TypeVar` or `Union` |
| Generics `<T>` | `Generic[T]` |
| `neverthrow` Result | Custom Result (or direct exceptions) |

### Async Patterns

| TypeScript | Python |
|------------|--------|
| `ReadableStream` | `AsyncIterator`/`AsyncGenerator` |
| `async function*` | `async def` with `yield` |
| `Promise<T>` | `Awaitable[T]` |
| `AbortController` | Custom `AbortSignal` class |

### Stream Processing

| TypeScript | Python |
|------------|--------|
| `for await (const item of stream)` | `async for item in stream:` |
| `stream.getReader()` | `aiter(stream)` |
| Web Streams API | asyncio queues |

## Key Design Decisions

### 1. **AsyncIterator over ReadableStream**

Python's AsyncIterator is the natural equivalent to ReadableStream:
- Native language support
- Works with `async for`
- Composable with asyncio

### 2. **Pydantic for Validation**

Pydantic replaces Zod:
- Industry standard in Python
- Great type inference
- FastAPI integration
- JSON schema generation

### 3. **Protocol Classes for Providers**

Using `Protocol` instead of abstract base classes:
- Structural typing (duck typing with types)
- More Pythonic
- Better with type checkers

### 4. **Direct Exceptions vs Result Types**

Unlike the TypeScript version which uses `neverthrow`, the Python port uses direct exceptions:
- More Pythonic
- FastAPI has built-in exception handling
- Easier error propagation in async code

### 5. **Callback-Based Client**

The client uses callbacks instead of reactive state:
- Simpler API
- No dependency on reactive frameworks
- Works with any async Python code

## Testing Strategy

### Unit Tests

Located in `packages/*/tests/`:
- Stream creation and execution
- Router functionality
- Caller operations
- Error handling
- Serialization/deserialization

### Integration Tests

The example application serves as an integration test:
- FastAPI server
- Redis provider
- Client-server communication
- Resume functionality

## Example Application

`examples/chat_demo/` demonstrates:
- FastAPI server setup
- Redis-backed streams
- Python client usage
- Stream resumption

## Differences from TypeScript Version

### What's the Same

- Core architecture and concepts
- Builder pattern API
- Provider abstraction
- Dual-write pattern
- SSE protocol
- Resumption tokens
- Error handling strategy

### What's Different

- **Language idioms**: Pythonic patterns vs JavaScript patterns
- **Type system**: Python type hints vs TypeScript
- **Validation**: Pydantic vs Zod
- **Streams**: AsyncIterator vs ReadableStream
- **Error handling**: Exceptions vs Result types
- **Client API**: Callbacks vs reactive state
- **Testing**: pytest vs vitest/jest

### What's Missing (Future Work)

- Client-side caller in core (currently only in adapter)
- More providers (PostgreSQL, MongoDB, etc.)
- More adapters (Django, Flask, etc.)
- WebSocket support
- Advanced error recovery
- Metrics and observability
- Stream cleanup utilities

## Performance Considerations

### Async/Await

Python's async/await is mature and performant:
- Native OS integration via asyncio
- Efficient event loop
- Good for I/O-bound workloads

### Redis Operations

- Uses pipelining where appropriate
- Blocking reads reduce polling
- Connection pooling via redis-py

### Memory Management

- Streams use queues with backpressure
- Chunks are not buffered in memory
- Redis handles persistence

## Future Enhancements

### Near Term

1. **More comprehensive tests**
   - Integration tests
   - Performance tests
   - Load tests

2. **Additional providers**
   - PostgreSQL (using LISTEN/NOTIFY)
   - MongoDB (change streams)
   - In-memory with disk spillover

3. **Additional adapters**
   - Django Channels
   - Flask with SSE
   - Starlette

### Long Term

1. **Advanced features**
   - Stream branching
   - Stream merging
   - Backpressure control
   - Rate limiting

2. **Observability**
   - OpenTelemetry integration
   - Metrics collection
   - Logging standardization

3. **Production features**
   - Health checks
   - Graceful shutdown
   - Circuit breakers
   - Retry policies

## Compatibility

- **Python**: 3.10+
- **Redis**: 5.0+ (for Streams support)
- **FastAPI**: 0.100+

## Package Structure

```
python/
├── packages/
│   ├── river-core/              # Core library
│   │   ├── river_core/
│   │   │   ├── __init__.py
│   │   │   ├── types.py
│   │   │   ├── stream.py
│   │   │   ├── router.py
│   │   │   ├── provider.py
│   │   │   ├── callers.py
│   │   │   ├── errors.py
│   │   │   └── helpers.py
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   ├── river-provider-redis/    # Redis provider
│   │   ├── river_provider_redis/
│   │   │   ├── __init__.py
│   │   │   └── provider.py
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   └── river-adapter-fastapi/   # FastAPI adapter
│       ├── river_adapter_fastapi/
│       │   ├── __init__.py
│       │   ├── server.py
│       │   └── client.py
│       ├── tests/
│       ├── pyproject.toml
│       └── README.md
│
├── examples/
│   └── chat_demo/              # Example application
│       ├── server.py
│       ├── client.py
│       ├── requirements.txt
│       └── README.md
│
├── README.md
├── CONTRIBUTING.md
├── IMPLEMENTATION_NOTES.md
├── pytest.ini
└── .gitignore
```

## Credits

This Python port was created by analyzing the TypeScript implementation in the main River repository. The core concepts, architecture, and API design are faithful to the original while adapting to Python's ecosystem and idioms.

Original River (TypeScript): https://github.com/bmdavis419/river

## License

MIT - Same as the original River library
