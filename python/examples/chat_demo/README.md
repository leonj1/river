# River Chat Demo

A demo application showing River's durable streaming with FastAPI and Redis.

## Features

- FastAPI backend with River streaming
- Redis-backed resumable streams
- Simple chat interface
- Demonstrates stream start and resume

## Setup

1. Install dependencies:

```bash
cd python/examples/chat_demo
pip install -r requirements.txt
```

2. Start Redis (using Docker):

```bash
docker run -d -p 6379:6379 redis:latest
```

Or use your own Redis instance.

3. Run the server:

```bash
python server.py
```

4. In another terminal, run the client:

```bash
python client.py
```

## Project Structure

```
chat_demo/
├── server.py          # FastAPI server with River endpoints
├── client.py          # Python client example
├── requirements.txt   # Dependencies
└── README.md         # This file
```

## How It Works

### Server

The server defines a simple chat stream that simulates an AI response:

1. Receives a prompt via POST
2. Generates chunks word-by-word
3. Stores chunks in Redis
4. Returns a resumption token
5. Supports resuming from any point

### Client

The client demonstrates two modes:

1. **Normal Mode**: Start a stream and receive all chunks
2. **Resume Mode**: Disconnect partway through and resume later

## Testing Resume Functionality

Run the client with different scenarios:

```bash
# Normal operation
python client.py

# Simulate disconnection (modify client.py to abort early)
# Then resume with the token
```

## API Endpoints

### POST /api/river

Start a new stream.

**Request:**
```json
{
  "router_stream_key": "chat",
  "input": {
    "prompt": "Tell me a story"
  }
}
```

**Response:** SSE stream

### GET /api/river?resumeKey=<token>

Resume an existing stream.

**Response:** SSE stream from resumption point

## License

MIT
