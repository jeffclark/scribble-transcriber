"""Core transcription service integrating GPU, audio, and output handling."""

import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from ..models.responses import TranscribeResponse, TranscriptionMetadata, TranscriptionSegment
from ..utils.validation import VideoValidationError, validate_video_path
from .audio_processor import AudioExtractionError, extract_audio, get_video_duration, validate_audio_track
from .gpu_manager import GPUManager

logger = logging.getLogger(__name__)


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
        file_path: str,
        model_size: str = "turbo",
        language: Optional[str] = None,
        beam_size: int = 5,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> TranscribeResponse:
        """
        Transcribe a video file and return structured results.

        Args:
            file_path: Path to video file
            model_size: Whisper model size (tiny, base, small, medium, large-v2, turbo)
            language: Optional language code (None for auto-detection)
            beam_size: Beam size for decoding (1-10, default 5)
            progress_callback: Optional callback for progress updates

        Returns:
            TranscribeResponse: Complete transcription with metadata and output files

        Raises:
            VideoValidationError: If file validation fails
            AudioExtractionError: If audio extraction fails
            RuntimeError: If transcription fails
        """
        logger.info(f"Starting transcription for: {file_path}")

        # Helper to emit progress
        def emit_progress(stage: str, progress: int, message: str, **extra):
            # Log progress to console/file for debugging
            logger.info(f"📊 Progress: {progress}% - {message} (stage: {stage})")

            if progress_callback:
                progress_callback({
                    "stage": stage,
                    "progress": progress,
                    "message": message,
                    **extra
                })

        # 1. Validate video file path (security checks)
        emit_progress("validating", 0, "Validating video file...")
        try:
            video_path = validate_video_path(file_path)
        except VideoValidationError as e:
            logger.error(f"Validation failed: {e}")
            raise

        # 2. Check for audio track
        emit_progress("validating", 5, "Checking audio track...")
        if not validate_audio_track(video_path):
            raise AudioExtractionError(f"Video file has no audio track: {video_path.name}")

        # 3. Extract audio
        emit_progress("extracting", 5, "Extracting audio...")
        try:
            audio_data = extract_audio(video_path)
            emit_progress("extracting", 10, f"Audio extracted: {len(audio_data)} bytes")
        except AudioExtractionError as e:
            logger.error(f"Audio extraction failed: {e}")
            raise

        # 4. Get model
        emit_progress("loading", 10, f"Loading {model_size} model...")
        try:
            model = self.gpu_manager.get_model(model_size)
            emit_progress("loading", 20, "Model loaded successfully")
        except RuntimeError as e:
            logger.error(f"Failed to load model: {e}")
            raise

        # 5. Transcribe with incremental progress
        emit_progress("transcribing", 20, "Starting transcription...")

        try:
            logger.info(f"Transcribing with {model_size} model, beam_size={beam_size}")

            # Save audio to temp file for faster-whisper
            # (faster-whisper expects file path, not bytes)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name

            try:
                segments_gen, info = model.transcribe(
                    temp_audio_path,
                    beam_size=beam_size,
                    vad_filter=True,  # Voice Activity Detection for better accuracy
                    language=language,
                )

                # CRITICAL: Process segments incrementally instead of list()
                segments_list = []
                segment_count = 0

                # Get estimated duration for progress calculation
                try:
                    duration = get_video_duration(video_path)
                except AudioExtractionError:
                    duration = None

                # Estimate total segments based on duration
                # Whisper typically creates segments of 5-8 seconds, use 7 as average
                estimated_total_segments = int(duration / 7) if duration else None

                for segment in segments_gen:
                    segments_list.append(segment)
                    segment_count += 1

                    # Report progress every 5 segments
                    if segment_count % 5 == 0:
                        # Progress from 20% to 95% based on time
                        if duration:
                            progress = min(20 + int((segment.end / duration) * 75), 95)
                        else:
                            # Fallback: estimate based on segment count
                            progress = min(20 + (segment_count * 2), 95)

                        emit_progress(
                            "transcribing",
                            progress,
                            f"Transcribing: {segment_count} segments processed",
                            segment_count=segment_count,
                            estimated_total_segments=estimated_total_segments,
                            current_time=segment.end
                        )

                emit_progress(
                    "transcribing",
                    90,
                    f"Transcription complete: {len(segments_list)} segments",
                    segment_count=len(segments_list),
                    estimated_total_segments=len(segments_list)  # Now we know the actual total
                )

                logger.info(
                    f"Transcription complete: {len(segments_list)} segments, "
                    f"language={info.language} (prob={info.language_probability:.2f})"
                )

            finally:
                # Cleanup temp audio file
                Path(temp_audio_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}")

        finally:
            # CRITICAL: Cleanup GPU memory after transcription
            # Fixes 300MB memory leak per transcription
            self.gpu_manager.cleanup_after_transcription()

        # 6. Get video duration (if not already obtained)
        if duration is None:
            try:
                duration = get_video_duration(video_path)
            except AudioExtractionError:
                # If duration probe fails, estimate from last segment
                duration = segments_list[-1].end if segments_list else 0.0

        # 7. Format outputs
        device_info = self.gpu_manager.get_device_info()

        metadata = TranscriptionMetadata(
            source_file=video_path.name,
            transcription_date=datetime.now(timezone.utc).isoformat(),
            model=model_size,
            device=device_info["device"],
            language=info.language,
            language_probability=float(info.language_probability),
            duration_seconds=float(duration),
        )

        transcription_segments = [
            TranscriptionSegment(id=i, start=float(seg.start), end=float(seg.end), text=seg.text.strip())
            for i, seg in enumerate(segments_list)
        ]

        # 8. Save output files
        emit_progress("saving", 95, "Saving output files...")
        output_files = self._save_outputs(video_path, metadata, transcription_segments)

        # Note: Don't send "completed" stage here - it's sent from main.py with full result
        # This prevents frontend from receiving incomplete completion messages

        return TranscribeResponse(metadata=metadata, segments=transcription_segments, output_files=output_files)

    def _save_outputs(
        self, video_path: Path, metadata: TranscriptionMetadata, segments: list
    ) -> dict:
        """
        Save transcription outputs in JSON and plain text formats.

        Files are saved in same directory as source video:
        - video_transcript.json
        - video_transcript.txt

        Args:
            video_path: Path to source video
            metadata: Transcription metadata
            segments: List of transcription segments

        Returns:
            dict: Paths to output files {"json": "...", "txt": "..."}
        """
        base_name = video_path.stem
        output_dir = video_path.parent

        # Generate output paths with conflict resolution
        json_path = self._get_unique_path(output_dir / f"{base_name}_transcript.json")
        txt_path = self._get_unique_path(output_dir / f"{base_name}_transcript.txt")

        # Save JSON
        json_output = {"metadata": metadata.model_dump(), "segments": [seg.model_dump() for seg in segments]}

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved JSON output: {json_path}")

        # Save plain text
        txt_output = "\n".join(seg.text for seg in segments)

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
