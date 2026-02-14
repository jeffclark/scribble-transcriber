#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$PROJECT_ROOT/backend/.server.pid"
PORT=8765

echo "Video Transcription Backend Status"
echo "==================================="

# Check PID file
if [ ! -f "$PID_FILE" ]; then
    echo "❌ Server not running (no PID file)"

    # Double-check port
    if lsof -ti:$PORT >/dev/null 2>&1; then
        echo "⚠️  Warning: Port $PORT is in use but no PID file"
        echo "Process info:"
        lsof -i:$PORT
    fi
    exit 1
fi

PID=$(cat "$PID_FILE")

# Check if process exists
if ! kill -0 $PID 2>/dev/null; then
    echo "❌ Server not running (stale PID: $PID)"
    exit 1
fi

echo "✅ Running (PID: $PID)"

# Check port
if lsof -ti:$PORT >/dev/null 2>&1; then
    echo "✅ Port $PORT listening"
else
    echo "⚠️  Port $PORT not listening"
fi

# Health check
if command -v curl >/dev/null 2>&1; then
    if curl -sf http://127.0.0.1:$PORT/health >/dev/null 2>&1; then
        echo "✅ Health check: OK"

        # Get details
        HEALTH=$(curl -s http://127.0.0.1:$PORT/health)
        echo ""
        echo "Server Details:"
        echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
    else
        echo "⚠️  Health check: Failed"
    fi
else
    echo "ℹ️  Install curl for health checks"
fi

echo ""
echo "Server URL: http://127.0.0.1:$PORT"
echo "Health: http://127.0.0.1:$PORT/health"
echo "API Docs: http://127.0.0.1:$PORT/docs"
