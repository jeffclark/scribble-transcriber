# Video Transcriber Backend

Local video transcription service with GPU acceleration using Whisper models.

## Features

- 🎬 Transcribe video files locally with Whisper Turbo
- 🚀 GPU acceleration (CUDA/MPS) with automatic CPU fallback
- 🔒 Secure token-based authentication
- 📝 Output in JSON and plain text formats
- ⚡ Fast processing with faster-whisper

## Requirements

- Python 3.11+
- FFmpeg (for audio extraction)
- CUDA 12.3+ (optional, for NVIDIA GPUs)

## Installation

1. **Create virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Verify FFmpeg is installed:**
```bash
ffmpeg -version
```

## Development Setup

1. **Install with dev dependencies:**
```bash
pip install -e ".[dev]"
```

2. **Run tests:**
```bash
pytest
```

## Usage

### Start the server

```bash
cd backend
uvicorn src.main:app --host 127.0.0.1 --port 8765
```

The server will start and display an authentication token in the logs:
```
INFO: Sidecar started with auth token: AbCdEf12...
```

### Health check

```bash
curl http://localhost:8765/health
```

### Transcribe a video

```bash
curl -X POST http://localhost:8765/transcribe \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: YOUR_TOKEN_HERE" \
  -d '{
    "file_path": "/path/to/video.mp4",
    "model_size": "turbo",
    "beam_size": 5
  }'
```

## API Endpoints

### `GET /health`
Health check endpoint (no authentication required).

**Response:**
```json
{
  "status": "ok",
  "model_loaded": true
}
```

### `POST /transcribe`
Transcribe a video file.

**Headers:**
- `X-Auth-Token`: Authentication token (required)

**Request body:**
```json
{
  "file_path": "/path/to/video.mp4",
  "model_size": "turbo",
  "language": null,
  "beam_size": 5
}
```

**Response:**
```json
{
  "metadata": {
    "source_file": "video.mp4",
    "transcription_date": "2026-02-13T14:30:00Z",
    "model": "turbo",
    "device": "cuda",
    "language": "en",
    "language_probability": 0.98,
    "duration_seconds": 120.5
  },
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 3.5,
      "text": "Welcome to the video."
    }
  ],
  "output_files": {
    "json": "/path/to/video_transcript.json",
    "txt": "/path/to/video_transcript.txt"
  }
}
```

## Configuration

### Supported Model Sizes

- `tiny` - Fastest, lowest accuracy
- `base` - Fast, good for real-time
- `small` - Balanced
- `medium` - High accuracy
- `large-v2` - Very high accuracy, slow
- `turbo` - **Recommended** - 6-8x faster than large-v3, minimal accuracy loss

### GPU Support

The service automatically detects and uses:
- **NVIDIA GPUs** via CUDA
- **Apple Silicon** via MPS (Metal Performance Shaders)
- **CPU fallback** if no GPU available

GPU memory is automatically cleaned after each transcription to prevent leaks.

## Security Features

- ✅ Token-based authentication for all transcription endpoints
- ✅ Path traversal validation (prevents access to system files)
- ✅ Secure temporary file handling (TOCTOU prevention)
- ✅ Restricted file permissions (0600) on temp files
- ✅ Allowed file extension validation

## Output Files

Transcriptions are saved in two formats:

1. **JSON** (`video_transcript.json`): Structured format with timestamps and metadata
2. **Text** (`video_transcript.txt`): Plain text transcript

Files are saved in the same directory as the source video.

## Troubleshooting

### GPU not detected

1. **NVIDIA GPUs**: Verify CUDA is installed:
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

2. **Apple Silicon**: Verify MPS is available:
```bash
python -c "import torch; print(torch.backends.mps.is_available())"
```

### Out of memory errors

The service automatically falls back to CPU if GPU runs out of memory. To reduce memory usage:
- Use a smaller model size (`small` or `base`)
- Process shorter videos
- Close other GPU-intensive applications

### FFmpeg not found

Install FFmpeg:
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from https://ffmpeg.org/download.html
- **Linux**: `sudo apt install ffmpeg` or `sudo yum install ffmpeg`

## License

MIT
