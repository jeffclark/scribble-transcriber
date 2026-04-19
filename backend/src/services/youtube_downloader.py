"""YouTube audio download service using yt-dlp."""

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|embed/)|youtu\.be/)"
    r"[A-Za-z0-9_-]{11}"
)


class YoutubeDownloadError(Exception):
    """Raised when a YouTube download or info fetch fails."""


def is_valid_youtube_url(url: str) -> bool:
    """Return True if url looks like a YouTube video URL."""
    return bool(YOUTUBE_URL_PATTERN.match(url.strip()))


def fetch_youtube_info(url: str) -> dict:
    """
    Fetch metadata for a YouTube video without downloading it.

    Args:
        url: YouTube video URL

    Returns:
        dict with keys: title, video_id, duration, uploader

    Raises:
        YoutubeDownloadError: If the URL is invalid or info fetch fails
    """
    if not is_valid_youtube_url(url):
        raise YoutubeDownloadError(f"Not a valid YouTube URL: {url}")

    try:
        import yt_dlp  # noqa: PLC0415

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "title": info.get("title", "Unknown title"),
            "video_id": info.get("id", ""),
            "duration": float(info.get("duration") or 0),
            "uploader": info.get("uploader") or info.get("channel") or "",
        }

    except YoutubeDownloadError:
        raise
    except Exception as e:
        raise YoutubeDownloadError(f"Failed to fetch video info: {e}") from e


def download_youtube_audio(
    url: str,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> tuple[Path, dict]:
    """
    Download the best audio stream from a YouTube URL to a temporary file.

    The caller is responsible for deleting the returned file after use.

    Args:
        url: YouTube video URL
        progress_callback: Optional callback receiving progress dicts:
            {"stage": "downloading", "progress": int, "message": str}

    Returns:
        (temp_audio_path, info_dict) — path to downloaded audio file and video metadata

    Raises:
        YoutubeDownloadError: If download fails
    """
    if not is_valid_youtube_url(url):
        raise YoutubeDownloadError(f"Not a valid YouTube URL: {url}")

    try:
        import yt_dlp  # noqa: PLC0415
        from .audio_processor import get_ffmpeg_path  # noqa: PLC0415
    except ImportError as e:
        raise YoutubeDownloadError(f"yt-dlp is not installed: {e}") from e

    # Create a temp file; yt-dlp will replace it with the downloaded audio
    fd, temp_base = tempfile.mkstemp(prefix="yt_audio_", dir=tempfile.gettempdir())
    os.close(fd)
    # Remove the empty file — yt-dlp will create <temp_base>.<ext>
    os.unlink(temp_base)

    def _progress_hook(d: dict) -> None:
        if progress_callback is None:
            return
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                pct = int(2 + (downloaded / total) * 13)  # map 0-100% → 2-15
            else:
                pct = 2
            speed = d.get("_speed_str", "").strip()
            msg = f"Downloading audio... {speed}" if speed else "Downloading audio..."
            progress_callback({"stage": "downloading", "progress": pct, "message": msg})
        elif status == "finished":
            progress_callback({"stage": "downloading", "progress": 15, "message": "Download complete, preparing audio..."})

    ydl_opts = {
        "format": "bestaudio/best",
        # Use Android client to bypass YouTube's SABR streaming 403 blocks
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
        "outtmpl": temp_base + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ffmpeg_location": get_ffmpeg_path(),
        "progress_hooks": [_progress_hook],
        # Don't post-process — we'll convert with our own extract_audio()
        "postprocessors": [],
    }

    if progress_callback:
        progress_callback({"stage": "downloading", "progress": 2, "message": "Connecting to YouTube..."})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        # Clean up any partial files
        for f in Path(tempfile.gettempdir()).glob(f"{Path(temp_base).name}.*"):
            f.unlink(missing_ok=True)
        raise YoutubeDownloadError(f"Download failed: {e}") from e

    # Find the downloaded file (yt-dlp picked the extension)
    downloaded_files = list(Path(tempfile.gettempdir()).glob(f"{Path(temp_base).name}.*"))
    if not downloaded_files:
        raise YoutubeDownloadError("Download completed but no output file found")

    audio_path = downloaded_files[0]
    logger.info(f"Downloaded YouTube audio to: {audio_path} ({audio_path.stat().st_size} bytes)")

    video_info = {
        "title": info.get("title", "Unknown title"),
        "video_id": info.get("id", ""),
        "duration": float(info.get("duration") or 0),
        "uploader": info.get("uploader") or info.get("channel") or "",
    }

    return audio_path, video_info
