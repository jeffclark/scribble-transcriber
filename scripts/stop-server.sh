#!/bin/bash
set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$PROJECT_ROOT/backend/.server.pid"
PORT=8765

echo "Stopping Video Transcription Backend..."

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  No PID file found at $PID_FILE"

    # Check if something is running on port anyway
    if lsof -ti:$PORT >/dev/null 2>&1; then
        echo "⚠️  Found process on port $PORT without PID file"
        PORT_PID=$(lsof -ti:$PORT)
        echo "Killing process $PORT_PID..."
        kill -9 $PORT_PID 2>/dev/null || true
        echo "✅ Port $PORT cleaned up"
    else
        echo "✅ Server not running"
    fi
    exit 0
fi

# Read PID
PID=$(cat "$PID_FILE")

# Check if process exists
if ! kill -0 $PID 2>/dev/null; then
    echo "⚠️  Process $PID not running (stale PID file)"
    rm -f "$PID_FILE"

    # Clean up port if needed
    if lsof -ti:$PORT >/dev/null 2>&1; then
        PORT_PID=$(lsof -ti:$PORT)
        kill -9 $PORT_PID 2>/dev/null || true
    fi
    echo "✅ Cleanup complete"
    exit 0
fi

echo "Stopping server (PID: $PID)..."

# Phase 1: Graceful shutdown (SIGTERM)
echo "⏳ Attempting graceful shutdown..."
kill -TERM $PID 2>/dev/null || true
sleep 5

# Check if stopped
if ! kill -0 $PID 2>/dev/null; then
    echo "✅ Server stopped gracefully"
    rm -f "$PID_FILE"
    exit 0
fi

# Phase 2: Wait a bit longer (GPU cleanup may take time)
echo "⏳ Waiting for cleanup to complete..."
sleep 3

if ! kill -0 $PID 2>/dev/null; then
    echo "✅ Server stopped"
    rm -f "$PID_FILE"
    exit 0
fi

# Phase 3: Force kill
echo "⚠️  Server not responding, forcing shutdown..."
kill -9 $PID 2>/dev/null || true
sleep 1

# Verify stopped
if kill -0 $PID 2>/dev/null; then
    echo "❌ Failed to stop server"
    exit 1
fi

# Clean up port if needed
if lsof -ti:$PORT >/dev/null 2>&1; then
    echo "Cleaning up port $PORT..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
fi

rm -f "$PID_FILE"
echo "✅ Server stopped (forced)"
