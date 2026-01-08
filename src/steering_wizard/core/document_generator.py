"""Document generation engine for creating steering documents."""

import os
import signal
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel

from ..models.config import ProjectConfiguration


class DocumentGeneratorError(Exception):
    """Base exception for document generator errors."""
    pass


class FileOverwriteError(DocumentGeneratorError):
    """Raised when file overwrite is denied by user."""
    pass


class DocumentGenerator:
    """Creates steering documents from collected configuration data."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the document generator."""
        self.console = console or Console()
        self._cleanup_files: list[Path] = []
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for cleanup on interruption."""
        def signal_handler(signum, frame):
            self._cleanup_partial_files()
            sys.exit(1)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def generate_development_guidelines(
        self, config: ProjectConfiguration, output_path: Path
    ) -> None:
        """
        Generate development-guidelines.md file from configuration.

        Args:
            config: Project configuration containing user preferences.
            output_path: Path to the output file.

        Raises:
            FileOverwriteError: If file exists and user denies overwrite.
            DocumentGeneratorError: If file generation fails.

        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        # Check for existing file and get user confirmation
        if output_path.exists():
            if not self._confirm_overwrite(output_path):
                raise FileOverwriteError(f"User denied overwrite of {output_path}")

        # Add to cleanup list
        self._cleanup_files.append(output_path)

        try:
            content = self._generate_development_guidelines_content(config)
            self._write_file_safely(output_path, content)
            self.console.print(f"[green]✓ Created development-guidelines.md[/green]")
        except Exception as e:
            raise DocumentGeneratorError(f"Failed to generate development guidelines: {e}") from e
        finally:
            # Remove from cleanup list on successful completion
            if output_path in self._cleanup_files:
                self._cleanup_files.remove(output_path)

    def generate_llm_guidance(
        self, config: ProjectConfiguration, output_path: Path
    ) -> None:
        """
        Generate llm-guidance.md file with current date and standard content.

        Args:
            config: Project configuration containing user preferences.
            output_path: Path to the output file.

        Raises:
            FileOverwriteError: If file exists and user denies overwrite.
            DocumentGeneratorError: If file generation fails.

        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
        """
        # Check for existing file and get user confirmation
        if output_path.exists():
            if not self._confirm_overwrite(output_path):
                raise FileOverwriteError(f"User denied overwrite of {output_path}")

        # Add to cleanup list
        self._cleanup_files.append(output_path)

        try:
            content = self._generate_llm_guidance_content(config)
            self._write_file_safely(output_path, content)
            self.console.print(f"[green]✓ Created llm-guidance.md[/green]")
        except Exception as e:
            raise DocumentGeneratorError(f"Failed to generate LLM guidance: {e}") from e
        finally:
            # Remove from cleanup list on successful completion
            if output_path in self._cleanup_files:
                self._cleanup_files.remove(output_path)

    def check_existing_files(self, output_dir: Path) -> list[Path]:
        """
        Check for existing steering files that might be overwritten.

        Args:
            output_dir: Directory to check for existing files.

        Returns:
            List of existing steering files.

        Requirements: 3.4, 4.5
        """
        existing_files = []
        standard_files = ["development-guidelines.md", "llm-guidance.md"]

        for filename in standard_files:
            file_path = output_dir / filename
            if file_path.exists():
                existing_files.append(file_path)

        return existing_files

    def _confirm_overwrite(self, file_path: Path) -> bool:
        """
        Confirm with user before overwriting existing file.

        Args:
            file_path: Path to the file that would be overwritten.

        Returns:
            True if user confirms overwrite, False otherwise.

        Requirements: 3.4, 4.5
        """
        self.console.print(f"\n[yellow]Warning: File already exists: {file_path.name}[/yellow]")
        return Confirm.ask(f"Do you want to overwrite {file_path.name}?", default=False)

    def _write_file_safely(self, file_path: Path, content: str) -> None:
        """
        Write content to file with error handling.

        Args:
            file_path: Path to write the file.
            content: Content to write.

        Raises:
            DocumentGeneratorError: If writing fails.
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except OSError as e:
            raise DocumentGeneratorError(f"Failed to write file {file_path}: {e}") from e

    def cleanup_on_interruption(self) -> None:
        """
        Public method to clean up partial files on interruption.
        
        Requirements: 5.3
        """
        if self._cleanup_files:
            self.console.print("\n[yellow]Cleaning up partial files...[/yellow]")
            self._cleanup_partial_files()
        
    def _cleanup_partial_files(self) -> None:
        """
        Clean up partially created files on interruption.

        Requirements: 5.3
        """
        for file_path in self._cleanup_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    self.console.print(f"[yellow]Cleaned up partial file: {file_path.name}[/yellow]")
            except OSError:
                # Ignore cleanup errors
                pass
        self._cleanup_files.clear()

    def _generate_development_guidelines_content(self, config: ProjectConfiguration) -> str:
        """
        Generate the content for development-guidelines.md.

        Args:
            config: Project configuration.

        Returns:
            Markdown content for development guidelines.

        Requirements: 3.1, 3.2, 3.3, 3.5
        """
        content = f"""# Development Guidelines

