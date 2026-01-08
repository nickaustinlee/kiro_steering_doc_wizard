"""Project discovery and validation functionality."""

import os
from pathlib import Path
from typing import Optional, List
import stat


class ProjectFinderError(Exception):
    """Base exception for project finder errors."""

    pass


class PermissionError(ProjectFinderError):
    """Raised when file system permissions prevent operations."""

    pass


class ProjectFinder:
    """Handles discovery and validation of Kiro project directories."""

    def find_kiro_project(self, start_path: Optional[Path] = None) -> Optional[Path]:
        """
        Find a Kiro project by searching for .kiro directory.

        Searches the current directory first, then parent directories up to
        the filesystem root.

        Args:
            start_path: Directory to start searching from. Defaults to current directory.

        Returns:
            Path to the directory containing .kiro folder, or None if not found.

        Requirements: 1.1, 1.2
        """
        if start_path is None:
            start_path = Path.cwd()

        # Use absolute path but don't resolve symlinks to avoid path comparison issues
        current_path = start_path.absolute()

        # Search current directory and parents up to filesystem root
        while True:
            kiro_path = current_path / ".kiro"

            try:
                if kiro_path.exists() and kiro_path.is_dir():
                    return current_path
            except PermissionError as e:
                # Continue searching if we can't access this directory
                pass

            # Check if we've reached the filesystem root
            parent = current_path.parent
            if parent == current_path:
                break
            current_path = parent

        return None

    def validate_project_structure(self, project_path: Path) -> bool:
        """
        Validate that a project has a proper Kiro structure.

        Args:
            project_path: Path to the project directory to validate.

        Returns:
            True if the project structure is valid, False otherwise.

        Requirements: 1.4
        """
        if not project_path.exists():
            return False

        if not project_path.is_dir():
            return False

        kiro_path = project_path / ".kiro"

        try:
            # Check if .kiro directory exists and is accessible
            if not kiro_path.exists():
                return False

            if not kiro_path.is_dir():
                return False

            # Check if we can read the .kiro directory
            if not os.access(kiro_path, os.R_OK):
                return False

            return True

        except (OSError, PermissionError):
            return False

    def ensure_steering_directory(self, project_path: Path) -> Path:
        """
        Ensure that the steering directory exists within the project.

        Creates .kiro/steering directory if it doesn't exist.

        Args:
            project_path: Path to the project directory.

        Returns:
            Path to the steering directory.

        Raises:
            PermissionError: If directory creation fails due to permissions.
            ProjectFinderError: If the project structure is invalid.

        Requirements: 1.3, 1.4, 5.1
        """
        if not self.validate_project_structure(project_path):
            raise ProjectFinderError(f"Invalid project structure at {project_path}")

        kiro_path = project_path / ".kiro"
        steering_path = kiro_path / "steering"

        try:
            # Create steering directory if it doesn't exist
            if not steering_path.exists():
                steering_path.mkdir(parents=True, exist_ok=True)

            # Verify we can write to the steering directory
            if not os.access(steering_path, os.W_OK):
                raise PermissionError(
                    f"Cannot write to steering directory: {steering_path}. "
                    f"Check permissions with: chmod u+w {steering_path}"
                )

            return steering_path

        except OSError as e:
            if e.errno == 13:  # Permission denied
                raise PermissionError(
                    f"Permission denied creating steering directory: {steering_path}. "
                    f"Try: sudo chmod u+w {kiro_path} or run with appropriate permissions."
                ) from e
            else:
                raise ProjectFinderError(
                    f"Failed to create steering directory: {e}"
                ) from e

    def get_project_display_path(self, project_path: Path) -> str:
        """
        Get a user-friendly display path for the project.

        Args:
            project_path: Path to the project directory.

        Returns:
            String representation of the path for display to user.

        Requirements: 1.5
        """
        try:
            # Try to get relative path from current directory
            relative_path = project_path.relative_to(Path.cwd())
            return f"./{relative_path}"
        except ValueError:
            # If not relative to current directory, return absolute path
            return str(project_path.resolve())

    def check_existing_files(self, steering_path: Path) -> list[Path]:
        """
        Check for existing steering files that might be overwritten.

        Args:
            steering_path: Path to the steering directory.

        Returns:
            List of existing steering files.

        Requirements: 3.4, 4.5
        """
        existing_files = []

        # Check for standard steering files
        standard_files = ["development-guidelines.md", "llm-guidance.md"]

        for filename in standard_files:
            file_path = steering_path / filename
            if file_path.exists():
                existing_files.append(file_path)

        return existing_files
