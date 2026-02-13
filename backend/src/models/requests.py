"""Pydantic request models for type-safe API validation."""

from pathlib import Path
from pydantic import BaseModel, Field, field_validator


class TranscribeRequest(BaseModel):
    """Request model for video transcription."""

    file_path: str = Field(..., description="Absolute path to video file")
    model_size: str = Field("turbo", description="Whisper model size")
    language: str | None = Field(None, description="Override language detection")
    beam_size: int = Field(5, ge=1, le=10, description="Beam size for decoding")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate that file path exists and is a file."""
        path = Path(v).resolve()
        if not path.exists():
            raise ValueError(f"File not found: {v}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {v}")
        return str(path)

    @field_validator("model_size")
    @classmethod
    def validate_model_size(cls, v: str) -> str:
        """Validate model size is one of allowed values."""
        allowed = ["tiny", "base", "small", "medium", "large-v2", "turbo"]
        if v not in allowed:
            raise ValueError(f"Invalid model size. Must be one of: {allowed}")
        return v

    model_config = {"json_schema_extra": {"example": {"file_path": "/path/to/video.mp4", "model_size": "turbo", "language": None, "beam_size": 5}}}
