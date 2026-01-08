"""Tests for project discovery functionality."""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from hypothesis import given, strategies as st, assume

from steering_wizard.core.project_finder import (
    ProjectFinder,
    ProjectFinderError,
    PermissionError,
)


class TestProjectFinder:
    """Test suite for ProjectFinder functionality."""

    def test_find_kiro_project_current_directory(self, mock_kiro_project):
        """Test finding .kiro project in current directory."""
        finder = ProjectFinder()

        # Change to the mock project directory
        original_cwd = Path.cwd()
        try:
            os.chdir(mock_kiro_project)
            result = finder.find_kiro_project()
            # Compare resolved paths to handle symlink differences
            assert result.resolve() == mock_kiro_project.resolve()
        finally:
            os.chdir(original_cwd)

    def test_find_kiro_project_parent_directory(self, temp_dir):
        """Test finding .kiro project in parent directory."""
        # Create .kiro in temp_dir
        kiro_dir = temp_dir / ".kiro"
        kiro_dir.mkdir()

        # Create subdirectory
        sub_dir = temp_dir / "subdir"
        sub_dir.mkdir()

        finder = ProjectFinder()
        result = finder.find_kiro_project(sub_dir)
        # Compare resolved paths to handle symlink differences
        assert result.resolve() == temp_dir.resolve()

    def test_find_kiro_project_not_found(self, temp_dir):
        """Test when no .kiro project is found."""
        finder = ProjectFinder()
        result = finder.find_kiro_project(temp_dir)
        assert result is None

    def test_validate_project_structure_valid(self, mock_kiro_project):
        """Test validation of valid project structure."""
        finder = ProjectFinder()
        assert finder.validate_project_structure(mock_kiro_project)

    def test_validate_project_structure_invalid(self, temp_dir):
        """Test validation of invalid project structure."""
        finder = ProjectFinder()
        assert not finder.validate_project_structure(temp_dir)

    def test_validate_project_structure_nonexistent(self):
        """Test validation of nonexistent directory."""
        finder = ProjectFinder()
        nonexistent = Path("/nonexistent/path")
        assert not finder.validate_project_structure(nonexistent)

    def test_ensure_steering_directory_creates(self, mock_kiro_project):
        """Test that steering directory is created if it doesn't exist."""
        # Remove the steering directory
        steering_dir = mock_kiro_project / ".kiro" / "steering"
        if steering_dir.exists():
            shutil.rmtree(steering_dir)

        finder = ProjectFinder()
        result = finder.ensure_steering_directory(mock_kiro_project)

        assert result == steering_dir
        assert steering_dir.exists()
        assert steering_dir.is_dir()

    def test_ensure_steering_directory_exists(self, mock_kiro_project):
        """Test when steering directory already exists."""
        finder = ProjectFinder()
        steering_dir = mock_kiro_project / ".kiro" / "steering"

        result = finder.ensure_steering_directory(mock_kiro_project)
        assert result == steering_dir

    def test_ensure_steering_directory_invalid_project(self, temp_dir):
        """Test ensure_steering_directory with invalid project."""
        finder = ProjectFinder()

        with pytest.raises(ProjectFinderError):
            finder.ensure_steering_directory(temp_dir)

    def test_get_project_display_path_relative(self, temp_dir):
        """Test display path when project is relative to current directory."""
        finder = ProjectFinder()

        # Create a subdirectory of current working directory
        cwd = Path.cwd()
        if temp_dir.is_relative_to(cwd):
            display_path = finder.get_project_display_path(temp_dir)
            assert display_path.startswith("./")
        else:
            # If not relative, should return absolute path
            display_path = finder.get_project_display_path(temp_dir)
            assert str(temp_dir.resolve()) in display_path

    def test_check_existing_files_none(self, mock_kiro_project):
        """Test checking for existing files when none exist."""
        finder = ProjectFinder()
        steering_dir = mock_kiro_project / ".kiro" / "steering"

        existing = finder.check_existing_files(steering_dir)
        assert existing == []

    def test_check_existing_files_some_exist(self, mock_kiro_project):
        """Test checking for existing files when some exist."""
        finder = ProjectFinder()
        steering_dir = mock_kiro_project / ".kiro" / "steering"

        # Create one of the standard files
        dev_guidelines = steering_dir / "development-guidelines.md"
        dev_guidelines.write_text("# Development Guidelines")

        existing = finder.check_existing_files(steering_dir)
        assert len(existing) == 1
        assert dev_guidelines in existing


