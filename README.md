# Video Transcriber

Cross-platform desktop application for batch video transcription using local Whisper models with GPU acceleration.

## Project Status

🚧 **Phase 1 (Backend MVP) - COMPLETE**

Core transcription service with GPU acceleration is implemented and tested.

### Completed Features

- ✅ Python FastAPI backend with faster-whisper
- ✅ GPU detection (CUDA, MPS, CPU fallback)
- ✅ Secure authentication and path validation
- ✅ Audio extraction with FFmpeg
- ✅ JSON and plain text output formats
- ✅ GPU memory leak fix (300MB per file)
- ✅ Comprehensive test suite

### Next Steps

- Phase 2: Tauri desktop shell (React/TypeScript frontend)
- Phase 3: Batch processing with queue management
- Phase 4: GPU optimization and fallback refinement
- Phase 5: Polish and distribution (DMG/MSI installers)

## Quick Start (Backend Only)

### Prerequisites

- Python 3.11+
- FFmpeg
- (Optional) CUDA 12.3+ for NVIDIA GPUs

### Installation

1. **Clone repository:**
```bash
cd ~/Projects/video-transcriber
```

2. **Set up Python environment:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. **Verify FFmpeg:**
```bash
ffmpeg -version
```

### Running the Backend

```bash
cd backend
source .venv/bin/activate
python -m uvicorn src.main:app --host 127.0.0.1 --port 8765
```

Or use the convenience script:
```bash
./scripts/dev.sh
```

The server will display an authentication token on startup:
```
🔐 Full Token: AbCdEfGh1234567890...
```

Copy this token for API requests.

### Testing

**Run unit tests:**
```bash
cd backend
pytest
```

**Run specific test file:**
```bash
pytest tests/test_validation.py -v
```

**Test the API manually:**
```bash
# 1. Start server (in one terminal)
python -m uvicorn src.main:app --host 127.0.0.1 --port 8765

# 2. Get auth token (in another terminal)
curl http://localhost:8765/token

# 3. Transcribe a video
curl -X POST http://localhost:8765/transcribe \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: YOUR_TOKEN_HERE" \
  -d '{
    "file_path": "/path/to/your/video.mp4",
    "model_size": "turbo",
    "beam_size": 5
  }'
```

## Architecture

```
video-transcriber/
├── backend/                 # Python FastAPI service (Phase 1 ✅)
│   ├── src/
│   │   ├── models/         # Pydantic request/response models
│   │   ├── services/       # Core business logic
│   │   │   ├── gpu_manager.py        # GPU detection & model lifecycle
│   │   │   ├── audio_processor.py    # FFmpeg audio extraction
│   │   │   └── transcription.py      # Main transcription service
│   │   ├── utils/          # Security, validation utilities
│   │   └── main.py         # FastAPI application
│   ├── tests/              # Test suite
│   └── requirements.txt    # Python dependencies
│
├── frontend/               # React/TypeScript UI (Phase 2 - TODO)
│   └── (coming soon)
│
└── docs/
    └── plans/              # Implementation plans
```

## Technology Stack

- **Backend**: Python 3.11+ with FastAPI
- **ML**: faster-whisper (6-8x faster than OpenAI Whisper)
- **Video**: FFmpeg for audio extraction
- **GPU**: CUDA (NVIDIA) or MPS (Apple Silicon) with CPU fallback
- **Frontend** (TODO): React 18 + TypeScript + Vite
- **Desktop** (TODO): Tauri 2.0 (Rust-based, 3-5MB bundle)

## Development

### Project Structure

- `backend/src/models/` - Type-safe API models with Pydantic
- `backend/src/services/` - Core transcription pipeline
- `backend/src/utils/` - Security, validation, helpers
- `backend/tests/` - Comprehensive test coverage

### Key Security Features

✅ **Implemented in Phase 1:**
- Token-based authentication (prevents local malware access)
- Path traversal validation (prevents access to system files)
- Secure temp file handling (TOCTOU prevention)
- Restrictive file permissions (0600)

### Performance Optimizations

✅ **Implemented in Phase 1:**
- GPU memory leak fix (~300MB per transcription)
- Lazy model loading (defer to first use, not startup)
- Simplified 2-level fallback (GPU → CPU, not 4-level YAGNI)
- Automatic resource cleanup after each transcription

## Documentation

- [Backend README](backend/README.md) - Detailed API documentation
- [Implementation Plan](docs/plans/2026-02-13-feat-desktop-video-transcription-app-plan.md) - Full project plan with research insights

## Troubleshooting

### GPU not detected

**NVIDIA GPUs:**
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

**Apple Silicon:**
```bash
python -c "import torch; print(torch.backends.mps.is_available())"
```

### FFmpeg not found

- **macOS**: `brew install ffmpeg`
- **Windows**: Download from https://ffmpeg.org/download.html
- **Linux**: `sudo apt install ffmpeg`

### Import errors

Make sure you're in the virtual environment:
```bash
source backend/.venv/bin/activate
```

## License

MIT

## Contributing

Phase 1 (Backend MVP) is complete. Phase 2 (Tauri desktop shell) is next!

See the [full implementation plan](docs/plans/2026-02-13-feat-desktop-video-transcription-app-plan.md) for details.
