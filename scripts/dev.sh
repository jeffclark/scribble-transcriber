#!/bin/bash
# Development server startup script

set -e

echo "Starting Video Transcription Backend..."
echo "======================================"

cd "$(dirname "$0")/../backend"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found"
    echo "Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ Dependencies not installed"
    echo "Run: pip install -r requirements.txt"
    exit 1
fi

echo "✅ Environment ready"
echo ""
echo "Starting server on http://127.0.0.1:8765"
echo "Press Ctrl+C to stop"
echo ""

# Start server
python -m uvicorn src.main:app --host 127.0.0.1 --port 8765 --reload
