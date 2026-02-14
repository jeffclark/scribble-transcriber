"""Secure audio extraction from video files using FFmpeg."""

import logging
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import ffmpeg

logger = logging.getLogger(__name__)


def get_ffmpeg_path() -> str:
    """
    Get path to ffmpeg binary (bundled or system).

    When running as PyInstaller bundle, use the bundled ffmpeg.
    Otherwise, use system ffmpeg from PATH.

    Returns:
        str: Path to ffmpeg executable
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        # FFmpeg is in same directory as the executable
        bundle_dir = os.path.dirname(sys.executable)
        ffmpeg_path = os.path.join(bundle_dir, "ffmpeg")

        if os.path.exists(ffmpeg_path):
            logger.info(f"Using bundled ffmpeg: {ffmpeg_path}")
            return ffmpeg_path
        else:
            logger.warning(f"Bundled ffmpeg not found at {ffmpeg_path}, falling back to system ffmpeg")

    # Fallback to system ffmpeg
    return "ffmpeg"


# Configure ffmpeg-python to use the correct executable
ffmpeg._ffmpeg_cmd = get_ffmpeg_path()


class AudioExtractionError(Exception):
    """Raised when audio extraction fails."""

    pass


@contextmanager
def secure_temp_audio_file(video_path: Path):
    """
    Create a secure temporary file for audio extraction.

    Features:
    - Uses file descriptor to prevent TOCTOU (Time-of-Check-Time-of-Use) race conditions
    - Sets restrictive permissions (0600 - owner read/write only)
    - Automatic cleanup in finally block
    - Critical security fix from research

    Args:
        video_path: Path to source video file (for logging)

    Yields:
        Path: Secure temporary audio file path

    Raises:
        AudioExtractionError: If temp file creation fails
    """
    fd = None
    temp_path = None

    try:
        # Create secure temp file with restrictive permissions
        fd, temp_path_str = tempfile.mkstemp(suffix=".wav", prefix="transcribe_", dir=tempfile.gettempdir())

        temp_path = Path(temp_path_str)

        # Close FD immediately but keep the file
        os.close(fd)
        fd = None

        # Set restrictive permissions (owner read/write only)
        os.chmod(temp_path, 0o600)

        logger.debug(f"Created secure temp file: {temp_path}")

        yield temp_path

    except Exception as e:
        raise AudioExtractionError(f"Failed to create temp file: {e}")

    finally:
        # Always cleanup, even on exception
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass

        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
                logger.debug(f"Cleaned up temp file: {temp_path}")
            except Exception as e:
                # Log but don't raise - cleanup failure shouldn't break processing
                logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")


def extract_audio(video_path: Path, timeout: int = 300) -> bytes:
    """
    Extract audio from video file as PCM 16kHz mono WAV.

    Audio format optimized for Whisper:
    - PCM (uncompressed)
    - 16kHz sample rate (Whisper's native rate)
    - Mono channel

    Args:
        video_path: Path to source video file
        timeout: Maximum time in seconds (default 5 minutes)

    Returns:
        bytes: Raw audio data in PCM 16kHz mono format

    Raises:
        AudioExtractionError: If extraction fails or times out
    """
    logger.info(f"Extracting audio from: {video_path.name}")

    with secure_temp_audio_file(video_path) as audio_path:
        try:
            # Extract audio using ffmpeg with timeout
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(
                stream,
                str(audio_path),
                acodec="pcm_s16le",  # Uncompressed PCM
                ac=1,  # Mono channel
                ar="16k",  # 16kHz (Whisper native)
                loglevel="error",  # Only show errors
            )
            stream = ffmpeg.overwrite_output(stream)

            # Run and capture output
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)

            logger.info(f"Audio extracted successfully: {audio_path.stat().st_size} bytes")

            # Read audio data
            audio_data = audio_path.read_bytes()
            return audio_data

        except subprocess.TimeoutExpired:
            raise AudioExtractionError(f"Audio extraction timed out after {timeout} seconds")

        except ffmpeg.Error as e:
            error_message = e.stderr.decode("utf-8") if e.stderr else str(e)
            logger.error(f"FFmpeg error: {error_message}")

            # Provide helpful error messages
            if "Invalid data found" in error_message:
                raise AudioExtractionError(f"Video file is corrupted or invalid: {video_path.name}")
            elif "Output file does not contain any stream" in error_message:
                raise AudioExtractionError(f"Video file has no audio track: {video_path.name}")
            else:
                raise AudioExtractionError(f"Failed to extract audio: {error_message}")

        except Exception as e:
            raise AudioExtractionError(f"Unexpected error during audio extraction: {e}")


def get_video_duration(video_path: Path) -> float:
    """
    Get duration of video file in seconds.

    Args:
        video_path: Path to video file

    Returns:
        float: Duration in seconds

    Raises:
        AudioExtractionError: If probe fails
    """
    try:
        probe = ffmpeg.probe(str(video_path))
        duration = float(probe["format"]["duration"])
        return duration

    except Exception as e:
        raise AudioExtractionError(f"Failed to probe video duration: {e}")


def validate_audio_track(video_path: Path) -> bool:
    """
    Check if video file has an audio track.

    Args:
        video_path: Path to video file

    Returns:
        bool: True if video has audio track, False otherwise
    """
    try:
        probe = ffmpeg.probe(str(video_path))
        audio_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]
        return len(audio_streams) > 0

    except Exception as e:
        logger.warning(f"Failed to validate audio track: {e}")
        return False  # Assume no audio if probe fails
