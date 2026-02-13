"""FastAPI application for video transcription service."""

import logging

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .models.requests import TranscribeRequest
from .models.responses import TranscribeResponse
from .services.transcription import TranscriptionService
from .utils.security import generate_auth_token, get_auth_token, verify_token
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
    allow_origins=["http://localhost:*", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize transcription service (singleton)
transcription_service = TranscriptionService()


@app.on_event("startup")
async def startup_event():
    """Initialize transcription service and generate auth token."""
    logger.info("=" * 60)
    logger.info("Starting Video Transcription Sidecar")
    logger.info("=" * 60)

    # Generate authentication token
    token = generate_auth_token()
    logger.info(f"🔐 Auth Token: {token[:12]}...")
    logger.info(f"🔐 Full Token: {token}")
    logger.info("   ⚠️  Copy this token for API requests (X-Auth-Token header)")

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
        logger.info(f"Received transcription request: {request.file_path}")

        result = await transcription_service.transcribe(
            file_path=request.file_path,
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

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
