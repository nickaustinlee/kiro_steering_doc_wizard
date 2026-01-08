"""Configuration data models for the steering docs wizard."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re
from datetime import datetime


@dataclass
class TestingConfig:
    """Configuration for testing preferences."""

    local_testing: str
    use_docker: bool
    use_pytest: bool

    def validate(self) -> bool:
        """Validate testing configuration."""
        valid_local_testing = ["docker", "pytest", "both", "none"]
        return self.local_testing.lower() in valid_local_testing


@dataclass
class GitHubConfig:
    """Configuration for GitHub integration."""

    repository_url: Optional[str]
    use_github_actions: bool

    def validate(self) -> bool:
        """Validate GitHub configuration."""
        if self.repository_url is None:
            return True

        # GitHub URL validation regex
        github_pattern = r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$"
        return bool(re.match(github_pattern, self.repository_url))


@dataclass
class FormattingConfig:
    """Configuration for code formatting preferences."""

    use_black: bool
    use_google_style: bool
    custom_rules: Optional[str]

    def validate(self) -> bool:
        """Validate formatting configuration."""
        # All formatting configurations are valid
        return True


@dataclass
class VirtualizationConfig:
    """Configuration for virtualization preferences."""

    preference: str  # "venv", "poetry", "poetry_with_venv_docs"
    include_venv_docs: bool

    def validate(self) -> bool:
        """Validate virtualization configuration."""
        valid_preferences = ["venv", "poetry", "poetry_with_venv_docs"]
        return self.preference.lower() in valid_preferences


@dataclass
class ProjectConfiguration:
    """Complete project configuration containing all user preferences."""

    testing: TestingConfig
    github: GitHubConfig
    formatting: FormattingConfig
    virtualization: VirtualizationConfig
    project_path: Path
    creation_date: str

    def validate(self) -> bool:
        """Validate the complete project configuration."""
        return (
            self.testing.validate()
            and self.github.validate()
            and self.formatting.validate()
            and self.virtualization.validate()
            and self.project_path.exists()
            and self._validate_date_format()
        )

    def _validate_date_format(self) -> bool:
        """Validate that creation_date is in YYYY-MM-DD format."""
        try:
            datetime.strptime(self.creation_date, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @classmethod
    def create_with_current_date(
        cls,
        testing: TestingConfig,
        github: GitHubConfig,
        formatting: FormattingConfig,
        virtualization: VirtualizationConfig,
        project_path: Path,
    ) -> "ProjectConfiguration":
        """Create a ProjectConfiguration with the current date."""
        current_date = datetime.now().strftime("%Y-%m-%d")
        return cls(
            testing=testing,
            github=github,
            formatting=formatting,
            virtualization=virtualization,
            project_path=project_path,
            creation_date=current_date,
        )
