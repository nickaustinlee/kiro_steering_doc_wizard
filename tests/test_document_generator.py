"""Tests for document_generator module."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st

from steering_wizard.core.document_generator import DocumentGenerator, DocumentGeneratorError, FileOverwriteError
from steering_wizard.models.config import (
    TestingConfig,
    GitHubConfig,
    FormattingConfig,
    VirtualizationConfig,
    ProjectConfiguration,
)


class TestDocumentGenerator:
    """Test cases for DocumentGenerator functionality."""

    def test_document_generator_initialization(self):
        """Test DocumentGenerator initialization."""
        generator = DocumentGenerator()
        assert generator is not None
        assert generator.console is not None

    def test_check_existing_files(self, temp_dir):
        """Test checking for existing files."""
        generator = DocumentGenerator()
        
        # Create some existing files
        (temp_dir / "development-guidelines.md").touch()
        (temp_dir / "llm-guidance.md").touch()
        (temp_dir / "other-file.md").touch()
        
        existing_files = generator.check_existing_files(temp_dir)
        
        # Should find the two standard files but not the other file
        assert len(existing_files) == 2
        file_names = [f.name for f in existing_files]
        assert "development-guidelines.md" in file_names
        assert "llm-guidance.md" in file_names
        assert "other-file.md" not in file_names

    def test_file_overwrite_confirmation_denied(self, temp_dir):
        """
        Test existing file detection and user confirmation when denied.
        
        Requirements: 3.4, 4.5, 5.3
        """
        # Create a mock console that denies overwrite
        mock_console = Mock()
        mock_console.print = Mock()
        
        generator = DocumentGenerator(console=mock_console)
        
        # Mock the Confirm.ask to return False (deny overwrite)
        with patch('steering_wizard.core.document_generator.Confirm.ask', return_value=False):
            # Create existing file
            existing_file = temp_dir / "development-guidelines.md"
            existing_file.write_text("existing content")
            
            # Create a simple configuration
            config = self._create_test_config(temp_dir)
            
            # Attempt to generate file should raise FileOverwriteError
            with pytest.raises(FileOverwriteError):
                generator.generate_development_guidelines(config, existing_file)
            
            # File should still contain original content
            assert existing_file.read_text() == "existing content"

    def test_file_overwrite_confirmation_accepted(self, temp_dir):
        """
        Test existing file detection and user confirmation when accepted.
        
        Requirements: 3.4, 4.5
        """
        # Create a mock console that accepts overwrite
        mock_console = Mock()
        mock_console.print = Mock()
        
        generator = DocumentGenerator(console=mock_console)
        
        # Mock the Confirm.ask to return True (accept overwrite)
        with patch('steering_wizard.core.document_generator.Confirm.ask', return_value=True):
            # Create existing file
            existing_file = temp_dir / "development-guidelines.md"
            existing_file.write_text("existing content")
            
            # Create a simple configuration
            config = self._create_test_config(temp_dir)
            
            # Generate file should succeed
            generator.generate_development_guidelines(config, existing_file)
            
            # File should contain new content
            new_content = existing_file.read_text()
            assert "existing content" not in new_content
            assert "# Development Guidelines" in new_content

    def test_file_cleanup_on_interruption(self, temp_dir):
        """
        Test file cleanup on interruption.
        
        Requirements: 5.3
        """
        mock_console = Mock()
        generator = DocumentGenerator(console=mock_console)
        
        # Create test files that would be cleaned up
        test_file1 = temp_dir / "development-guidelines.md"
        test_file2 = temp_dir / "llm-guidance.md"
        
        # Add files to cleanup list manually (simulating partial creation)
        generator._cleanup_files = [test_file1, test_file2]
        
        # Create the files
        test_file1.write_text("partial content 1")
        test_file2.write_text("partial content 2")
        
        # Verify files exist
        assert test_file1.exists()
        assert test_file2.exists()
        
        # Call cleanup
        generator._cleanup_partial_files()
        
        # Verify files are removed
        assert not test_file1.exists()
        assert not test_file2.exists()
        
        # Verify cleanup list is cleared
        assert len(generator._cleanup_files) == 0

    def test_file_cleanup_handles_missing_files(self, temp_dir):
        """
        Test file cleanup handles missing files gracefully.
        
        Requirements: 5.3
        """
        mock_console = Mock()
        generator = DocumentGenerator(console=mock_console)
        
        # Add non-existent files to cleanup list
        non_existent_file = temp_dir / "non-existent.md"
        generator._cleanup_files = [non_existent_file]
        
        # Cleanup should not raise an error
        generator._cleanup_partial_files()
        
        # Verify cleanup list is cleared
        assert len(generator._cleanup_files) == 0

    def test_successful_file_generation_removes_from_cleanup(self, temp_dir):
        """
        Test that successful file generation removes files from cleanup list.
        
        Requirements: 5.3
        """
        mock_console = Mock()
        generator = DocumentGenerator(console=mock_console)
        
        # Create a simple configuration
        config = self._create_test_config(temp_dir)
        
        # Generate file
        output_file = temp_dir / "development-guidelines.md"
        generator.generate_development_guidelines(config, output_file)
        
        # Verify file was created
        assert output_file.exists()
        
        # Verify cleanup list is empty (file was removed after successful generation)
        assert len(generator._cleanup_files) == 0

    def _create_test_config(self, project_path: Path) -> ProjectConfiguration:
        """Create a simple test configuration."""
        testing = TestingConfig(
            local_testing="pytest", use_docker=False, use_pytest=True
        )
        github = GitHubConfig(repository_url=None, use_github_actions=False)
        formatting = FormattingConfig(
            use_black=True, use_google_style=True, custom_rules=None
        )
        virtualization = VirtualizationConfig(
            preference="poetry", include_venv_docs=False
        )
        
        return ProjectConfiguration.create_with_current_date(
            testing=testing,
            github=github,
            formatting=formatting,
            virtualization=virtualization,
            project_path=project_path,
        )


# Property-based test for File Generation Completeness
@given(
    local_testing=st.sampled_from(["docker", "pytest", "both", "none"]),
    use_docker=st.booleans(),
    use_pytest=st.booleans(),
    repository_url=st.one_of(
        st.none(),
        st.text(min_size=1, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc"))).map(
            lambda x: f"https://github.com/user/{x[:20]}"  # Limit length for valid URLs
        ),
    ),
    use_github_actions=st.booleans(),
    use_black=st.booleans(),
    use_google_style=st.booleans(),
    custom_rules=st.one_of(st.none(), st.text(max_size=200)),  # Limit size for reasonable test performance
    preference=st.sampled_from(["venv", "poetry", "poetry_with_venv_docs"]),
    include_venv_docs=st.booleans(),
)
def test_file_generation_completeness(
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
    Property 4: File Generation Completeness

    For any valid project directory and user configuration, the wizard should create
    both development-guidelines.md and llm-guidance.md files with all required sections
    (date, user preferences, standard guidance) in valid markdown format.

    **Feature: steering-docs-wizard, Property 4: File Generation Completeness**
    **Validates: Requirements 3.1, 3.5, 4.1, 4.2, 4.3**
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

        # Only test with valid configurations
        if not (testing.validate() and github.validate() and formatting.validate() and virtualization.validate()):
            return

        # Create the complete configuration
        config = ProjectConfiguration.create_with_current_date(
            testing=testing,
            github=github,
            formatting=formatting,
            virtualization=virtualization,
            project_path=temp_path,
        )

        # Create document generator with mocked console to avoid interactive prompts
        mock_console = Mock()
        generator = DocumentGenerator(console=mock_console)

        # Generate both documents
        dev_guidelines_path = temp_path / "development-guidelines.md"
        llm_guidance_path = temp_path / "llm-guidance.md"

        generator.generate_development_guidelines(config, dev_guidelines_path)
        generator.generate_llm_guidance(config, llm_guidance_path)

        # Verify both files were created
        assert dev_guidelines_path.exists(), "development-guidelines.md should be created"
        assert llm_guidance_path.exists(), "llm-guidance.md should be created"

        # Read and verify content of development guidelines
        dev_content = dev_guidelines_path.read_text(encoding='utf-8')
        
        # Verify required sections and content preservation
        assert "# Development Guidelines" in dev_content
        assert config.creation_date in dev_content
        assert local_testing in dev_content
        
        # Check for boolean values in the format the generator actually outputs
        docker_text = "Yes" if use_docker else "No"
        pytest_text = "Yes" if use_pytest else "No"
        assert docker_text in dev_content
        assert pytest_text in dev_content
        
        if repository_url:
            assert repository_url in dev_content
        
        if custom_rules and custom_rules.strip():
            # Normalize line endings for comparison since file writing may normalize them
            normalized_custom_rules = custom_rules.replace('\r\n', '\n').replace('\r', '\n')
            assert normalized_custom_rules in dev_content
            
        assert preference in dev_content

        # Read and verify content of LLM guidance
        llm_content = llm_guidance_path.read_text(encoding='utf-8')
        
        # Verify required sections and content preservation
        assert "# LLM Development Guidance" in llm_content
        assert config.creation_date in llm_content
        assert local_testing in llm_content
        assert preference in llm_content
        
        if repository_url:
            assert repository_url in llm_content
            
        if custom_rules and custom_rules.strip():
            # Normalize line endings for comparison since file writing may normalize them
            normalized_custom_rules = custom_rules.replace('\r\n', '\n').replace('\r', '\n')
            assert normalized_custom_rules in llm_content

        # Verify both files contain valid markdown structure
        assert dev_content.startswith("# ")
        assert llm_content.startswith("# ")
        
        # Verify files are not empty and have substantial content
        assert len(dev_content) > 100, "Development guidelines should have substantial content"
        assert len(llm_content) > 100, "LLM guidance should have substantial content"

    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_path, ignore_errors=True)
