"""Core transcription service integrating GPU, audio, and output handling."""

import json
import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from ..models.responses import TranscribeResponse, TranscriptionMetadata, TranscriptionSegment
from ..utils.validation import VideoValidationError, validate_video_path
from .audio_processor import AudioExtractionError, extract_audio, get_video_duration, validate_audio_track
from .gpu_manager import GPUManager
from .youtube_downloader import YoutubeDownloadError, download_youtube_audio

logger = logging.getLogger(__name__)

_UNSAFE_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|]')


def _sanitize_filename(title: str) -> str:
    """Replace filesystem-unsafe characters and trim the result."""
    sanitized = _UNSAFE_FILENAME_CHARS.sub("_", title)
    return sanitized.strip(". ")[:200] or "youtube_video"


class TranscriptionService:
    """
    Core transcription service orchestrating the full pipeline:
    1. Validate video file
    2. Extract audio
    3. Transcribe with Whisper
    4. Format and save outputs
    5. Cleanup GPU memory
    """

    def __init__(self):
        self.gpu_manager = GPUManager()
        self._initialized = False

    async def initialize(self):
        """Initialize GPU manager and detect device."""
        await self.gpu_manager.initialize()
        self._initialized = True
        logger.info("TranscriptionService initialized")

    async def cleanup(self):
        """Cleanup GPU resources."""
        self.gpu_manager.cleanup()
        logger.info("TranscriptionService cleanup complete")

    def is_ready(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    async def transcribe(
        self,
        file_path: Optional[str] = None,
        youtube_url: Optional[str] = None,
        model_size: str = "turbo",
        language: Optional[str] = None,
        beam_size: int = 5,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> TranscribeResponse:
        """
        Transcribe a video file or YouTube URL and return structured results.

        Args:
            file_path: Path to local video file (mutually exclusive with youtube_url)
            youtube_url: YouTube URL to download and transcribe (mutually exclusive with file_path)
            model_size: Whisper model size (tiny, base, small, medium, large-v2, turbo)
            language: Optional language code (None for auto-detection)
            beam_size: Beam size for decoding (1-10, default 5)
            progress_callback: Optional callback for progress updates

        Returns:
            TranscribeResponse: Complete transcription with metadata and output files

        Raises:
            VideoValidationError: If file validation fails
            AudioExtractionError: If audio extraction fails
            YoutubeDownloadError: If YouTube download fails
            RuntimeError: If transcription fails
        """
        source = file_path or youtube_url
        logger.info(f"Starting transcription for: {source}")

        # Helper to emit progress
        def emit_progress(stage: str, progress: int, message: str, **extra):
            logger.info(f"📊 Progress: {progress}% - {message} (stage: {stage})")
            if progress_callback:
                progress_callback({"stage": stage, "progress": progress, "message": message, **extra})

        # --- Phase 1: Source setup ---
        # Result: audio_data (bytes), source_name (str), duration (float|None), output_dir (Path), base_name (str)

        if youtube_url:
            # YouTube flow: download audio, convert to PCM WAV via extract_audio()
            yt_temp_path: Optional[Path] = None
            try:
                yt_temp_path, yt_info = download_youtube_audio(
                    youtube_url,
                    progress_callback=progress_callback,  # raw dict callback
                )
                audio_data = extract_audio(yt_temp_path)
                emit_progress("extracting", 16, f"Audio prepared: {len(audio_data)} bytes")
            except (YoutubeDownloadError, AudioExtractionError):
                raise
            except Exception as e:
                raise YoutubeDownloadError(f"Failed to prepare YouTube audio: {e}") from e
            finally:
                if yt_temp_path is not None:
                    yt_temp_path.unlink(missing_ok=True)

            source_name = _sanitize_filename(yt_info.get("title", "youtube_video"))
            base_name = source_name
            duration: Optional[float] = yt_info.get("duration") or None
            output_dir = Path.home() / "Downloads"

            emit_progress("loading", 18, f"Loading {model_size} model...")

        else:
            # Local file flow
            emit_progress("validating", 0, "Validating video file...")
            try:
                video_path = validate_video_path(file_path)
            except VideoValidationError as e:
                logger.error(f"Validation failed: {e}")
                raise

            emit_progress("validating", 5, "Checking audio track...")
            if not validate_audio_track(video_path):
                raise AudioExtractionError(f"Video file has no audio track: {video_path.name}")

            emit_progress("extracting", 5, "Extracting audio...")
            try:
                audio_data = extract_audio(video_path)
                emit_progress("extracting", 10, f"Audio extracted: {len(audio_data)} bytes")
            except AudioExtractionError as e:
                logger.error(f"Audio extraction failed: {e}")
                raise

            source_name = video_path.name
            base_name = video_path.stem
            duration = None  # will probe below
            output_dir = video_path.parent

            emit_progress("loading", 10, f"Loading {model_size} model...")

        # --- Phase 2: Load model ---
        try:
            model = self.gpu_manager.get_model(model_size)
            emit_progress("loading", 20, "Model loaded successfully")
        except RuntimeError as e:
            logger.error(f"Failed to load model: {e}")
            raise

        # --- Phase 3: Transcribe ---
        emit_progress("transcribing", 20, "Starting transcription...")

        try:
            logger.info(f"Transcribing with {model_size} model, beam_size={beam_size}")

            # Save audio to temp file for faster-whisper (expects file path, not bytes)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name

            try:
                segments_gen, info = model.transcribe(
                    temp_audio_path,
                    beam_size=beam_size,
                    vad_filter=True,
                    language=language,
                )

                segments_list = []
                segment_count = 0

                # For file-based flow, probe duration now if we don't have it
                if duration is None and not youtube_url:
                    try:
                        duration = get_video_duration(video_path)
                    except (AudioExtractionError, NameError):
                        duration = None

                estimated_total_segments = int(duration / 7) if duration else None

                for segment in segments_gen:
                    segments_list.append(segment)
                    segment_count += 1

                    if segment_count % 5 == 0:
                        if duration:
                            progress = min(20 + int((segment.end / duration) * 75), 95)
                        else:
                            progress = min(20 + (segment_count * 2), 95)

                        emit_progress(
                            "transcribing",
                            progress,
                            f"Transcribing: {segment_count} segments processed",
                            segment_count=segment_count,
                            estimated_total_segments=estimated_total_segments,
                            current_time=segment.end,
                        )

                emit_progress(
                    "transcribing",
                    90,
                    f"Transcription complete: {len(segments_list)} segments",
                    segment_count=len(segments_list),
                    estimated_total_segments=len(segments_list),
                )

                logger.info(
                    f"Transcription complete: {len(segments_list)} segments, "
                    f"language={info.language} (prob={info.language_probability:.2f})"
                )

            finally:
                Path(temp_audio_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}")

        finally:
            self.gpu_manager.cleanup_after_transcription()

        # --- Phase 3.5: Diarize ---
        emit_progress("diarizing", 90, "Identifying speakers...")
        try:
            from .diarization import diarize_segments
            speaker_labels = diarize_segments(audio_data, segments_list)
            logger.info(f"Diarization complete: {len(set(speaker_labels))} speaker(s) detected")
        except Exception as e:
            logger.warning(f"Diarization failed, skipping: {e}")
            speaker_labels = ["Speaker 1"] * len(segments_list)
        emit_progress("diarizing", 93, "Speakers identified")

        # --- Phase 4: Format and save ---
        if duration is None:
            duration = segments_list[-1].end if segments_list else 0.0

        device_info = self.gpu_manager.get_device_info()

        metadata = TranscriptionMetadata(
            source_file=source_name,
            transcription_date=datetime.now(timezone.utc).isoformat(),
            model=model_size,
            device=device_info["device"],
            language=info.language,
            language_probability=float(info.language_probability),
            duration_seconds=float(duration),
        )

        transcription_segments = [
            TranscriptionSegment(
                id=i,
                start=float(seg.start),
                end=float(seg.end),
                text=seg.text.strip(),
                speaker=speaker_labels[i],
            )
            for i, seg in enumerate(segments_list)
        ]

        emit_progress("saving", 95, "Saving output files...")
        output_files = self._save_outputs(output_dir, base_name, metadata, transcription_segments)

        return TranscribeResponse(metadata=metadata, segments=transcription_segments, output_files=output_files)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _save_outputs(
        self, output_dir: Path, base_name: str, metadata: TranscriptionMetadata, segments: list
    ) -> dict:
        """
        Save transcription outputs in JSON and plain text formats.

        Args:
            output_dir: Directory to save output files
            base_name: Filename stem to use for output files
            metadata: Transcription metadata
            segments: List of transcription segments

        Returns:
            dict: Paths to output files {"json": "...", "txt": "..."}
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate output paths with conflict resolution
        json_path = self._get_unique_path(output_dir / f"{base_name}_transcript.json")
        txt_path = self._get_unique_path(output_dir / f"{base_name}_transcript.txt")

        # Save JSON
        json_output = {"metadata": metadata.model_dump(), "segments": [seg.model_dump() for seg in segments]}

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved JSON output: {json_path}")

        # Save plain text with timestamps and speaker labels
        txt_output = "\n".join(
            f"[{self._format_timestamp(seg.start)}] {seg.speaker or 'Speaker 1'}: {seg.text}"
            for seg in segments
        )

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_output)

        logger.info(f"Saved text output: {txt_path}")

        return {"json": str(json_path), "txt": str(txt_path)}

    def _get_unique_path(self, path: Path) -> Path:
        """
        Generate unique file path by appending (1), (2), etc. if file exists.

        Args:
            path: Desired output path

        Returns:
            Path: Unique path that doesn't exist
        """
        if not path.exists():
            return path

        counter = 1
        while True:
            new_path = path.parent / f"{path.stem} ({counter}){path.suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
