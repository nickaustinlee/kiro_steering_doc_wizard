"""Integration tests for the complete steering wizard workflow."""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner

from steering_wizard.main import main
from steering_wizard.models.config import ProjectConfiguration, TestingConfig, GitHubConfig, FormattingConfig, VirtualizationConfig


class TestIntegration:
    """Integration test cases for end-to-end functionality."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.runner = CliRunner()

    def teardown_method(self):
        """Clean up test environment after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_test_project(self, with_kiro_dir=True):
        """Create a test project structure."""
        project_dir = self.temp_dir / "test_project"
        project_dir.mkdir()
        
        if with_kiro_dir:
            kiro_dir = project_dir / ".kiro"
            kiro_dir.mkdir()
            
        return project_dir

    def test_complete_workflow_with_valid_inputs(self):
        """
        Test complete wizard execution with valid inputs.
        
        Requirements: All requirements integration
        """
        project_dir = self.create_test_project()
        
        # Mock user inputs for the questionnaire
        with patch('steering_wizard.core.questionnaire.Prompt.ask') as mock_prompt, \
             patch('steering_wizard.core.questionnaire.Confirm.ask') as mock_confirm, \
             patch('click.confirm') as mock_click_confirm:
            
            # Configure mock responses
            mock_prompt.side_effect = [
                "2",  # pytest testing
                "https://github.com/test/repo",  # GitHub URL
                "2",  # Poetry virtualization
            ]
            
            mock_confirm.side_effect = [
                True,   # Has GitHub repo
                True,   # Use GitHub Actions
                True,   # Use Black
                True,   # Use Google style
                False,  # No custom rules
                False,  # No venv docs
            ]
            
            mock_click_confirm.side_effect = [
                False,  # Don't show file contents
            ]
            
            # Run the wizard
            result = self.runner.invoke(main, ['--target-dir', str(project_dir)])
            
            # Verify successful execution
            assert result.exit_code == 0
            assert "Steering documents created successfully" in result.output
            
            # Verify files were created
            steering_dir = project_dir / ".kiro" / "steering"
            assert steering_dir.exists()
            assert (steering_dir / "development-guidelines.md").exists()
            assert (steering_dir / "llm-guidance.md").exists()
            
            # Verify file contents contain expected information
            dev_guidelines = (steering_dir / "development-guidelines.md").read_text()
            assert "pytest" in dev_guidelines
            assert "https://github.com/test/repo" in dev_guidelines
            assert "Poetry" in dev_guidelines
            
            llm_guidance = (project_dir / ".kiro" / "steering" / "llm-guidance.md").read_text()
            assert "**Generated on**:" in llm_guidance
            assert "pytest" in llm_guidance

    def test_dry_run_mode_functionality(self):
        """
        Test dry-run mode functionality.
        
        Requirements: 6.4
        """
        project_dir = self.create_test_project()
        
        with patch('steering_wizard.core.questionnaire.Prompt.ask') as mock_prompt, \
             patch('steering_wizard.core.questionnaire.Confirm.ask') as mock_confirm:
            
            # Configure minimal mock responses
            mock_prompt.side_effect = ["2", "2"]  # pytest, poetry
            mock_confirm.side_effect = [False, False, True, True, False, False]
            
            # Run in dry-run mode
            result = self.runner.invoke(main, ['--target-dir', str(project_dir), '--dry-run'])
            
            # Verify successful execution
            assert result.exit_code == 0
            assert "DRY RUN MODE" in result.output
            assert "Dry run completed successfully" in result.output
            
            # Verify no files were actually created
            steering_dir = project_dir / ".kiro" / "steering"
            if steering_dir.exists():
                assert not (steering_dir / "development-guidelines.md").exists()
                assert not (steering_dir / "llm-guidance.md").exists()

    def test_error_recovery_scenarios(self):
        """
        Test error recovery scenarios.
        
        Requirements: 5.1, 5.2, 5.3
        """
        # Test with non-existent target directory
        non_existent_dir = self.temp_dir / "non_existent"
        
        result = self.runner.invoke(main, ['--target-dir', str(non_existent_dir)])
        
        # Click returns exit code 2 for usage errors
        assert result.exit_code in [1, 2]
        assert "does not exist" in result.output

    def test_file_overwrite_handling(self):
        """
        Test file overwrite confirmation handling.
        
        Requirements: 3.4, 4.5, 5.3
        """
        project_dir = self.create_test_project()
        steering_dir = project_dir / ".kiro" / "steering"
        steering_dir.mkdir(parents=True)
        
        # Create existing files
        (steering_dir / "development-guidelines.md").write_text("Existing content")
        (steering_dir / "llm-guidance.md").write_text("Existing content")
        
        # Test that existing files are detected
        from steering_wizard.core.document_generator import DocumentGenerator
        from rich.console import Console
        
        doc_gen = DocumentGenerator(Console())
        existing_files = doc_gen.check_existing_files(steering_dir)
        
        assert len(existing_files) == 2
        assert any(f.name == "development-guidelines.md" for f in existing_files)
        assert any(f.name == "llm-guidance.md" for f in existing_files)

    def test_keyboard_interrupt_handling(self):
        """
        Test keyboard interrupt handling and cleanup.
        
        Requirements: 5.3
        """
        project_dir = self.create_test_project()
        
        with patch('steering_wizard.core.questionnaire.QuestionnaireEngine.collect_configuration') as mock_collect:
            # Simulate keyboard interrupt during configuration
            mock_collect.side_effect = KeyboardInterrupt()
            
            result = self.runner.invoke(main, ['--target-dir', str(project_dir)])
            
            assert result.exit_code == 1
            assert "Wizard interrupted by user" in result.output

    def test_permission_error_handling(self):
        """
        Test permission error handling.
        
        Requirements: 5.1
        """
        project_dir = self.create_test_project()
        
        # Make the .kiro directory read-only to simulate permission error
        kiro_dir = project_dir / ".kiro"
        os.chmod(kiro_dir, 0o444)  # Read-only
        
        try:
            with patch('steering_wizard.core.questionnaire.Prompt.ask') as mock_prompt, \
                 patch('steering_wizard.core.questionnaire.Confirm.ask') as mock_confirm:
                
                mock_prompt.side_effect = ["2", "2"]
                mock_confirm.side_effect = [False, False, True, True, False, False]
                
                result = self.runner.invoke(main, ['--target-dir', str(project_dir)])
                
                assert result.exit_code == 1
                assert ("Permission" in result.output or "permission" in result.output)
                
        finally:
            # Restore permissions for cleanup
            os.chmod(kiro_dir, 0o755)

    def test_version_option(self):
        """
        Test --version option functionality.
        
        Requirements: 6.2
        """
        result = self.runner.invoke(main, ['--version'])
        
        assert result.exit_code == 0
        assert "Steering Docs Wizard" in result.output
        assert "version" in result.output

    def test_help_option(self):
        """
        Test --help option functionality.
        
        Requirements: 6.1
        """
        result = self.runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert "Create standardized steering documents" in result.output
        assert "--target-dir" in result.output
        assert "--dry-run" in result.output

    def test_project_discovery_without_kiro_directory(self):
        """
        Test project discovery when no .kiro directory exists.
        
        Requirements: 1.1, 1.2, 1.3
        """
        project_dir = self.create_test_project(with_kiro_dir=False)
        
        # Test the project finder directly
        from steering_wizard.core.project_finder import ProjectFinder
        
        finder = ProjectFinder()
        
        # Should not find .kiro directory initially
        found_project = finder.find_kiro_project(project_dir)
        assert found_project is None
        
        # Create .kiro directory first
        kiro_dir = project_dir / ".kiro"
        kiro_dir.mkdir()
        
        # Now should be able to create steering directory
        steering_path = finder.ensure_steering_directory(project_dir)
        assert steering_path.exists()
        assert steering_path.name == "steering"
        assert steering_path.parent.name == ".kiro"

    def test_configuration_validation_failure(self):
        """
        Test configuration validation failure handling.
        
        Requirements: 2.7, 5.2
        """
        project_dir = self.create_test_project()
        
        with patch('steering_wizard.core.questionnaire.QuestionnaireEngine.validate_all_responses') as mock_validate:
            mock_validate.return_value = False
            
            with patch('steering_wizard.core.questionnaire.Prompt.ask') as mock_prompt, \
                 patch('steering_wizard.core.questionnaire.Confirm.ask') as mock_confirm:
                
                mock_prompt.side_effect = ["2", "2"]
                mock_confirm.side_effect = [False, False, True, True, False, False]
                
                result = self.runner.invoke(main, ['--target-dir', str(project_dir)])
                
                assert result.exit_code == 1
                assert "Configuration validation failed" in result.output

    def test_file_content_display_option(self):
        """
        Test file content display functionality.
        
        Requirements: 5.5
        """
        project_dir = self.create_test_project()
        
        with patch('steering_wizard.core.questionnaire.Prompt.ask') as mock_prompt, \
             patch('steering_wizard.core.questionnaire.Confirm.ask') as mock_confirm, \
             patch('click.confirm') as mock_click_confirm:
            
            # Configure mock responses
            mock_prompt.side_effect = ["2", "2"]
            mock_confirm.side_effect = [False, False, True, True, False, False]
            mock_click_confirm.side_effect = [True]  # Show file contents
            
            result = self.runner.invoke(main, ['--target-dir', str(project_dir)])
            
            assert result.exit_code == 0
            assert "Contents of development-guidelines.md" in result.output
            assert "Contents of llm-guidance.md" in result.output

    def test_custom_formatting_rules_integration(self):
        """
        Test integration with custom formatting rules.
        
        Requirements: 2.5
        """
        project_dir = self.create_test_project()
        
        with patch('steering_wizard.core.questionnaire.Prompt.ask') as mock_prompt, \
             patch('steering_wizard.core.questionnaire.Confirm.ask') as mock_confirm, \
             patch('steering_wizard.core.questionnaire.QuestionnaireEngine._prompt_custom_formatting_rules') as mock_custom, \
             patch('click.confirm') as mock_click_confirm:
            
            # Configure mock responses
            mock_prompt.side_effect = ["2", "2"]
            mock_confirm.side_effect = [False, False, True, True, True, False]  # Include custom rules
            mock_custom.return_value = "Custom rule: Use 120 character line length"
            mock_click_confirm.side_effect = [False]
            
            result = self.runner.invoke(main, ['--target-dir', str(project_dir)])
            
            assert result.exit_code == 0
            
            # Verify custom rules are included in the generated file
            dev_guidelines = (project_dir / ".kiro" / "steering" / "development-guidelines.md").read_text()
            assert "Custom rule: Use 120 character line length" in dev_guidelines
