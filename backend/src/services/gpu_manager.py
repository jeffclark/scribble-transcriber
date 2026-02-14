"""GPU detection and Whisper model lifecycle management."""

import gc
import logging
import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class GPUManager:
    """
    Manages GPU detection, model loading, and lifecycle.

    Features:
    - Automatic GPU detection (CUDA, MPS, CPU)
    - Simplified 2-level fallback (GPU -> CPU, not 4-level YAGNI)
    - Lazy model loading (defer until first transcription)
    - Proper cleanup to fix 300MB GPU memory leak
    """

    def __init__(self):
        self._model: Optional[WhisperModel] = None
        self._device: str = "cpu"
        self._compute_type: str = "int8"
        self._current_model_size: Optional[str] = None

    async def initialize(self):
        """Detect GPU and set device configuration."""
        self._device, self._compute_type = self._detect_device()
        logger.info(f"GPU Manager initialized - device: {self._device}, compute_type: {self._compute_type}")

    def _detect_device(self) -> Tuple[str, str]:
        """
        Detect best available device using lightweight subprocess calls.

        This replaces torch.cuda.is_available() and torch.backends.mps.is_available()
        with subprocess-based checks, saving 250MB bundle size + 200MB RAM.

        Returns:
            tuple[str, str]: (device, compute_type)
                device: "cuda" or "cpu"
                compute_type: "float16" for CUDA, "int8" for CPU
        """
        # Check for NVIDIA GPU first
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                gpu_name = result.stdout.strip()
                logger.info(f"CUDA GPU detected: {gpu_name}")
                return "cuda", "float16"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # nvidia-smi not found or timed out - no NVIDIA GPU
            pass

        # Check for Apple Silicon
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                cpu_brand = result.stdout.strip()
                if "Apple" in cpu_brand or any(chip in cpu_brand for chip in ["M1", "M2", "M3", "M4"]):
                    logger.info(f"Apple Silicon detected: {cpu_brand}")
                    logger.info("Using CPU with int8 (faster-whisper doesn't support MPS)")
                    # Note: faster-whisper (ctranslate2) doesn't support MPS
                    return "cpu", "int8"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # sysctl failed - continue to generic CPU fallback
                pass

        # Fallback: Generic CPU
        logger.info("No GPU detected, using CPU with int8 quantization")
        return "cpu", "int8"

    def _is_model_cached(self, model_size: str) -> bool:
        """
        Check if model is already cached locally.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v2, turbo)

        Returns:
            bool: True if model is cached, False otherwise
        """
        cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        expected_model_path = cache_dir / f"models--Systran--faster-whisper-{model_size}"
        return expected_model_path.exists()

    def get_model(self, model_size: str = "turbo") -> WhisperModel:
        """
        Lazy-load Whisper model on first use.

        This defers model download to first transcription rather than startup
        for better UX (recommendation from research).

        Args:
            model_size: Whisper model size (default: turbo - 6-8x faster than large-v3)

        Returns:
            WhisperModel: Loaded model ready for transcription

        Raises:
            RuntimeError: If model loading fails
        """
        # If model already loaded and same size, reuse it
        if self._model is not None and self._current_model_size == model_size:
            return self._model

        # If switching models, cleanup old one first
        if self._model is not None:
            logger.info(f"Switching from {self._current_model_size} to {model_size}, cleaning up old model")
            self.cleanup()

        # Load model with automatic GPU fallback
        try:
            logger.info(f"Loading {model_size} model on {self._device}...")

            # Check if model is cached
            is_cached = self._is_model_cached(model_size)
            if is_cached:
                logger.info(f"Model {model_size} found in cache, loading...")
            else:
                logger.info(f"Model {model_size} not cached, will download (~3GB)...")

            self._model = WhisperModel(model_size, device=self._device, compute_type=self._compute_type)

            self._current_model_size = model_size
            logger.info(f"Model {model_size} loaded successfully on {self._device}")

            return self._model

        except RuntimeError as e:
            error_msg = str(e).lower()

            # If GPU out of memory, try CPU fallback
            if "out of memory" in error_msg and self._device != "cpu":
                logger.warning(
                    f"GPU OOM loading {model_size} model. Falling back to CPU with int8 quantization..."
                )
                self._device = "cpu"
                self._compute_type = "int8"

                # Cleanup any partial GPU allocations
                self._cleanup_gpu_memory()

                try:
                    self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
                    self._current_model_size = model_size
                    logger.info(f"Model {model_size} loaded successfully on CPU (fallback)")
                    return self._model

                except Exception as fallback_error:
                    raise RuntimeError(f"Failed to load model on CPU after GPU OOM: {fallback_error}")

            # Other errors - raise
            raise RuntimeError(f"Failed to load model {model_size} on {self._device}: {e}")

    def _cleanup_gpu_memory(self):
        """
        Force GPU memory cleanup.

        Note: With ctranslate2 (used by faster-whisper), GPU memory is managed
        internally. We rely on Python's garbage collector here.

        Previously used torch.cuda.empty_cache(), but we've removed torch
        dependency to save 250MB bundle size. ctranslate2 handles cleanup.
        """
        # ctranslate2 manages GPU memory internally
        # Just trigger Python GC to release any references
        gc.collect()
        logger.debug("Memory cleanup triggered (ctranslate2 manages GPU internally)")

    def cleanup_after_transcription(self):
        """
        Cleanup GPU memory after transcription.

        Call this after EVERY transcription to prevent memory leak.
        Does not unload the model - just releases cached memory.
        """
        self._cleanup_gpu_memory()
        gc.collect()
        logger.debug("Post-transcription memory cleanup complete")

    def cleanup(self):
        """
        Full cleanup - release model and GPU resources.

        Call this during shutdown or when switching models.
        """
        if self._model is not None:
            logger.info(f"Releasing {self._current_model_size} model resources")
            del self._model
            self._model = None
            self._current_model_size = None

        self._cleanup_gpu_memory()
        gc.collect()

        logger.info("GPU Manager cleanup complete")

    def is_ready(self) -> bool:
        """Check if model is loaded and ready for transcription."""
        return self._model is not None

    def get_device_info(self) -> dict:
        """
        Get current device information.

        Returns:
            dict: Device info with keys: device, compute_type, model_size
        """
        return {
            "device": self._device,
            "compute_type": self._compute_type,
            "model_size": self._current_model_size or "not loaded",
        }
