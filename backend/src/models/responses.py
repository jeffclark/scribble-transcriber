"""Pydantic response models for type-safe API responses."""

from typing import Optional

from pydantic import BaseModel


class TranscriptionSegment(BaseModel):
    """A single segment of transcribed text with timestamps."""

    id: int
    start: float
    end: float
    text: str
    speaker: Optional[str] = None

    model_config = {"json_schema_extra": {"example": {"id": 0, "start": 0.0, "end": 3.5, "text": "Welcome to today's meeting.", "speaker": "Speaker 1"}}}


class TranscriptionMetadata(BaseModel):
    """Metadata about the transcription process and results."""

    source_file: str
    transcription_date: str
    model: str
    device: str
    language: str
    language_probability: float
    duration_seconds: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_file": "meeting.mp4",
                "transcription_date": "2026-02-13T14:30:00Z",
                "model": "turbo",
                "device": "cuda",
                "language": "en",
                "language_probability": 0.98,
                "duration_seconds": 3600.5,
            }
        }
    }


class TranscribeResponse(BaseModel):
    """Complete transcription response with metadata, segments, and output files."""

    metadata: TranscriptionMetadata
    segments: list[TranscriptionSegment]
    output_files: dict[str, str]

    model_config = {
        "json_schema_extra": {
            "example": {
                "metadata": {
                    "source_file": "meeting.mp4",
                    "transcription_date": "2026-02-13T14:30:00Z",
                    "model": "turbo",
                    "device": "cuda",
                    "language": "en",
                    "language_probability": 0.98,
                    "duration_seconds": 3600.5,
                },
                "segments": [{"id": 0, "start": 0.0, "end": 3.5, "text": "Welcome to today's meeting."}],
                "output_files": {"json": "/path/to/meeting_transcript.json", "txt": "/path/to/meeting_transcript.txt"},
            }
        }
    }
