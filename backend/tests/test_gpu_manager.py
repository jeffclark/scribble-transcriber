"""Tests for GPU manager and model lifecycle."""

import pytest

from src.services.gpu_manager import GPUManager


@pytest.mark.asyncio
async def test_gpu_manager_initialization():
    """Test GPU manager initializes and detects device."""
    manager = GPUManager()

    # Before initialization
    assert not manager.is_ready()

    # Initialize
    await manager.initialize()

    # After initialization
    device_info = manager.get_device_info()
    assert device_info["device"] in ["cuda", "mps", "cpu"]
    assert device_info["compute_type"] in ["float16", "int8"]
    assert device_info["model_size"] == "not loaded"

    # Cleanup
    manager.cleanup()


@pytest.mark.asyncio
async def test_gpu_manager_model_loading():
    """Test model loading (may take time on first run)."""
    manager = GPUManager()
    await manager.initialize()

    # Get model (will download if not cached)
    model = manager.get_model("tiny")  # Use tiny model for faster test

    assert model is not None
    assert manager.is_ready()

    device_info = manager.get_device_info()
    assert device_info["model_size"] == "tiny"

    # Cleanup
    manager.cleanup()
    assert not manager.is_ready()


@pytest.mark.asyncio
async def test_gpu_manager_model_switching():
    """Test switching between different model sizes."""
    manager = GPUManager()
    await manager.initialize()

    # Load first model
    model1 = manager.get_model("tiny")
    assert manager.get_device_info()["model_size"] == "tiny"

    # Switch to different model
    model2 = manager.get_model("base")
    assert manager.get_device_info()["model_size"] == "base"

    # Cleanup
    manager.cleanup()


@pytest.mark.asyncio
async def test_gpu_manager_cleanup_after_transcription():
    """Test memory cleanup after transcription doesn't unload model."""
    manager = GPUManager()
    await manager.initialize()

    # Load model
    model = manager.get_model("tiny")
    assert manager.is_ready()

    # Cleanup after transcription
    manager.cleanup_after_transcription()

    # Model should still be loaded
    assert manager.is_ready()

    # Full cleanup
    manager.cleanup()
    assert not manager.is_ready()
