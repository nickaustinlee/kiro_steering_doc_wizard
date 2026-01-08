"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
import tempfile
import shutil
from typing import Generator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_kiro_project(temp_dir: Path) -> Path:
    """Create a mock Kiro project structure for testing."""
    kiro_dir = temp_dir / ".kiro"
    kiro_dir.mkdir()
    steering_dir = kiro_dir / "steering"
    steering_dir.mkdir()
    return temp_dir
