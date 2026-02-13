"""Validation utilities for secure file path handling."""

from pathlib import Path

# Allowed video file extensions
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".m4v"}

# Sensitive system directories that should never be accessed
SENSITIVE_PATHS = [
    Path("/etc"),
    Path("/sys"),
    Path("/proc"),
    Path("/dev"),
    Path("/boot"),
    Path("/root"),
]


class VideoValidationError(Exception):
    """Raised when video file validation fails."""

    pass


def validate_video_path(file_path: str) -> Path:
    """
    Validate and sanitize user-provided video path.

    This function prevents:
    - Path traversal attacks (../ sequences)
    - Symlink attacks (resolves to real path)
    - Access to sensitive system directories
    - Invalid file types
    - Non-existent files

    Args:
        file_path: User-provided path to video file

    Returns:
        Path: Validated and resolved absolute path

    Raises:
        VideoValidationError: If validation fails
    """
    try:
        # Resolve to absolute path (follows symlinks, resolves .. and .)
        path = Path(file_path).resolve()
    except (RuntimeError, OSError) as e:
        raise VideoValidationError(f"Invalid file path: {e}")

    # Check file exists
    if not path.exists():
        raise VideoValidationError(f"File does not exist: {path}")

    # Check it's a file (not directory)
    if not path.is_file():
        raise VideoValidationError(f"Path is not a file: {path}")

    # Check extension
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise VideoValidationError(
            f"Unsupported file type: {path.suffix}. " f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Prevent reading from sensitive system directories
    for sensitive in SENSITIVE_PATHS:
        try:
            # is_relative_to() checks if path is under sensitive directory
            if path.is_relative_to(sensitive):
                raise VideoValidationError(f"Cannot process files from system directories: {sensitive}")
        except ValueError:
            # is_relative_to() raises ValueError if paths have different drive letters (Windows)
            continue

    return path


def validate_output_directory(output_dir: str) -> Path:
    """
    Validate that output directory exists and is writable.

    Args:
        output_dir: Path to output directory

    Returns:
        Path: Validated absolute path to directory

    Raises:
        VideoValidationError: If directory doesn't exist or isn't writable
    """
    try:
        path = Path(output_dir).resolve()
    except (RuntimeError, OSError) as e:
        raise VideoValidationError(f"Invalid directory path: {e}")

    if not path.exists():
        raise VideoValidationError(f"Directory does not exist: {path}")

    if not path.is_dir():
        raise VideoValidationError(f"Path is not a directory: {path}")

    # Check if writable by attempting to create a temp file
    test_file = path / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
    except OSError:
        raise VideoValidationError(f"Directory is not writable: {path}")

    return path
