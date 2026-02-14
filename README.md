# Scribble - Video Transcriber

Desktop application for batch video transcription using local Whisper models. All transcription happens on your Mac - no cloud services, no data sent anywhere.

## Download and Install

**Latest Release:** [Scribble v0.1.0 for macOS (Apple Silicon)](frontend/src-tauri/target/release/bundle/dmg/Video%20Transcriber_0.1.0_aarch64.dmg)

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## Requirements

- **macOS 11.0 (Big Sur) or later**
- **Apple Silicon (M1/M2/M3/M4) ONLY** - Intel Macs not supported
- **2GB free disk space** (for Whisper models)

## Known Limitations (v0.1.0)

- **Apple Silicon Only**: This release is built for M1/M2/M3/M4 Macs only. Intel Macs are not supported due to architecture constraints.
- **Orphan Processes**: When quitting with Cmd+Q, backend processes may not terminate immediately. If the app won't connect after relaunching, manually quit `scribble-backend` processes in Activity Monitor or run `killall scribble-backend` in Terminal.
- **First Launch Slow**: The first transcription takes 30-60 seconds longer as Whisper models are downloaded.
- **CPU-Only Transcription**: macOS builds use CPU mode (MPS support coming in future release).

## Features

- ✅ **Fully local transcription** - No internet required after initial setup
- ✅ **Multiple Whisper models** - Turbo, Base, Small, Medium, Large-v3
- ✅ **Batch processing** - Queue multiple videos
- ✅ **Real-time progress** - See transcription progress per video
- ✅ **Multiple output formats** - JSON (with timestamps) and plain text
- ✅ **Auto-start backend** - No terminal commands needed
- ✅ **Clean shutdown** - Backend terminates when app quits

## Project Status

✅ **v0.1.0 - macOS Distribution Ready**

All phases complete. The app is packaged and ready for distribution.

## Building from Source

For developers who want to build from source or contribute to the project.

### Prerequisites

- macOS with Apple Silicon (M1/M2/M3/M4)
- Xcode Command Line Tools: `xcode-select --install`
- Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- Node.js 18+: `brew install node`
- Python 3.11+: `brew install python@3.11`
- FFmpeg: `brew install ffmpeg`

### Build Steps

1. **Clone repository:**
```bash
git clone https://github.com/yourusername/video-transcriber.git
cd video-transcriber
```

2. **Build backend binary:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

# Build PyInstaller bundle
pyinstaller --clean backend.spec

# Copy to Tauri binaries directory
cp dist/scribble-backend/scribble-backend ../frontend/src-tauri/binaries/scribble-backend-aarch64-apple-darwin
chmod +x ../frontend/src-tauri/binaries/scribble-backend-aarch64-apple-darwin
```

3. **Download FFmpeg binary:**
```bash
cd ../frontend/src-tauri/binaries
curl -L https://evermeet.cx/ffmpeg/getrelease/arm64/ffmpeg/zip -o ffmpeg.zip
unzip ffmpeg.zip
mv ffmpeg ffmpeg-aarch64-apple-darwin
chmod +x ffmpeg-aarch64-apple-darwin
rm ffmpeg.zip
```

4. **Build Tauri app:**
```bash
cd ../../
npm install
npm run tauri build
```

5. **Output:**
```
frontend/src-tauri/target/release/bundle/
├── dmg/Video Transcriber_0.1.0_aarch64.dmg
└── macos/Video Transcriber.app
```

## Development (Backend Only)

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
