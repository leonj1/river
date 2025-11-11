# Contributing to River Python

Thank you for your interest in contributing to the River Python port!

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/bmdavis419/river
cd river/python
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install packages in development mode:
```bash
# Install core
cd packages/river-core
pip install -e ".[dev]"
cd ../..

# Install Redis provider
cd packages/river-provider-redis
pip install -e ".[dev]"
cd ../..

# Install FastAPI adapter
cd packages/river-adapter-fastapi
pip install -e ".[dev]"
cd ../..
```

## Running Tests

Run all tests:
```bash
pytest
```

Run tests for a specific package:
```bash
pytest packages/river-core/tests/
```

Run with coverage:
```bash
pytest --cov=river_core --cov=river_provider_redis --cov=river_adapter_fastapi
```

## Code Style

We use:
- **ruff** for linting and formatting
- **mypy** for type checking

Format code:
```bash
ruff format .
```

Check types:
```bash
mypy packages/river-core/river_core
```

## Project Structure

```
python/
├── packages/
│   ├── river-core/           # Core library
│   ├── river-provider-redis/ # Redis provider
│   └── river-adapter-fastapi/# FastAPI adapter
├── examples/                  # Example applications
└── tests/                     # Integration tests (if any)
```

## Adding New Features

1. Create a feature branch:
```bash
git checkout -b feature/my-feature
```

2. Make your changes

3. Add tests for your changes

4. Ensure all tests pass:
```bash
pytest
```

5. Format and type check:
```bash
ruff format .
mypy packages/
```

6. Commit and push:
```bash
git add .
git commit -m "feat: add my feature"
git push origin feature/my-feature
```

7. Open a pull request

## Adding a New Provider

To add a new provider (e.g., PostgreSQL, MongoDB):

1. Create a new package:
```bash
mkdir -p packages/river-provider-<name>/river_provider_<name>
```

2. Implement the provider interface from `river_core.types.RiverProvider`

3. Add tests

4. Add documentation

## Adding a New Adapter

To add a new framework adapter (e.g., Django, Flask):

1. Create a new package:
```bash
mkdir -p packages/river-adapter-<name>/river_adapter_<name>
```

2. Implement:
   - Server-side endpoint handlers
   - Client-side streaming client
   - SSE or WebSocket protocol

3. Add tests

4. Add example application

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions or changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

## Questions?

Open an issue or discussion on GitHub!
