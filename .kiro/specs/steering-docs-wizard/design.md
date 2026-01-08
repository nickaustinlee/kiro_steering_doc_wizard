# Design Document: Steering Docs Wizard

## Overview

The Steering Docs Wizard is a Python CLI application that guides developers through creating standardized steering documents for Kiro projects. The application uses modern Python packaging standards with `pyproject.toml`, leverages Typer for CLI functionality, and follows Google's Python style guide with Black formatting.

The wizard operates as an interactive questionnaire that collects project preferences and generates two key steering documents: `development-guidelines.md` (user configuration) and `llm-guidance.md` (AI assistant guidance).

## Architecture

The application follows a modular architecture with clear separation of concerns:

```
steering-docs-wizard/
├── src/
│   └── steering_wizard/
│       ├── __init__.py
│       ├── main.py              # CLI entry point and command definitions
│       ├── core/
│       │   ├── __init__.py
│       │   ├── project_finder.py    # Project discovery and validation
│       │   ├── questionnaire.py     # Interactive user prompts
│       │   └── document_generator.py # Steering document creation
│       └── models/
│           ├── __init__.py
│           └── config.py        # Configuration data structures
├── tests/
│   ├── __init__.py
│   ├── test_project_finder.py
│   ├── test_questionnaire.py
│   ├── test_document_generator.py
│   └── test_integration.py
├── pyproject.toml
├── README.md
└── Dockerfile
```

## Components and Interfaces

