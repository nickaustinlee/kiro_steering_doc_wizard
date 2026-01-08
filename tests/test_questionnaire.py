"""Tests for the interactive questionnaire engine."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, assume
from rich.console import Console

from steering_wizard.core.questionnaire import QuestionnaireEngine
from steering_wizard.models.config import (
    TestingConfig,
    GitHubConfig,
    FormattingConfig,
    VirtualizationConfig,
    ProjectConfiguration,
)


class TestQuestionnaireEngine:
    """Test suite for QuestionnaireEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock(spec=Console)
        self.engine = QuestionnaireEngine(console=self.console)
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_questionnaire_engine_initialization(self):
        """Test QuestionnaireEngine initialization."""
        # Test with provided console
        engine_with_console = QuestionnaireEngine(console=self.console)
        assert engine_with_console.console == self.console

        # Test with default console
        engine_default = QuestionnaireEngine()
        assert engine_default.console is not None

    def test_validate_all_responses_valid_config(self):
        """Test validation with valid configuration."""
        config = self._create_valid_config()
        result = self.engine.validate_all_responses(config)
        assert result is True

    def test_validate_all_responses_invalid_config(self):
        """Test validation with invalid configuration."""
        # Create config with invalid testing preference
        testing = TestingConfig(
            local_testing="invalid", use_docker=True, use_pytest=False
        )
        github = GitHubConfig(repository_url=None, use_github_actions=False)
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
            project_path=self.temp_dir,
        )

        result = self.engine.validate_all_responses(config)
        assert result is False

    def _create_valid_config(self) -> ProjectConfiguration:
        """Create a valid ProjectConfiguration for testing."""
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

        return ProjectConfiguration.create_with_current_date(
            testing=testing,
            github=github,
            formatting=formatting,
            virtualization=virtualization,
            project_path=self.temp_dir,
        )


# Property-based test for Input Validation and Recovery
@given(
    invalid_urls=st.one_of(
        st.text(min_size=1, max_size=50).filter(
            lambda x: not x.startswith("https://github.com/")
        ),
        st.just("not-a-url"),
        st.just("http://github.com/user/repo"),  # Wrong protocol
        st.just("https://gitlab.com/user/repo"),  # Wrong domain
        st.just("https://github.com/"),  # Missing user/repo
        st.just("https://github.com/user"),  # Missing repo
    ),
    valid_urls=st.one_of(
        st.just("https://github.com/user/repo"),
        st.just("https://github.com/test-user/test-repo"),
        st.just("https://github.com/user123/repo-name"),
        st.just("https://github.com/user/repo/"),  # With trailing slash
    ),
)
def test_input_validation_and_recovery(invalid_urls, valid_urls):
    """
    Property 2: Input Validation and Recovery

    For any user input that fails validation (invalid URLs, missing required fields),
    the system should re-prompt with specific validation feedback and allow the user
    to correct their input without losing previous valid responses.

    **Feature: steering-docs-wizard, Property 2: Input Validation and Recovery**
    **Validates: Requirements 2.2, 2.6, 5.2**
    """
    import re

    # Test GitHub URL validation pattern
    github_pattern = r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$"

    # Invalid URLs should not match the pattern
    assert not re.match(
        github_pattern, invalid_urls
    ), f"Invalid URL {invalid_urls} should not match pattern"

    # Valid URLs should match the pattern
    assert re.match(
        github_pattern, valid_urls
    ), f"Valid URL {valid_urls} should match pattern"

    # Test GitHubConfig validation
    invalid_config = GitHubConfig(repository_url=invalid_urls, use_github_actions=True)
    assert (
        not invalid_config.validate()
    ), f"GitHubConfig with invalid URL {invalid_urls} should not validate"

    valid_config = GitHubConfig(repository_url=valid_urls, use_github_actions=True)
    assert (
        valid_config.validate()
    ), f"GitHubConfig with valid URL {valid_urls} should validate"

    # Test that None URLs are always valid (optional field)
    none_config = GitHubConfig(repository_url=None, use_github_actions=False)
    assert none_config.validate(), "GitHubConfig with None URL should always validate"


