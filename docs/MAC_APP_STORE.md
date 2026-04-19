# Mac App Store: Why Scribble Isn't Distributed There

Short version: MAS isn't pursued. This doc exists so future contributors don't re-investigate.

## The two reasons

### 1. Apple Developer Program is paid

MAS requires an active Apple Developer Program membership ($99/year). For a free tool, that cost was declined by the project owner.

### 2. The architecture is sandbox-incompatible

Even if the $99 were paid, the current app would require a months-long rewrite to fit the MAS sandbox. The blockers are all load-bearing to how Scribble works today:

| Blocker | Location | MAS rule it violates |
|---------|----------|----------------------|
| Spawns `scribble-backend` Python binary as a subprocess on launch | `frontend/src-tauri/src/main.rs:82` | MAS sandbox prohibits spawning arbitrary child processes |
| Runs `sh -c "lsof -ti :8765 \| xargs kill -9"` at startup and shutdown | `frontend/src-tauri/src/main.rs:52-56`, `118-122` | Shell invocation and `lsof` are blocked in the sandbox |
| Binds FastAPI to TCP port 8765 | `frontend/src-tauri/src/main.rs:74` | MAS restricts arbitrary port binding |
| Bundles `ffmpeg` as an external executable | `frontend/src-tauri/tauri.conf.json` (externalBin) | Third-party media tools must be replaced with AVFoundation |
| YouTube download via `yt-dlp` | `backend/src/services/youtube_downloader.py` | High rejection risk on MAS review regardless of sandbox compliance |

## What a MAS-compatible version would look like

- Embed Whisper inference directly in the Tauri Rust process (`whisper-rs` or similar). No Python, no FastAPI, no subprocess.
- Replace `ffmpeg` with `AVFoundation` Swift bindings for audio extraction.
- Drop or redesign the YouTube feature.
- Add strict sandbox entitlements (user-selected file read/write only, no arbitrary filesystem access).
- All model files must live in the app container, not `~/.cache/huggingface`.

Estimated effort: **3–6 months of full-time work** with uncertain approval.

## If you're considering picking this up anyway

1. Start with the subprocess removal — everything else depends on it.
2. Expect the first MAS submission to be rejected; budget for 2–3 review cycles.
3. Price the opportunity cost: the same time invested in a sharper free DMG (sparse indexing, GPU support, better UX) likely has higher return.

For now: the signed / unsigned DMG from the project website is the only supported distribution channel.
