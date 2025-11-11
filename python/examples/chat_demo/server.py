"""
River Chat Demo - FastAPI Server

A simple chat server demonstrating River's durable streaming capabilities.
"""

import asyncio
import sys
from pathlib import Path

# Add packages to path (for local development)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "river-core"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "river-provider-redis"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "river-adapter-fastapi"))

from fastapi import FastAPI, Request
from pydantic import BaseModel
from river_core import create_river_stream, create_river_router
from river_provider_redis import redis_provider
from river_adapter_fastapi import river_endpoint_handler

app = FastAPI(title="River Chat Demo")


class ChatInput(BaseModel):
    """Input schema for chat stream."""

    prompt: str


async def chat_runner(ctx):
    """
    Chat stream runner - simulates an AI response.

    This demonstrates:
    - Chunked streaming (word by word)
    - Async delays (simulating AI generation)
    - Proper stream lifecycle
    """
    prompt = ctx.input.prompt

    # Simulate AI response
    response = f"You asked: '{prompt}'. Here's a simulated response: "
    response += "The River library makes it easy to build durable, resumable streams. "
    response += "This demo shows how chunks are streamed word-by-word and persisted to Redis. "
    response += "You can disconnect and resume at any time!"

    # Stream word by word
    words = response.split()
    for i, word in enumerate(words):
        # Add space between words
        chunk = word if i == 0 else f" {word}"
        await ctx.stream.append_chunk(chunk)

        # Simulate processing delay
        await asyncio.sleep(0.2)

    # Close the stream
    await ctx.stream.close()


# Create Redis provider
provider = redis_provider(
    redis_url="redis://localhost:6379",
    key_prefix="chat_demo:",
)

# Define the chat stream
chat_stream = (
    create_river_stream()
    .input_schema(ChatInput)
    .provider(provider)
    .runner(chat_runner)
)

# Create router
router = create_river_router({"chat": chat_stream})

# Create endpoint handlers
handlers = river_endpoint_handler(router)


@app.post("/api/river")
async def start_stream(request: Request):
    """Start a new chat stream."""
    return await handlers["post"](request)


@app.get("/api/river")
async def resume_stream(request: Request):
    """Resume an existing chat stream."""
    return await handlers["get"](request)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "River Chat Demo",
        "endpoints": {
            "start": "POST /api/river",
            "resume": "GET /api/river?resumeKey=<token>",
        },
    }


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting River Chat Demo Server")
    print("📍 Server: http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
    print("🔴 Redis: redis://localhost:6379")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
