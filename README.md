# Steering Docs Wizard

A Python CLI wizard that guides developers through creating standardized steering documents for Kiro development projects.

## Overview

The Steering Docs Wizard collects project configuration preferences and generates appropriate steering files in the `.kiro/steering` directory to guide AI development assistants.

## Features

- Interactive questionnaire for project configuration
- Automatic project discovery and validation
- Generation of standardized steering documents
- Support for various development workflows and preferences
- Professional CLI interface with help and options

## Installation

```bash
# Install with Poetry
poetry install

# Or install from source
pip install -e .
```

## Usage

```bash
# Run the wizard in the current directory
steering-wizard

# Show help
steering-wizard --help

# Specify a different target directory
steering-wizard --target-dir /path/to/project

# Dry run (show what would be created)
steering-wizard --dry-run
```

## Development

This project uses Poetry for dependency management and packaging.

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Format code
poetry run black .

# Lint code
poetry run pylint src/

# Type checking
poetry run mypy src/
```

## Requirements

- Python 3.11+
- Poetry (for development)

## Generated Documents

The wizard creates two main steering documents:

1. **development-guidelines.md** - Contains your project configuration and preferences
2. **llm-guidance.md** - Provides AI assistants with context about your development setup

## License

MIT License