Generated on: {config.creation_date}

## Project Configuration

### Testing Preferences
- **Local Testing**: {config.testing.local_testing}
- **Docker Support**: {'Yes' if config.testing.use_docker else 'No'}
- **Pytest Support**: {'Yes' if config.testing.use_pytest else 'No'}

### GitHub Configuration
"""

        if config.github.repository_url:
            content += f"""- **Repository URL**: {config.github.repository_url}
- **GitHub Actions**: {'Yes' if config.github.use_github_actions else 'No'}
"""
        else:
            content += "- **Repository**: Not configured\n"

        content += f"""
### Code Formatting
- **Black Formatter**: {'Yes' if config.formatting.use_black else 'No'}
- **Google Style Guide**: {'Yes' if config.formatting.use_google_style else 'No'}
"""

        if config.formatting.custom_rules:
            content += f"""
#### Custom Formatting Rules
```
{config.formatting.custom_rules}
```
"""

        content += f"""
### Virtualization
- **Preference**: {config.virtualization.preference}
- **Include venv Documentation**: {'Yes' if config.virtualization.include_venv_docs else 'No'}

## Development Workflow

This document captures the development preferences for this project. These settings should be used to configure development tools and CI/CD pipelines.

### Testing Setup
"""

        if config.testing.use_docker:
            content += """
#### Docker Testing
- Use Docker containers for consistent testing environments
- Ensure Dockerfile is properly configured for the project
"""

        if config.testing.use_pytest:
            content += """
#### Pytest Configuration
- Use pytest as the primary testing framework
- Configure pytest.ini or pyproject.toml for test discovery
- Include appropriate test coverage reporting
"""

        if config.github.use_github_actions:
            content += f"""
### GitHub Actions
- Configure automated testing workflows
- Repository: {config.github.repository_url or 'TBD'}
- Include testing across multiple Python versions if applicable
"""

        content += """
### Code Quality
"""

        if config.formatting.use_black:
            content += """
#### Black Formatter
- Use Black for automatic code formatting
- Configure line length and other Black settings as needed
"""

        if config.formatting.use_google_style:
            content += """
#### Google Python Style Guide
- Follow Google Python style guide for code structure
- Use appropriate docstring formats
- Maintain consistent naming conventions
"""

        if config.virtualization.preference == "poetry":
            content += """
### Dependency Management
- Use Poetry for dependency management and packaging
- Maintain pyproject.toml for project configuration
- Use Poetry environments for development
"""
        elif config.virtualization.preference == "venv":
            content += """
### Virtual Environments
- Use Python venv for virtual environment management
- Maintain requirements.txt for dependencies
- Document environment setup procedures
"""
        elif config.virtualization.preference == "poetry_with_venv_docs":
            content += """
### Dependency Management
- Use Poetry for dependency management and packaging
- Maintain pyproject.toml for project configuration
- Include venv documentation for alternative setup methods
"""

        if config.virtualization.include_venv_docs:
            content += """
#### Virtual Environment Setup (Alternative)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```
"""

        content += """
---

