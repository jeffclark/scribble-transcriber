#!/usr/bin/env python3
"""
Standalone entry point for bundled backend.
This file doesn't use relative imports and works with PyInstaller.
"""

import sys
import os
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the backend."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Video Transcription Sidecar Backend")
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to listen on (default: 8765)"
    )
    args = parser.parse_args()

    # Add src directory to Python path if needed
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        bundle_dir = sys._MEIPASS
        src_path = os.path.join(bundle_dir, 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
    else:
        # Running as script
        src_path = os.path.join(os.path.dirname(__file__), 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    # Now we can import from src
    try:
        from src.main import app
        import uvicorn

        # Run uvicorn
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=args.port,
            log_level="info",
            timeout_keep_alive=300,
            limit_concurrency=None,
        )
    except Exception as e:
        logger.error(f"Failed to start backend: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
