# Implementation Plan: Steering Docs Wizard

## Overview

This implementation plan breaks down the steering docs wizard into discrete coding tasks that build incrementally toward a complete Python CLI application. Each task focuses on implementing specific components while maintaining integration with previously completed work.

## Tasks

- [x] 1. Set up project structure and configuration with Poetry
  - Initialize project with `poetry init` and configure `pyproject.toml`
  - Set up `src/steering_wizard/` package structure with `__init__.py` files
  - Add dependencies: `typer`, `rich` for CLI; dev dependencies: `pytest`, `hypothesis`, `black`, `pylint`, `mypy`
  - Configure Black, Pylint, and mypy in `pyproject.toml`
  - Create basic `README.md` and `.gitignore`
  - _Requirements: 6.1, 6.2_

- [x] 1.1 Set up testing framework and Docker configuration with Poetry
  - Configure pytest and Hypothesis as dev dependencies in Poetry
  - Create `Dockerfile` using Poetry for multi-version Python testing (3.11-3.14)
  - Set up basic test directory structure
  - Configure Poetry scripts for testing and linting
  - _Requirements: Testing Strategy_

- [x] 2. Implement configuration data models
  - Create `src/steering_wizard/models/config.py` with dataclasses
  - Define `TestingConfig`, `GitHubConfig`, `FormattingConfig`, `VirtualizationConfig`, and `ProjectConfiguration`
  - Add type hints and validation methods
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 2.1 Write property test for configuration models
  - **Property 3: Content Preservation Round-Trip**
  - **Validates: Requirements 3.2, 3.3, 4.4**

- [x] 3. Implement project discovery functionality
  - Create `src/steering_wizard/core/project_finder.py`
  - Implement `find_kiro_project()` method with directory traversal
  - Add `validate_project_structure()` and `ensure_steering_directory()` methods
  - Handle file system permissions and error cases
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 3.1 Write property test for project discovery
  - **Property 1: Project Discovery Consistency**
  - **Validates: Requirements 1.1, 1.2, 1.4**

- [x] 3.2 Write unit tests for project finder edge cases
  - Test permission denied scenarios
  - Test missing directory cases
  - Test invalid project structures
  - _Requirements: 5.1_

- [x] 4. Implement interactive questionnaire engine
  - Create `src/steering_wizard/core/questionnaire.py`
  - Implement user prompts for testing preferences, GitHub info, formatting rules, and virtualization preferences
  - Add input validation with re-prompting on invalid input
  - Handle custom formatting rules input
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 4.1 Write property test for input validation
  - **Property 2: Input Validation and Recovery**
  - **Validates: Requirements 2.2, 2.6, 5.2**

- [x] 4.2 Write property test for custom input handling
  - **Property 7: Custom Input Handling**
  - **Validates: Requirements 2.5**

- [x] 5. Checkpoint - Core functionality validation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement document generation engine
  - Create `src/steering_wizard/core/document_generator.py`
  - Implement `generate_development_guidelines()` with markdown template
  - Implement `generate_llm_guidance()` with current date and standard content
  - Add file existence checking and overwrite confirmation
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6.1 Write property test for file generation
  - **Property 4: File Generation Completeness**
  - **Validates: Requirements 3.1, 3.5, 4.1, 4.2, 4.3**

- [x] 6.2 Write unit tests for file overwrite scenarios
  - Test existing file detection and user confirmation
  - Test file cleanup on interruption
  - _Requirements: 3.4, 4.5, 5.3_

- [x] 7. Implement CLI interface with Typer
  - Create `src/steering_wizard/main.py` with Typer CLI setup
  - Add main command with `--help`, `--version`, `--target-dir`, and `--dry-run` options
  - Implement colored output and consistent formatting
  - Wire together all components for complete workflow
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 7.1 Write property test for CLI options
  - **Property 5: CLI Options Functionality**
  - **Validates: Requirements 6.3, 6.4**

- [x] 7.2 Write property test for output formatting
  - **Property 6: Output Formatting Consistency**
  - **Validates: Requirements 1.5, 3.5, 5.4, 6.5**

- [x] 7.3 Write unit tests for CLI interface
  - Test help and version output
  - Test error message formatting
  - Test success message display
  - _Requirements: 6.1, 6.2, 5.4, 5.5_

- [x] 8. Implement error handling and user experience features
  - Add comprehensive error handling throughout the application
  - Implement file cleanup on interruption (signal handling)
  - Add success summary with created file listing
  - Add option to display generated file contents
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8.1 Write integration tests for complete workflow
  - Test end-to-end wizard execution
  - Test error recovery scenarios
  - Test dry-run mode functionality
  - _Requirements: All requirements integration_

- [ ] 9. Final checkpoint and package preparation with Poetry
  - Ensure all tests pass across Python versions 3.11-3.14 using Poetry environments
  - Verify code formatting with Black and linting with Pylint via Poetry scripts
  - Test CLI installation with `poetry install` and execution
  - Prepare package for distribution with `poetry build`
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- Integration tests ensure end-to-end functionality
- Poetry manages dependencies, virtual environments, and package building
- Docker testing ensures compatibility across Python versions with Poetry