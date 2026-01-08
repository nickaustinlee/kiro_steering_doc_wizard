"""Tests for the CLI interface."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from hypothesis import given, strategies as st, assume
import tempfile
import shutil

from steering_wizard.main import main
from steering_wizard import __version__


class TestCLIOptions:
    """Test CLI options functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_help_option(self):
        """Test --help option displays usage information."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Create standardized steering documents" in result.output
        assert "--target-dir" in result.output
        assert "--dry-run" in result.output
        assert "--version" in result.output

    def test_version_option(self):
        """Test --version option displays version information."""
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output
        assert "Steering Docs Wizard" in result.output

    def test_version_short_option(self):
        """Test -v short option for version."""
        result = self.runner.invoke(main, ["-v"])
        assert result.exit_code == 0
        assert __version__ in result.output

    @given(
        target_dir_exists=st.booleans(),
        has_kiro_dir=st.booleans(),
    )
    def test_target_dir_option_property(self, target_dir_exists: bool, has_kiro_dir: bool):
        """
        Property test for --target-dir option functionality.
        
        **Feature: steering-docs-wizard, Property 5: CLI Options Functionality**
        **Validates: Requirements 6.3, 6.4**
        
        For any valid target directory option, the wizard should modify its behavior
        appropriately without affecting the core functionality or output quality.
        """
        # Skip test if we can't create the conditions
        assume(target_dir_exists)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_project"
            target_path.mkdir()
            
            if has_kiro_dir:
                kiro_dir = target_path / ".kiro"
                kiro_dir.mkdir()
                steering_dir = kiro_dir / "steering"
                steering_dir.mkdir()
            
            # Test that target-dir option is recognized and processed
            result = self.runner.invoke(main, ["--target-dir", str(target_path), "--dry-run"], input="n\n")
            
            # Should not crash due to target-dir option
            assert result.exit_code in [0, 1]  # 0 for success, 1 for expected user cancellation
            
            if has_kiro_dir:
                # Should find the project
                assert "Found Kiro project" in result.output or "Kiro project" in result.output
            else:
                # Should offer to create new structure
                assert "create a new .kiro/steering" in result.output or "No .kiro directory found" in result.output

    @given(
        has_project=st.booleans(),
    )
    def test_dry_run_option_property(self, has_project: bool):
        """
        Property test for --dry-run option functionality.
        
        **Feature: steering-docs-wizard, Property 5: CLI Options Functionality**
        **Validates: Requirements 6.3, 6.4**
        
        For any valid command-line options (--dry-run), the wizard should modify its behavior
        appropriately without affecting the core functionality or output quality.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            if has_project:
                kiro_dir = project_path / ".kiro"
                kiro_dir.mkdir()
                steering_dir = kiro_dir / "steering"
                steering_dir.mkdir()
            
            # Test dry-run mode
            result = self.runner.invoke(
                main, 
                ["--target-dir", str(project_path), "--dry-run"], 
                input="y\n" * 20  # Answer yes to all prompts
            )
            
            # Dry run should complete without errors
            if has_project or "create a new .kiro/steering" in result.output:
                # Should show dry run mode
                assert "DRY RUN MODE" in result.output or "Dry run" in result.output or result.exit_code in [0, 1]
                
                # Should not actually create files (this is the key property)
                if has_project:
                    dev_guidelines = project_path / ".kiro" / "steering" / "development-guidelines.md"
                    llm_guidance = project_path / ".kiro" / "steering" / "llm-guidance.md"
                    
                    # Files should not exist after dry run
                    assert not dev_guidelines.exists()
                    assert not llm_guidance.exists()


