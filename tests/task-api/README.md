# Task API Tests

This directory contains automated tests for the Task API.

## Test Structure

- `conftest.py` - Shared fixtures (database, Redis mock, test client)
- `test_health.py` - Health check endpoint tests
- `test_tasks.py` - Task CRUD endpoint tests
- `test_crud.py` - Data layer and caching logic tests

## Running Tests

From the project root directory:

```bash
# Install dependencies
pip3 install -r task-api/requirements.txt -r requirements-test.txt

# Run all tests
python3 -m pytest

# Run with verbose output
python3 -m pytest -v

# Run specific test file
python3 -m pytest tests/task-api/test_tasks.py

# Run with coverage (requires pytest-cov)
python3 -m pytest --cov=task-api/app
```

## Test Design

### Data Isolation
- Uses SQLite in-memory database instead of MySQL
- Each test gets a fresh database schema
- No data leaks between tests

### Redis Mocking
- Uses `fakeredis` to simulate Redis Cluster
- Tests cache hit/miss scenarios without real Redis

### Extensibility
- Add new test files following the `test_*.py` naming convention
- Reuse fixtures from `conftest.py`
- Use `@pytest.mark.asyncio` for async tests

## Directory Structure

```
sre-learning/
├── task-api/              # Application code (packaged in Docker)
│   └── app/
├── tests/
│   └── task-api/          # Test code (NOT packaged in Docker)
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_tasks.py
│       └── test_crud.py
├── pyproject.toml         # pytest configuration
└── requirements-test.txt  # Test dependencies
```

## Dependencies

Test dependencies are in `requirements-test.txt` at the project root:

```
pytest>=7.0
pytest-asyncio>=0.21
httpx>=0.24
fakeredis>=2.0
aiosqlite>=0.19
```
