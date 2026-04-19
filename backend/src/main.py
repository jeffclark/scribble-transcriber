"""FastAPI application for video transcription service."""

import argparse
import asyncio
import json
import logging
import os

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .models.requests import TranscribeRequest
from .models.responses import TranscribeResponse
from .services.transcription import TranscriptionService
from .services.youtube_downloader import YoutubeDownloadError, fetch_youtube_info
from .utils.security import generate_auth_token, get_auth_token, verify_token, verify_token_value
from .utils.validation import VideoValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Video Transcription Sidecar",
    description="Local video transcription service with GPU acceleration",
    version="0.1.0",
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",      # Vite dev server (localhost variant)
        "http://127.0.0.1:1420",      # Vite dev server (IP variant)
        "http://localhost:3000",      # Alternative dev port (localhost variant)
        "http://127.0.0.1:3000",      # Alternative dev port (IP variant)
        "tauri://localhost",          # Tauri v2 production
        "https://tauri.localhost",    # Tauri HTTPS variant
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    """Log incoming requests for debugging connection issues."""
    origin = request.headers.get("origin", "No origin header")
    logger.info(f"Incoming request: {request.method} {request.url.path} from origin: {origin}")

    response = await call_next(request)
    return response


# Initialize transcription service (singleton)
transcription_service = TranscriptionService()


