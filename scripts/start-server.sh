#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
PID_FILE="$BACKEND_DIR/.server.pid"
LOG_FILE="$BACKEND_DIR/server.log"
PORT=8765

echo "Starting Video Transcription Backend..."
echo "======================================="

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 $PID 2>/dev/null; then
        echo "⚠️  Server already running (PID: $PID)"
        echo "Use './scripts/server.sh stop' to stop it first"
        exit 1
    else
        echo "⚠️  Removing stale PID file"
        rm -f "$PID_FILE"
    fi
fi

# Check if port is in use
if lsof -ti:$PORT >/dev/null 2>&1; then
    echo "❌ Port $PORT is already in use"
    echo ""
    echo "Process using port:"
    lsof -i:$PORT
    echo ""
    echo "To stop it: ./scripts/server.sh stop"
    exit 1
fi

cd "$BACKEND_DIR"

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found"
    echo "Run: python -m venv .venv"
    exit 1
fi

echo "✅ Environment ready"

# Activate venv
source .venv/bin/activate

# Check dependencies
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ Dependencies not installed"
    echo "Run: pip install -r requirements.txt"
    exit 1
fi

echo "✅ Dependencies installed"
echo "✅ Port $PORT available"

# Rotate log if too large
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$LOG_SIZE" -gt 10000 ]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        echo "📝 Rotated old logs"
    fi
fi

# Start server in background
echo "🚀 Starting server..."
nohup python -m uvicorn src.main:app \
    --host 127.0.0.1 \
    --port $PORT \
    --reload \
    > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

echo "✅ Server started (PID: $SERVER_PID)"
echo ""

# Wait for server to be ready (check health endpoint)
echo "⏳ Waiting for server to be ready..."
for i in {1..30}; do
    sleep 1
    if curl -sf http://127.0.0.1:$PORT/health >/dev/null 2>&1; then
        echo "✅ Server is healthy"
        break
    fi

    # Check if process died
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "❌ Server failed to start"
        echo ""
        echo "Last 20 lines of log:"
        tail -20 "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi

    if [ $i -eq 30 ]; then
        echo "⚠️  Server started but health check timeout"
        echo "Check logs: tail -f $LOG_FILE"
    fi
done

# Extract and display token (first 30 lines usually contain startup)
echo ""
echo "Server Information"
echo "=================="
TOKEN=$(grep -A1 "Full Token:" "$LOG_FILE" 2>/dev/null | tail -1 | awk '{print $NF}' || echo "")
if [ -n "$TOKEN" ]; then
    echo "🔐 Auth Token: ${TOKEN:0:12}..."
    echo "🔐 Full Token: $TOKEN"
else
    echo "⚠️  Token not found in logs yet"
    echo "Check: grep 'Token' $LOG_FILE"
fi

echo ""
echo "📍 Server: http://127.0.0.1:$PORT"
echo "📍 Health: http://127.0.0.1:$PORT/health"
echo "📍 Docs: http://127.0.0.1:$PORT/docs"
echo ""
echo "📝 Logs: $LOG_FILE"
echo "   View: tail -f $LOG_FILE"
echo ""
echo "To stop: ./scripts/server.sh stop"