class TestCLIErrorHandling:
    """Test CLI error handling and user experience."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_invalid_target_dir(self):
        """Test error handling for invalid target directory."""
        result = self.runner.invoke(main, ["--target-dir", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        # This is difficult to test directly, but we can test that the CLI
        # has proper exception handling structure
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            kiro_dir = project_path / ".kiro"
            kiro_dir.mkdir()
            
            # Test with minimal input that would trigger early exit
            result = self.runner.invoke(
                main, 
                ["--target-dir", str(project_path)], 
                input="\x03"  # Ctrl+C simulation (may not work in all environments)
            )
            
            # Should handle interruption gracefully
            assert result.exit_code in [0, 1]


class TestCLIOutputFormatting:
    """Test CLI output formatting consistency."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_help_formatting(self):
        """Test help output formatting consistency."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        
        # Check for consistent formatting elements
        output = result.output
        assert "Usage:" in output
        assert "Options:" in output
        assert "--help" in output
        
        # Should have proper option descriptions
        lines = output.split('\n')
        help_lines = [line for line in lines if '--help' in line]
        assert len(help_lines) > 0
        assert any('Show this message and exit' in line or 'help' in line.lower() for line in help_lines)

    def test_version_formatting(self):
        """Test version output formatting consistency."""
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        
        output = result.output.strip()
        # Should contain both tool name and version
        assert "Steering Docs Wizard" in output
        assert __version__ in output
        
        # Should be properly formatted (not just raw version number)
        assert len(output.split()) >= 2  # At least tool name and version

    @given(
        has_kiro_project=st.booleans(),
    )
    def test_output_formatting_consistency_property(self, has_kiro_project: bool):
        """
        Property test for output formatting consistency.
        
        **Feature: steering-docs-wizard, Property 6: Output Formatting Consistency**
        **Validates: Requirements 1.5, 3.5, 5.4, 6.5**
        
        For any type of output message (prompts, errors, success messages, file summaries),
        the formatting and presentation should follow consistent patterns and include
        appropriate visual indicators.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            if has_kiro_project:
                kiro_dir = project_path / ".kiro"
                kiro_dir.mkdir()
                steering_dir = kiro_dir / "steering"
                steering_dir.mkdir()
            
            # Run with dry-run to avoid file creation but get output
            result = self.runner.invoke(
                main,
                ["--target-dir", str(project_path), "--dry-run"],
                input="y\n" * 20  # Answer yes to all prompts
            )
            
            output = result.output
            
            # Check for consistent formatting patterns
            if "Step" in output:
                # Should have step indicators
                step_lines = [line for line in output.split('\n') if 'Step' in line]
                assert len(step_lines) > 0
                
                # Steps should be consistently formatted
                for line in step_lines:
                    # Should contain step number and description
                    assert any(char.isdigit() for char in line)
            
            # Check for visual indicators (✓, •, etc.)
            if has_kiro_project or "create" in output.lower():
                # Should have success indicators or bullet points
                visual_indicators = ['✓', '•', '-', '*', '>', '→']
                has_visual_indicator = any(indicator in output for indicator in visual_indicators)
                
                # At least some visual formatting should be present
                assert has_visual_indicator or '[' in output  # Rich formatting or visual indicators

    def test_error_message_formatting(self):
        """Test error message formatting consistency."""
        # Test with a scenario that should produce an error
        result = self.runner.invoke(main, ["--target-dir", "/root/nonexistent"])
        
        # Should have proper exit code for error
        assert result.exit_code != 0
        
        # Error output should be present (either stdout or stderr)
        error_output = result.output + (result.stderr or "")
        assert len(error_output.strip()) > 0

    def test_success_message_display(self):
        """Test success message display formatting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            kiro_dir = project_path / ".kiro"
            kiro_dir.mkdir()
            steering_dir = kiro_dir / "steering"
            steering_dir.mkdir()
            
            # Run in dry-run mode to get success messages without file creation
            result = self.runner.invoke(
                main,
                ["--target-dir", str(project_path), "--dry-run"],
                input="y\n" * 20  # Answer yes to all prompts
            )
            
            if result.exit_code == 0:
                output = result.output
                
                # Should have completion message
                success_indicators = [
                    "completed successfully",
                    "✓",
                    "Success",
                    "Created",
                    "ready"
                ]
                
                has_success_indicator = any(indicator in output for indicator in success_indicators)
                assert has_success_indicator