@app.on_event("startup")
async def startup_event():
    """Initialize transcription service and generate auth token."""
    logger.info("=" * 60)
    logger.info("Starting Video Transcription Sidecar")
    logger.info("=" * 60)

    # Check if running as Tauri sidecar (AUTH_TOKEN environment variable)
    env_token = os.getenv("AUTH_TOKEN")
    if env_token:
        # Running as sidecar - use token from Tauri
        token = env_token
        logger.info(f"🔐 Auth Token (from Tauri): {token[:8]}***")
        logger.info("   ✅ Sidecar mode - auth token provided by Tauri")
        # Force set the token for verification
        from .utils.security import set_auth_token
        set_auth_token(token)
    else:
        # Development mode - generate token locally
        token = generate_auth_token()
        logger.info(f"🔐 Auth Token (generated): {token[:8]}***")
        logger.info("   ⚠️  Copy this token for API requests (X-Auth-Token header)")
        logger.info(f"   Full token (dev only): {token}")

    # Initialize transcription service
    logger.info("Initializing transcription service...")
    await transcription_service.initialize()

    device_info = transcription_service.gpu_manager.get_device_info()
    logger.info(f"✅ GPU/CPU: {device_info['device']} ({device_info['compute_type']})")
    logger.info("✅ Service ready for transcription requests")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup transcription service resources."""
    logger.info("Shutting down Video Transcription Sidecar...")
    await transcription_service.cleanup()
    logger.info("Shutdown complete")


@app.get("/health")
async def health_check():
    """
    Health check endpoint (no authentication required).

    Returns:
        dict: Health status and model readiness
    """
    device_info = transcription_service.gpu_manager.get_device_info()

    return {
        "status": "ok",
        "service": "video-transcription-sidecar",
        "version": "0.1.0",
        "initialized": transcription_service.is_ready(),
        "model_loaded": transcription_service.gpu_manager.is_ready(),
        "device": device_info["device"],
        "model_size": device_info["model_size"],
    }


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(request: TranscribeRequest, _: str = Depends(verify_token)) -> TranscribeResponse:
    """
    Transcribe a video file and return structured results.

    Requires authentication via X-Auth-Token header.

    Args:
        request: Transcription request with file path and options
        _: Authentication token (validated by dependency)

    Returns:
        TranscribeResponse: Complete transcription with metadata and output files

    Raises:
        HTTPException: 400 for validation errors, 404 for file not found, 500 for server errors
    """
    try:
        source = request.file_path or request.youtube_url
        logger.info(f"Received transcription request: {source}")

        result = await transcription_service.transcribe(
            file_path=request.file_path,
            youtube_url=request.youtube_url,
            model_size=request.model_size,
            language=request.language,
            beam_size=request.beam_size,
        )

        logger.info(f"Transcription successful: {len(result.segments)} segments")
        return result

    except VideoValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except RuntimeError as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}"
        )


@app.get("/youtube-info")
async def youtube_info(
    url: str = Query(..., description="YouTube video URL"),
    token: str = Query(..., description="Authentication token"),
):
    """
    Fetch metadata for a YouTube video without downloading it.

    Requires authentication via token query parameter.

    Returns:
        dict: title, video_id, duration, uploader
    """
    if not verify_token_value(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    try:
        info = fetch_youtube_info(url)
        return info
    except YoutubeDownloadError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"YouTube info error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch video info: {e}")


def format_sse(data: dict) -> str:
    """Format data as Server-Sent Event."""
    return f"data: {json.dumps(data)}\n\n"


@app.get("/transcribe-stream")
async def transcribe_stream(
    file_path: str = Query(None, description="Path to video file"),
    youtube_url: str = Query(None, description="YouTube URL to transcribe"),
    model_size: str = Query("turbo", description="Whisper model size"),
    beam_size: int = Query(5, description="Beam size for decoding"),
    language: str = Query(None, description="Optional language code"),
    token: str = Query(..., description="Authentication token"),
):
    """
    Stream transcription progress using Server-Sent Events.

    Requires authentication via token query parameter (EventSource doesn't support custom headers).
    EventSource only supports GET, so all parameters must be passed as query params.

    Args:
        file_path: Path to video file
        model_size: Whisper model size (default: turbo)
        beam_size: Beam size for decoding (default: 5)
        language: Optional language code (default: None for auto-detection)
        token: Authentication token (from query parameter)

    Returns:
        StreamingResponse: SSE stream with progress updates

    SSE Message Format:
        {
            "stage": "extracting|loading|transcribing|saving|completed|error",
            "progress": 0-100,
            "message": "Human readable status",
            "segment_count": Optional[int],
            "current_time": Optional[float],
            "result": Optional[TranscribeResponse]
        }
    """
    # Verify token
    if not verify_token_value(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    if not file_path and not youtube_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide file_path or youtube_url")

    async def event_generator():
        try:
            source = file_path or youtube_url
            logger.info(f"Starting streaming transcription: {source}")

            # Send immediate connection confirmation (prevents buffering)
            yield format_sse({
                "stage": "connecting",
                "progress": 0,
                "message": "Connected to transcription service"
            })
            logger.info("📡 Sent connection confirmation to frontend")

            # Create a queue for progress updates
            progress_queue = asyncio.Queue()

            # Capture the event loop reference NOW (while in async context)
            # This is critical because queue_progress will be called from a different thread
            loop = asyncio.get_running_loop()

            def queue_progress(data: dict):
                """Thread-safe progress callback."""
                try:
                    # Simple synchronous put via call_soon_threadsafe
                    def sync_put():
                        try:
                            progress_queue.put_nowait(data)
                            logger.info(f"✅ Queued progress: {data.get('stage')} - {data.get('progress')}%")
                        except asyncio.QueueFull:
                            logger.error(f"❌ Queue full, dropping progress update")

                    # Use the captured loop reference (from async context)
                    loop.call_soon_threadsafe(sync_put)

                except Exception as e:
                    logger.error(f"❌ Failed to queue progress: {e}")

            # Run transcription in separate thread to avoid blocking event loop
            # CRITICAL: model.transcribe() is CPU-bound and blocks the event loop
            async def run_transcription():
                try:
                    # Use asyncio.to_thread (Python 3.9+) to run in thread pool
                    import functools

                    # Create a sync wrapper that calls the async function
                    def sync_transcribe():
                        import asyncio
                        # Create new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(
                                transcription_service.transcribe(
                                    file_path=file_path,
                                    youtube_url=youtube_url,
                                    model_size=model_size,
                                    language=language if language else None,
                                    beam_size=beam_size,
                                    progress_callback=queue_progress,
                                )
                            )
                            return result
                        finally:
                            loop.close()

                    # Run in thread pool
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(None, sync_transcribe)

                    await progress_queue.put({"__result__": result})
                except Exception as e:
                    logger.error(f"Transcription error: {e}")
                    await progress_queue.put({"__error__": str(e)})

            # Start transcription task
            transcription_task = asyncio.create_task(run_transcription())

            # Send test message to verify stream is working
            await asyncio.sleep(0.1)  # Small delay to ensure task started
            logger.info("📡 Sending test progress message")

            # Stream progress updates
            while True:
                data = await progress_queue.get()

                if "__result__" in data:
                    # Transcription complete
                    result = data["__result__"]
                    logger.info("✅ Sending lightweight completion to frontend")

                    # Only send file paths - not the full result!
                    # This prevents SSE message fragmentation for large transcriptions (1000+ segments)
                    yield format_sse({
                        "stage": "completed",
                        "progress": 100,
                        "message": "Transcription complete",
                        "output_files": result.output_files,  # Just the file paths
                        "segment_count": len(result.segments),
                        "metadata": {
                            "source_file": result.metadata.source_file,
                            "language": result.metadata.language,
                            "duration_seconds": result.metadata.duration_seconds,
                        }
                    })
                    logger.info("✅ Sent lightweight completion to frontend")
                    break

                elif "__error__" in data:
                    # Transcription failed
                    logger.error(f"❌ Streaming error to frontend: {data['__error__']}")
                    yield format_sse({
                        "stage": "error",
                        "progress": 0,
                        "message": f"Transcription failed: {data['__error__']}"
                    })
                    break

                else:
                    # Progress update
                    logger.info(f"📡 Streaming to frontend: {data.get('stage')} - {data.get('progress')}%")
                    yield format_sse(data)

            # Wait for transcription task to complete
            await transcription_task

        except Exception as e:
            logger.error(f"Streaming transcription error: {e}")
            yield format_sse({
                "stage": "error",
                "progress": 0,
                "message": f"Server error: {str(e)}"
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@app.get("/token")
async def get_token_endpoint():
    """
    Get the current authentication token (for development/debugging).

    Note: In production, this endpoint should be removed or protected.

    Returns:
        dict: Current auth token
    """
    try:
        token = get_auth_token()
        return {"token": token}
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Parse command-line arguments (for Tauri sidecar mode)
    parser = argparse.ArgumentParser(description="Video Transcription Sidecar Backend")
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to listen on (default: 8765)"
    )
    args = parser.parse_args()

    # Configure uvicorn for SSE streaming (no buffering)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
        log_level="info",
        timeout_keep_alive=300,  # Keep SSE connections alive
        limit_concurrency=None,  # No limit on concurrent connections
    )