*This document was generated by the Steering Docs Wizard. Update these guidelines as your project evolves.*
"""

        return content

    def _generate_llm_guidance_content(self, config: ProjectConfiguration) -> str:
        """
        Generate the content for llm-guidance.md.

        Args:
            config: Project configuration.

        Returns:
            Markdown content for LLM guidance.

        Requirements: 4.1, 4.2, 4.3, 4.4
        """
        content = f"""# LLM Development Guidance

**Generated on**: {config.creation_date}

## Project Context

This document provides guidance for AI development assistants working on this project.

### Development Environment
- **Testing Framework**: {config.testing.local_testing}
- **Virtualization**: {config.virtualization.preference}
- **Code Formatting**: {'Black' if config.formatting.use_black else 'Manual'} + {'Google Style' if config.formatting.use_google_style else 'Custom Style'}

### Repository Information
"""

        if config.github.repository_url:
            content += f"""- **GitHub Repository**: {config.github.repository_url}
- **CI/CD**: {'GitHub Actions configured' if config.github.use_github_actions else 'Manual testing'}
"""
        else:
            content += "- **Repository**: Local development (no remote repository configured)\n"

        content += """
## Development Guidelines

### Code Quality Standards
"""

        if config.formatting.use_black:
            content += """
#### Formatting
- Use Black formatter for all Python code
- Maintain consistent code formatting across the project
"""

        if config.formatting.use_google_style:
            content += """
#### Style Guide
- Follow Google Python Style Guide
- Use proper docstring formats
- Maintain clear and descriptive variable names
"""

        if config.formatting.custom_rules:
            content += f"""
#### Custom Formatting Rules
The project has specific formatting requirements:

```
{config.formatting.custom_rules}
```
"""

        content += """
### Testing Approach
"""

        if config.testing.use_pytest:
            content += """
- Use pytest for unit testing and integration testing
- Write comprehensive test coverage for new features
- Follow test-driven development practices where appropriate
"""

        if config.testing.use_docker:
            content += """
- Use Docker for consistent testing environments
- Ensure tests pass in containerized environments
- Consider multi-stage Docker builds for testing
"""

        content += f"""
### Environment Management
"""

        if config.virtualization.preference == "poetry":
            content += """
- Use Poetry for dependency management
- Update pyproject.toml for new dependencies
- Use `poetry install` for environment setup
- Use `poetry add` for adding new dependencies
"""
        elif config.virtualization.preference == "venv":
            content += """
- Use Python venv for virtual environments
- Update requirements.txt for new dependencies
- Document environment setup in README
"""
        elif config.virtualization.preference == "poetry_with_venv_docs":
            content += """
- Primary: Use Poetry for dependency management
- Alternative: Support venv setup for contributors
- Maintain both pyproject.toml and requirements.txt when needed
"""

        content += """
## AI Assistant Guidelines

### Efficiency and Collaboration
1. **Incremental Development**: Make small, focused changes that can be easily reviewed
2. **Clear Communication**: Explain reasoning behind architectural decisions
3. **Error Handling**: Implement robust error handling and user-friendly error messages
4. **Documentation**: Keep code comments and documentation up to date
5. **Testing**: Write tests for new functionality and ensure existing tests pass

### Code Generation Best Practices
1. **Follow Project Patterns**: Maintain consistency with existing code structure
2. **Type Hints**: Use Python type hints for better code clarity
3. **Error Messages**: Provide helpful error messages with suggested solutions
4. **Performance**: Consider performance implications of code changes
5. **Security**: Follow security best practices for file operations and user input

### Project-Specific Considerations
"""

        if config.github.use_github_actions:
            content += """
- **CI/CD Integration**: Ensure changes are compatible with GitHub Actions workflows
"""

        if config.testing.local_testing != "none":
            content += f"""
- **Testing Strategy**: Align with the project's {config.testing.local_testing} testing approach
"""

        content += f"""
- **Development Workflow**: Respect the {config.virtualization.preference} environment setup
"""

        if config.formatting.custom_rules:
            content += """
- **Custom Requirements**: Follow the project-specific formatting rules defined above
"""

        content += f"""
### Current Project State
- **Configuration Date**: {config.creation_date}
- **Project Path**: {config.project_path}

---

*This guidance document was automatically generated based on project configuration. Update as the project evolves.*
"""

        return content