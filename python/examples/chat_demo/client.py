"""
River Chat Demo - Python Client

Demonstrates starting and resuming streams with the River client.
"""

import asyncio
import sys
from pathlib import Path

# Add packages to path (for local development)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "river-core"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "river-adapter-fastapi"))

from river_adapter_fastapi import create_river_client


async def demo_basic_stream():
    """Demonstrate basic stream usage."""
    print("=== Basic Stream Demo ===\n")

    client = create_river_client("http://localhost:8000/api/river")

    resume_token = None
    chunks = []

    def handle_chunk(chunk):
        """Handle incoming chunks."""
        chunks.append(chunk)
        print(chunk, end="", flush=True)

    def handle_special(special):
        """Handle special chunks."""
        nonlocal resume_token
        if special.get("type") == "stream_start":
            resume_token = special.get("encoded_resumption_token")
            print(f"\n[Stream started - Token: {resume_token[:20]}...]\n")
        elif special.get("type") == "stream_end":
            total_chunks = special.get("total_chunks", 0)
            total_time = special.get("total_time_ms", 0)
            print(f"\n\n[Stream ended - {total_chunks} chunks in {total_time:.2f}ms]")

    def handle_complete():
        """Handle stream completion."""
        print("\n[Stream complete]")

    def handle_error(error):
        """Handle errors."""
        print(f"\n[Error: {error}]")

    # Start the stream
    await client.chat.start(
        input_data={"prompt": "Tell me about River"},
        on_chunk=handle_chunk,
        on_special=handle_special,
        on_complete=handle_complete,
        on_error=handle_error,
    )

    return resume_token, chunks


async def demo_resume_stream(resume_token: str):
    """Demonstrate resuming a stream."""
    print("\n\n=== Resume Stream Demo ===\n")
    print(f"Resuming from token: {resume_token[:20]}...\n")

    client = create_river_client("http://localhost:8000/api/river")

    def handle_chunk(chunk):
        print(chunk, end="", flush=True)

    def handle_special(special):
        if special.get("type") == "stream_end":
            print(f"\n\n[Resume complete]")

    def handle_complete():
        print("\n[Stream complete]")

    def handle_error(error):
        print(f"\n[Error: {error}]")

    # Resume the stream
    await client.chat.resume(
        resume_key=resume_token,
        on_chunk=handle_chunk,
        on_special=handle_special,
        on_complete=handle_complete,
        on_error=handle_error,
    )


async def main():
    """Run the demo."""
    print("🚀 River Chat Demo Client\n")
    print("Make sure the server is running on http://localhost:8000\n")

    try:
        # Demo 1: Basic stream
        resume_token, chunks = await demo_basic_stream()

        # Wait a bit
        await asyncio.sleep(2)

        # Demo 2: Resume (will replay all chunks from Redis)
        if resume_token:
            await demo_resume_stream(resume_token)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. Redis is running on localhost:6379")
        print("  2. Server is running on localhost:8000")
        print("  3. Run: python server.py")


if __name__ == "__main__":
    asyncio.run(main())