### CLI Interface (main.py)
Built with [Typer](https://typer.tiangolo.com/) for modern Python CLI development with type hints and automatic help generation. Provides the main entry point and command-line argument parsing.

**Key Features:**
- Type-safe command definitions using Python type hints
- Automatic help generation and validation
- Support for `--help`, `--version`, `--target-dir`, and `--dry-run` options
- Colored output for better user experience

### Project Finder (project_finder.py)
Handles discovery and validation of Kiro project directories.

**Interface:**
```python
class ProjectFinder:
    def find_kiro_project(self, start_path: Path = None) -> Optional[Path]
    def validate_project_structure(self, project_path: Path) -> bool
    def ensure_steering_directory(self, project_path: Path) -> Path
```

### Questionnaire Engine (questionnaire.py)
Manages interactive user prompts and input validation.

**Interface:**
```python
class QuestionnaireEngine:
    def collect_configuration(self) -> ProjectConfiguration
    def prompt_testing_preferences(self) -> TestingConfig
    def prompt_github_info(self) -> GitHubConfig
    def prompt_formatting_rules(self) -> FormattingConfig
```

### Document Generator (document_generator.py)
Creates steering documents from collected configuration data.

**Interface:**
```python
class DocumentGenerator:
    def generate_development_guidelines(self, config: ProjectConfiguration, output_path: Path) -> None
    def generate_llm_guidance(self, config: ProjectConfiguration, output_path: Path) -> None
    def check_existing_files(self, output_dir: Path) -> List[Path]
```

### Configuration Models (models/config.py)
Type-safe data structures using Python dataclasses for configuration management.

**Data Models:**
```python
@dataclass
class TestingConfig:
    local_testing: str
    use_docker: bool
    use_pytest: bool

@dataclass
class GitHubConfig:
    repository_url: Optional[str]
    use_github_actions: bool

@dataclass
class FormattingConfig:
    use_black: bool
    use_google_style: bool
    custom_rules: Optional[str]

@dataclass
class VirtualizationConfig:
    preference: str  # "venv", "poetry", "poetry_with_venv_docs"
    include_venv_docs: bool

@dataclass
class ProjectConfiguration:
    testing: TestingConfig
    github: GitHubConfig
    formatting: FormattingConfig
    virtualization: VirtualizationConfig
    project_path: Path
    creation_date: str
```

## Data Models

### Input Validation
- **GitHub URLs**: Regex validation for proper GitHub repository format
- **Directory Paths**: Path existence and permission validation
- **User Choices**: Enumerated options with fallback to custom input

### File Generation Templates
- **Markdown Templates**: Jinja2-style templates for consistent document structure
- **Date Formatting**: ISO 8601 format (YYYY-MM-DD) for timestamps
- **Content Preservation**: Structured sections that maintain user input fidelity

## Error Handling

### File System Errors
- **Permission Denied**: Clear error messages with suggested solutions (chmod, sudo)
- **Directory Creation**: Graceful handling of existing directories and permission issues
- **Partial File Creation**: Cleanup of incomplete files on interruption

### Input Validation Errors
- **Invalid URLs**: Re-prompt with format examples and validation feedback
- **Invalid Paths**: Directory existence checks with helpful error messages
- **Interrupted Sessions**: Signal handling for clean exit and file cleanup

### Recovery Mechanisms
- **Retry Logic**: Up to 3 attempts for correctable input errors
- **Graceful Degradation**: Continue with default values when optional inputs fail
- **User Confirmation**: Explicit confirmation before overwriting existing files

## Testing Strategy

The testing approach combines traditional unit testing with property-based testing using pytest and Hypothesis to ensure robust validation across diverse inputs.

### Unit Testing with pytest
- **Component Testing**: Individual module testing with mocked dependencies
- **Integration Testing**: End-to-end workflow testing with temporary directories
- **Edge Case Testing**: Boundary conditions, empty inputs, and error scenarios
- **CLI Testing**: Command-line interface testing using Typer's testing utilities

### Property-Based Testing with Hypothesis
Property-based tests validate universal properties that should hold for all valid inputs, using Hypothesis to generate diverse test cases automatically.

**Testing Configuration:**
- Minimum 100 iterations per property test
- Each property test references its corresponding design property
- Tag format: **Feature: steering-docs-wizard, Property {number}: {property_text}**

### Docker Testing Environment
Multi-version Python testing (3.11-3.14) using Docker containers to ensure compatibility across Python versions.

**Docker Configuration:**
```dockerfile
FROM python:3.11-slim
FROM python:3.12-slim  
FROM python:3.13-slim
FROM python:3.14-slim
```

### Code Quality Tools
- **Black**: Automatic code formatting
- **Pylint**: Google Python style guide enforcement (ignoring formatting rules handled by Black)
- **Type Checking**: mypy for static type validation
- **Coverage**: pytest-cov for test coverage reporting

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the requirements analysis, the following properties must hold for all valid executions of the steering docs wizard:

### Property 1: Project Discovery Consistency
*For any* directory structure, the project finder should consistently locate `.kiro` directories by searching the current directory first, then parent directories up to the filesystem root, and should validate that found directories can support steering document creation.
**Validates: Requirements 1.1, 1.2, 1.4**

### Property 2: Input Validation and Recovery
*For any* user input that fails validation (invalid URLs, missing required fields), the system should re-prompt with specific validation feedback and allow the user to correct their input without losing previous valid responses.
**Validates: Requirements 2.2, 2.6, 5.2**

### Property 3: Content Preservation Round-Trip
*For any* valid user configuration input, the generated steering documents should contain all provided user data in a structured format that preserves the original input values exactly as entered.
**Validates: Requirements 3.2, 3.3, 4.4**

### Property 4: File Generation Completeness
*For any* valid project directory and user configuration, the wizard should create both `development-guidelines.md` and `llm-guidance.md` files with all required sections (date, user preferences, standard guidance) in valid markdown format.
**Validates: Requirements 3.1, 3.5, 4.1, 4.2, 4.3**

### Property 5: CLI Options Functionality
*For any* valid command-line options (`--target-dir`, `--dry-run`), the wizard should modify its behavior appropriately without affecting the core functionality or output quality.
**Validates: Requirements 6.3, 6.4**

### Property 6: Output Formatting Consistency
*For any* type of output message (prompts, errors, success messages, file summaries), the formatting and presentation should follow consistent patterns and include appropriate visual indicators.
**Validates: Requirements 1.5, 3.5, 5.4, 6.5**

### Property 7: Custom Input Handling
*For any* custom formatting rules or free-form text input provided by the user, the system should accept and preserve the input without modification while incorporating it appropriately into the generated documents.
**Validates: Requirements 2.5**