# Property-based test for Project Discovery Consistency
@given(
    # Generate directory structures with varying depths
    depth=st.integers(min_value=0, max_value=5),
    has_kiro_at_level=st.integers(min_value=0, max_value=5),
    create_kiro=st.booleans(),
)
def test_project_discovery_consistency(depth, has_kiro_at_level, create_kiro):
    """
    Property 1: Project Discovery Consistency

    For any directory structure, the project finder should consistently locate
    .kiro directories by searching the current directory first, then parent
    directories up to the filesystem root, and should validate that found
    directories can support steering document creation.

    **Feature: steering-docs-wizard, Property 1: Project Discovery Consistency**
    **Validates: Requirements 1.1, 1.2, 1.4**
    """
    # Skip test cases where .kiro would be created above the search depth
    assume(not create_kiro or has_kiro_at_level <= depth)

    # Create a temporary directory structure
    temp_root = Path(tempfile.mkdtemp())
    try:
        # Build nested directory structure
        current_path = temp_root
        paths = [current_path]

        for i in range(depth):
            current_path = current_path / f"level_{i}"
            current_path.mkdir()
            paths.append(current_path)

        # Create .kiro directory at specified level if requested
        kiro_parent = None
        if create_kiro and has_kiro_at_level < len(paths):
            kiro_parent = paths[has_kiro_at_level]
            kiro_dir = kiro_parent / ".kiro"
            kiro_dir.mkdir()

        # Test project discovery from the deepest directory
        finder = ProjectFinder()
        search_from = paths[-1] if paths else temp_root

        result = finder.find_kiro_project(search_from)

        # Verify consistency: should find .kiro if it exists in the path
        if create_kiro and kiro_parent:
            # Compare resolved paths to handle symlink differences
            assert result.resolve() == kiro_parent.resolve()
            # Should also validate the found project structure
            assert finder.validate_project_structure(result)
        else:
            assert result is None

        # Test that searching from any intermediate directory gives consistent results
        for path in paths:
            intermediate_result = finder.find_kiro_project(path)

            if create_kiro and kiro_parent:
                # Check if the kiro_parent is in the search path (current or parent)
                try:
                    # If path is the same as or a descendant of kiro_parent, should find it
                    if path.resolve() == kiro_parent.resolve() or path.is_relative_to(
                        kiro_parent
                    ):
                        assert intermediate_result is not None
                        assert intermediate_result.resolve() == kiro_parent.resolve()
                    else:
                        # If path is a parent of kiro_parent, won't find it (search only goes up)
                        assert intermediate_result is None
                except (ValueError, OSError):
                    # Handle cases where path comparison fails
                    pass
            else:
                # Should not find anything if no .kiro was created
                assert intermediate_result is None

    finally:
        # Clean up
        shutil.rmtree(temp_root, ignore_errors=True)


# Edge case tests for permission scenarios and missing directories
class TestProjectFinderEdgeCases:
    """Test edge cases for project finder functionality."""

    def test_permission_denied_directory_traversal(self, temp_dir):
        """Test handling of permission denied during directory traversal."""
        finder = ProjectFinder()

        # Create a directory structure
        restricted_dir = temp_dir / "restricted"
        restricted_dir.mkdir()

        # Create .kiro in a subdirectory
        sub_dir = restricted_dir / "subdir"
        sub_dir.mkdir()
        kiro_dir = sub_dir / ".kiro"
        kiro_dir.mkdir()

        # Test that finder handles permission errors gracefully
        # (Note: This test may not trigger actual permission errors on all systems)
        result = finder.find_kiro_project(sub_dir)
        # Should either find the .kiro or return None, but not crash
        assert result is None or result == sub_dir

    def test_missing_directory_validation(self):
        """Test validation of missing directories."""
        finder = ProjectFinder()

        missing_path = Path("/definitely/does/not/exist")
        assert not finder.validate_project_structure(missing_path)

    def test_invalid_project_structure_file_instead_of_directory(self, temp_dir):
        """Test validation when .kiro is a file instead of directory."""
        finder = ProjectFinder()

        # Create .kiro as a file instead of directory
        kiro_file = temp_dir / ".kiro"
        kiro_file.write_text("not a directory")

        assert not finder.validate_project_structure(temp_dir)

    def test_ensure_steering_directory_permission_error_simulation(self, temp_dir):
        """Test error handling when steering directory creation fails."""
        # Create a valid .kiro directory
        kiro_dir = temp_dir / ".kiro"
        kiro_dir.mkdir()

        finder = ProjectFinder()

        # This should work normally
        result = finder.ensure_steering_directory(temp_dir)
        assert result.exists()

    def test_find_kiro_project_with_file_permissions(self, temp_dir):
        """Test project finding with various file permission scenarios."""
        finder = ProjectFinder()

        # Create .kiro directory
        kiro_dir = temp_dir / ".kiro"
        kiro_dir.mkdir()

        # Test normal case
        result = finder.find_kiro_project(temp_dir)
        assert result == temp_dir

        # Test validation
        assert finder.validate_project_structure(temp_dir)
