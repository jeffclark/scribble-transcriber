"""Tests for path validation and security checks."""

import tempfile
from pathlib import Path

import pytest

from src.utils.validation import VideoValidationError, validate_video_path


def test_validate_video_path_success():
    """Test successful validation of valid video file."""
    # Create a temporary video file
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(b"fake video content")

    try:
        result = validate_video_path(str(temp_path))
        assert result == temp_path.resolve()
        assert result.is_file()
    finally:
        temp_path.unlink()


def test_validate_video_path_not_exists():
    """Test validation fails for non-existent file."""
    with pytest.raises(VideoValidationError, match="File does not exist"):
        validate_video_path("/nonexistent/video.mp4")


def test_validate_video_path_is_directory():
    """Test validation fails for directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with pytest.raises(VideoValidationError, match="Path is not a file"):
            validate_video_path(temp_dir)


def test_validate_video_path_invalid_extension():
    """Test validation fails for invalid file extension."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        with pytest.raises(VideoValidationError, match="Unsupported file type"):
            validate_video_path(str(temp_path))
    finally:
        temp_path.unlink()


def test_validate_video_path_system_directory():
    """Test validation prevents access to sensitive system directories."""
    # Try to access /etc/passwd (common on Unix-like systems)
    # Note: Will fail on extension check first, but still rejected
    etc_passwd = Path("/etc/passwd")
    if etc_passwd.exists():
        with pytest.raises(VideoValidationError):  # Either extension or system dir error
            validate_video_path(str(etc_passwd))


def test_validate_video_path_allowed_extensions():
    """Test all allowed video extensions pass validation."""
    allowed_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".m4v"]

    for ext in allowed_extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake video")

        try:
            result = validate_video_path(str(temp_path))
            assert result.suffix.lower() == ext
        finally:
            temp_path.unlink()
