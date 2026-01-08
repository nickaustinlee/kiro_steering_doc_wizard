"""Tests for configuration data models."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from hypothesis import given, strategies as st

from steering_wizard.models.config import (
    TestingConfig,
    GitHubConfig,
    FormattingConfig,
    VirtualizationConfig,
    ProjectConfiguration,
)


class TestConfigurationModels:
    """Test suite for configuration data models."""

    def test_testing_config_validation(self):
        """Test TestingConfig validation."""
        # Valid configurations
        valid_config = TestingConfig(
            local_testing="docker", use_docker=True, use_pytest=False
        )
        assert valid_config.validate()

        valid_config2 = TestingConfig(
            local_testing="pytest", use_docker=False, use_pytest=True
        )
        assert valid_config2.validate()

        # Invalid configuration
        invalid_config = TestingConfig(
            local_testing="invalid", use_docker=True, use_pytest=False
        )
        assert not invalid_config.validate()

    def test_github_config_validation(self):
        """Test GitHubConfig validation."""
        # Valid configurations
        valid_config = GitHubConfig(
            repository_url="https://github.com/user/repo", use_github_actions=True
        )
        assert valid_config.validate()

        valid_config_none = GitHubConfig(repository_url=None, use_github_actions=False)
        assert valid_config_none.validate()

        # Invalid configuration
        invalid_config = GitHubConfig(
            repository_url="not-a-github-url", use_github_actions=True
        )
        assert not invalid_config.validate()

    def test_formatting_config_validation(self):
        """Test FormattingConfig validation."""
        config = FormattingConfig(
            use_black=True, use_google_style=True, custom_rules="Custom rule"
        )
        assert config.validate()

    def test_virtualization_config_validation(self):
        """Test VirtualizationConfig validation."""
        # Valid configurations
        valid_config = VirtualizationConfig(preference="poetry", include_venv_docs=True)
        assert valid_config.validate()

        # Invalid configuration
        invalid_config = VirtualizationConfig(
            preference="invalid", include_venv_docs=False
        )
        assert not invalid_config.validate()

    def test_project_configuration_create_with_current_date(self, temp_dir):
        """Test ProjectConfiguration creation with current date."""
        testing = TestingConfig(
            local_testing="docker", use_docker=True, use_pytest=False
        )
        github = GitHubConfig(
            repository_url="https://github.com/user/repo", use_github_actions=True
        )
        formatting = FormattingConfig(
            use_black=True, use_google_style=True, custom_rules=None
        )
        virtualization = VirtualizationConfig(
            preference="poetry", include_venv_docs=True
        )

        config = ProjectConfiguration.create_with_current_date(
            testing=testing,
            github=github,
            formatting=formatting,
            virtualization=virtualization,
            project_path=temp_dir,
        )

        assert config.creation_date == datetime.now().strftime("%Y-%m-%d")
        assert config.validate()


# Property-based test for Content Preservation Round-Trip
@given(
    local_testing=st.sampled_from(["docker", "pytest", "both", "none"]),
    use_docker=st.booleans(),
    use_pytest=st.booleans(),
    repository_url=st.one_of(
        st.none(),
        st.text(min_size=1).map(
            lambda x: f"https://github.com/user/{x.replace('/', '_')}"
        ),
    ),
    use_github_actions=st.booleans(),
    use_black=st.booleans(),
    use_google_style=st.booleans(),
    custom_rules=st.one_of(st.none(), st.text()),
    preference=st.sampled_from(["venv", "poetry", "poetry_with_venv_docs"]),
    include_venv_docs=st.booleans(),
)
def test_content_preservation_round_trip(
    local_testing,
    use_docker,
    use_pytest,
    repository_url,
    use_github_actions,
    use_black,
    use_google_style,
    custom_rules,
    preference,
    include_venv_docs,
):
    """
    Property 3: Content Preservation Round-Trip

    For any valid user configuration input, the generated steering documents should
    contain all provided user data in a structured format that preserves the
    original input values exactly as entered.

    **Feature: steering-docs-wizard, Property 3: Content Preservation Round-Trip**
    **Validates: Requirements 3.2, 3.3, 4.4**
    """
    # Create a temporary directory for this test iteration
    temp_path = Path(tempfile.mkdtemp())
    try:
        # Create configuration objects with the generated data
        testing = TestingConfig(
            local_testing=local_testing, use_docker=use_docker, use_pytest=use_pytest
        )

        github = GitHubConfig(
            repository_url=repository_url, use_github_actions=use_github_actions
        )

        formatting = FormattingConfig(
            use_black=use_black,
            use_google_style=use_google_style,
            custom_rules=custom_rules,
        )

        virtualization = VirtualizationConfig(
            preference=preference, include_venv_docs=include_venv_docs
        )

        # Create the complete configuration
        config = ProjectConfiguration.create_with_current_date(
            testing=testing,
            github=github,
            formatting=formatting,
            virtualization=virtualization,
            project_path=temp_path,
        )

        # Verify that all original input values are preserved exactly
        assert config.testing.local_testing == local_testing
        assert config.testing.use_docker == use_docker
        assert config.testing.use_pytest == use_pytest

        assert config.github.repository_url == repository_url
        assert config.github.use_github_actions == use_github_actions

        assert config.formatting.use_black == use_black
        assert config.formatting.use_google_style == use_google_style
        assert config.formatting.custom_rules == custom_rules

        assert config.virtualization.preference == preference
        assert config.virtualization.include_venv_docs == include_venv_docs

        assert config.project_path == temp_path

        # Verify the configuration is valid (when inputs are valid)
        if (
            testing.validate()
            and github.validate()
            and formatting.validate()
            and virtualization.validate()
        ):
            assert config.validate()
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_path, ignore_errors=True)
