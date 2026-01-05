# Contributing to fastapi-role

Thank you for your interest in contributing! We welcome bug reports, feature requests, and pull requests.

## getting Started

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    uv sync
    # or
    pip install -e ".[dev]"
    ```
3.  Run tests to ensure everything is working:
    ```bash
    pytest
    ```

## Development Workflow

1.  Create a new branch for your feature/fix: `git checkout -b feature/my-feature`.
2.  Write tests for your changes. We practice Test-Driven Development (TDD).
3.  Implement your changes.
4.  Run tests again to ensure no regressions.
5.  Run linting: `ruff check .`
6.  Submit a Pull Request.

## Code Style

- We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.
- Type hints are mandatory for all function signatures.
- Docstrings should follow Google style.

## Testing

- Uses `pytest` and `pytest-asyncio`.
- All new features must include tests.
- Maintain test coverage (aim for >90%).