# Property-based test for Custom Input Handling
@given(
    custom_rules=st.one_of(
        st.none(),
        st.text(),
        st.text(min_size=1, max_size=1000),
        st.text().filter(lambda x: "\n" in x),  # Multi-line text
        st.just(""),  # Empty string
        st.just("   "),  # Whitespace only
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Ps", "Pe", "Po")
            )
        ),  # Various characters
    )
)
def test_custom_input_handling(custom_rules):
    """
    Property 7: Custom Input Handling

    For any custom formatting rules or free-form text input provided by the user,
    the system should accept and preserve the input without modification while
    incorporating it appropriately into the generated documents.

    **Feature: steering-docs-wizard, Property 7: Custom Input Handling**
    **Validates: Requirements 2.5**
    """
    # Create FormattingConfig with custom rules
    config = FormattingConfig(
        use_black=True, use_google_style=True, custom_rules=custom_rules
    )

    # The configuration should always be valid regardless of custom rules content
    assert (
        config.validate()
    ), f"FormattingConfig should validate with any custom rules: {repr(custom_rules)}"

    # The custom rules should be preserved exactly as provided
    assert (
        config.custom_rules == custom_rules
    ), f"Custom rules should be preserved exactly: expected {repr(custom_rules)}, got {repr(config.custom_rules)}"

    # Test that the configuration can be created and used in ProjectConfiguration
    temp_path = Path(tempfile.mkdtemp())
    try:
        testing = TestingConfig(
            local_testing="pytest", use_docker=False, use_pytest=True
        )
        github = GitHubConfig(repository_url=None, use_github_actions=False)
        virtualization = VirtualizationConfig(
            preference="poetry", include_venv_docs=True
        )

        project_config = ProjectConfiguration.create_with_current_date(
            testing=testing,
            github=github,
            formatting=config,
            virtualization=virtualization,
            project_path=temp_path,
        )

        # The custom rules should still be preserved in the complete configuration
        assert (
            project_config.formatting.custom_rules == custom_rules
        ), "Custom rules should be preserved in ProjectConfiguration"

        # The project configuration should be valid when all components are valid
        if (
            testing.validate()
            and github.validate()
            and config.validate()
            and virtualization.validate()
        ):
            assert (
                project_config.validate()
            ), "ProjectConfiguration should be valid when all components are valid"

    finally:
        # Clean up
        shutil.rmtree(temp_path, ignore_errors=True)


# Additional unit tests for specific validation scenarios
class TestInputValidationScenarios:
    """Test specific input validation scenarios."""

    def test_testing_config_validation_scenarios(self):
        """Test various TestingConfig validation scenarios."""
        # Valid scenarios
        valid_configs = [
            TestingConfig("docker", True, False),
            TestingConfig("pytest", False, True),
            TestingConfig("both", True, True),
            TestingConfig("none", False, False),
        ]

        for config in valid_configs:
            assert config.validate(), f"Config should be valid: {config}"

        # Invalid scenarios
        invalid_configs = [
            TestingConfig("invalid", True, False),
            TestingConfig("", True, False),
        ]

        for config in invalid_configs:
            assert not config.validate(), f"Config should be invalid: {config}"

    def test_virtualization_config_validation_scenarios(self):
        """Test various VirtualizationConfig validation scenarios."""
        # Valid scenarios
        valid_configs = [
            VirtualizationConfig("venv", True),
            VirtualizationConfig("poetry", False),
            VirtualizationConfig("poetry_with_venv_docs", True),
        ]

        for config in valid_configs:
            assert config.validate(), f"Config should be valid: {config}"

        # Invalid scenarios
        invalid_configs = [
            VirtualizationConfig("invalid", True),
            VirtualizationConfig("", True),
        ]

        for config in invalid_configs:
            assert not config.validate(), f"Config should be invalid: {config}"
