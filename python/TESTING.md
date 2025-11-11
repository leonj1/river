# Testing Guide for River Python

This guide explains how to run tests for the River Python port.

## Prerequisites

- Python 3.10+
- Docker and Docker Compose
- pip

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements-dev.txt

# 2. Install River packages in development mode
make install

# 3. Start Redis containers
make start-redis

# 4. Run all tests
make test
```

## Test Types

### Unit Tests

Tests that don't require external dependencies (no Redis needed).

```bash
# Run all unit tests
make test-unit

# Or directly with pytest
pytest packages/river-core/tests/ -v
```

**What they test:**
- Stream builder pattern
- Router functionality
- Server-side callers
- Error handling
- Type validation

### Integration Tests

Tests that require Redis to be running.

```bash
# Run all integration tests
make test-integration

# Or directly with pytest
REDIS_URL=redis://localhost:6380 pytest -m integration -v
```

**What they test:**
- Redis provider start/resume
- Data persistence in Redis
- Error handling with Redis
- Concurrent streams
- FastAPI endpoint integration

## Docker Compose Setup

The project includes a `docker-compose.yml` with two Redis containers:

1. **Main Redis** (port 6379) - For development
2. **Test Redis** (port 6380) - For integration tests

```bash
# Start Redis containers
docker compose up -d

# Or using make
make start-redis

# Check container status
docker ps | grep redis

# Stop containers
docker compose down
# Or
make stop-redis

# View Redis logs
docker compose logs redis
docker compose logs redis-test
```

## Makefile Commands

The `Makefile` provides convenient commands:

```bash
make help              # Show all available commands
make install           # Install all packages in dev mode
make test              # Run all tests (unit + integration)
make test-unit         # Run only unit tests
make test-integration  # Run integration tests (starts Redis)
make start-redis       # Start Redis with Docker Compose
make stop-redis        # Stop Redis containers
make clean             # Clean Python cache and build artifacts
```

## Running Specific Tests

### Run tests for a specific package

```bash
# Core tests only
pytest packages/river-core/tests/ -v

# Redis provider tests only
REDIS_URL=redis://localhost:6380 pytest packages/river-provider-redis/tests/ -v -m integration

# FastAPI adapter tests only
REDIS_URL=redis://localhost:6380 pytest packages/river-adapter-fastapi/tests/ -v -m integration
```

### Run a specific test file

```bash
pytest packages/river-core/tests/test_stream.py -v
```

### Run a specific test function

```bash
pytest packages/river-core/tests/test_stream.py::test_create_stream -v
```

### Run with coverage

```bash
pytest --cov=river_core --cov=river_provider_redis --cov=river_adapter_fastapi --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

## Test Markers

Tests are marked with pytest markers:

- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.integration` - Integration tests requiring Redis

```bash
# Run only integration tests
pytest -m integration

# Run only unit tests (exclude integration)
pytest -m "not integration"
```

## Environment Variables

Configure tests with environment variables:

```bash
# Redis URL for integration tests (default: redis://localhost:6380)
export REDIS_URL=redis://your-redis-host:6379

# Run tests
pytest -m integration
```

Or set in `.env.test` file:

```bash
REDIS_URL=redis://localhost:6380
```

## Debugging Tests

### Run with verbose output

```bash
pytest -v -s
```

### Run with print statements visible

```bash
pytest -s  # Shows print() output
```

### Stop on first failure

```bash
pytest -x
```

### Run last failed tests

```bash
pytest --lf
```

### Drop into debugger on failure

```bash
pytest --pdb
```

## Writing New Tests

### Unit Test Template

```python
# packages/river-core/tests/test_myfeature.py

import pytest
from pydantic import BaseModel
from river_core import create_river_stream

class MyInput(BaseModel):
    value: int

@pytest.mark.asyncio
async def test_my_feature():
    """Test description."""
    # Test implementation
    assert True
```

### Integration Test Template

```python
# packages/river-provider-redis/tests/test_myfeature.py

import pytest
from pydantic import BaseModel
from river_provider_redis import redis_provider

class MyInput(BaseModel):
    value: int

@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_feature(redis_url, clean_redis):
    """Test description."""
    provider = redis_provider(redis_url=redis_url)
    # Test implementation
    assert True
```

### Test Fixtures

Common fixtures available:

- `redis_url` - Redis connection URL
- `redis_client` - Async Redis client
- `clean_redis` - Cleans Redis before/after test
- `create_test_app` - Factory for FastAPI test apps

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6380:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          make install

      - name: Run tests
        env:
          REDIS_URL: redis://localhost:6380
        run: |
          make test
```

## Troubleshooting

### Redis connection errors

```
Error: Connection refused to redis://localhost:6380
```

**Solution:** Ensure Redis is running:
```bash
make start-redis
docker ps | grep redis
```

### Module not found errors

```
ModuleNotFoundError: No module named 'river_core'
```

**Solution:** Install packages in development mode:
```bash
make install
```

### Tests hang or timeout

**Solution:** Check Redis is responding:
```bash
docker exec river-redis-test redis-cli ping
# Should return: PONG
```

### Permission errors with Docker

**Solution:** Ensure Docker daemon is running and you have permissions:
```bash
sudo usermod -aG docker $USER
# Then log out and back in
```

## Test Coverage Goals

Target coverage levels:
- **Core library**: >90%
- **Redis provider**: >80%
- **FastAPI adapter**: >75%

Current status can be checked with:
```bash
pytest --cov=river_core --cov=river_provider_redis --cov=river_adapter_fastapi --cov-report=term-missing
```

## Performance Testing

For load testing:

```python
import asyncio
import time

async def load_test():
    tasks = []
    for i in range(100):
        tasks.append(run_stream(i))

    start = time.time()
    await asyncio.gather(*tasks)
    elapsed = time.time() - start

    print(f"Processed 100 streams in {elapsed:.2f}s")
```

## Best Practices

1. **Always clean Redis between tests** - Use the `clean_redis` fixture
2. **Use descriptive test names** - `test_redis_provider_handles_large_streams`
3. **Test both success and error cases** - Happy path and edge cases
4. **Keep tests fast** - Unit tests < 0.1s, integration tests < 1s
5. **Use fixtures for common setup** - Avoid duplication
6. **Mark tests appropriately** - Use `@pytest.mark.integration`
7. **Test async code properly** - Use `@pytest.mark.asyncio`

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Redis testing guide](https://redis.io/docs/manual/testing/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)

## Support

For issues with tests:
1. Check [TEST_RESULTS.md](TEST_RESULTS.md) for known issues
2. Review [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
3. Open an issue on GitHub with test output
