"""Pydantic request models for type-safe API validation."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class TranscribeRequest(BaseModel):
    """Request model for video transcription."""

    file_path: Optional[str] = Field(None, description="Absolute path to video file")
    youtube_url: Optional[str] = Field(None, description="YouTube URL to download and transcribe")
    model_size: str = Field("turbo", description="Whisper model size")
    language: Optional[str] = Field(None, description="Override language detection")
    beam_size: int = Field(5, ge=1, le=10, description="Beam size for decoding")

    @model_validator(mode="after")
    def validate_source(self) -> "TranscribeRequest":
        """Enforce exactly one of file_path or youtube_url."""
        has_file = bool(self.file_path)
        has_url = bool(self.youtube_url)
        if has_file == has_url:
            raise ValueError("Exactly one of file_path or youtube_url must be provided")
        if has_file:
            path = Path(self.file_path).resolve()
            if not path.exists():
                raise ValueError(f"File not found: {self.file_path}")
            if not path.is_file():
                raise ValueError(f"Path is not a file: {self.file_path}")
            self.file_path = str(path)
        return self

    @field_validator("model_size")
    @classmethod
    def validate_model_size(cls, v: str) -> str:
        """Validate model size is one of allowed values."""
        allowed = ["tiny", "base", "small", "medium", "large-v2", "turbo"]
        if v not in allowed:
            raise ValueError(f"Invalid model size. Must be one of: {allowed}")
        return v

    model_config = {"json_schema_extra": {"example": {"file_path": "/path/to/video.mp4", "model_size": "turbo", "language": None, "beam_size": 5}}}


class YoutubeInfoRequest(BaseModel):
    """Request model for YouTube video info lookup."""

    url: str = Field(..., description="YouTube video URL")
