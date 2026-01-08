# Testing Guide

This document describes the testing setup and procedures for the steering-wizard project.

## Testing Framework

The project uses the following testing tools:

- **pytest**: Main testing framework
- **Hypothesis**: Property-based testing library
- **pytest-cov**: Coverage reporting
- **Docker**: Multi-version Python testing

## Running Tests

### Local Testing

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run code quality checks
make quality
```

### Docker Testing

Test across multiple Python versions using Docker:

```bash
# Build all Docker images
make docker-build

# Test with Python 3.11
make docker-test-py311

# Test with Python 3.12
make docker-test-py312

# Test with Python 3.13
make docker-test-py313

# Run tests across all Python versions
make docker-test
```

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest configuration and fixtures
├── test_project_finder.py   # Tests for project discovery
├── test_questionnaire.py    # Tests for interactive prompts
├── test_document_generator.py # Tests for document generation
└── test_integration.py      # End-to-end integration tests
```

## Shared Fixtures

The `conftest.py` file provides common fixtures:

- `temp_dir`: Creates a temporary directory for testing
- `mock_kiro_project`: Sets up a mock Kiro project structure

## Property-Based Testing

The project uses Hypothesis for property-based testing to validate universal properties across diverse inputs. Property tests are configured to run a minimum of 100 iterations per test.

## Code Quality

The project enforces code quality through:

- **Black**: Code formatting (88 character line length)
- **Pylint**: Linting with Google Python style guide
- **mypy**: Static type checking

Run all quality checks with:

```bash
make quality
```

## Supported Python Versions

The project supports Python 3.11+ and is tested across:

- Python 3.11
- Python 3.12
- Python 3.13

## CI/CD Integration

The Docker setup enables easy integration with CI/CD systems. The multi-stage Dockerfile allows testing across all supported Python versions in parallel.