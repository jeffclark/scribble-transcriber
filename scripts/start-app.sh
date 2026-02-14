#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "🚀 Starting Video Transcriber Application"
echo "=========================================="
echo ""

# Cleanup function for graceful shutdown
cleanup() {
    echo ""
    echo "🛑 Shutting down application..."

    # Stop backend
    if [ -n "$BACKEND_PID" ]; then
        echo "⏳ Stopping backend server..."
        "$SCRIPT_DIR/stop-server.sh"
    fi

    # Stop frontend (Tauri)
    if [ -n "$FRONTEND_PID" ]; then
        echo "⏳ Stopping Mac app..."
        kill -TERM $FRONTEND_PID 2>/dev/null || true
        wait $FRONTEND_PID 2>/dev/null || true
    fi

    echo "✅ Application stopped"
    exit 0
}

# Register cleanup on exit signals
trap cleanup SIGINT SIGTERM EXIT

# Check if frontend dependencies are installed
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "⚠️  Frontend dependencies not installed"
    echo "Installing dependencies..."
    cd "$FRONTEND_DIR"
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install frontend dependencies"
        exit 1
    fi
    cd "$PROJECT_ROOT"
fi

# Step 1: Start backend server
echo "📡 Starting backend server..."
"$SCRIPT_DIR/start-server.sh"

if [ $? -ne 0 ]; then
    echo "❌ Failed to start backend server"
    exit 1
fi

# Mark that backend is running (for cleanup)
BACKEND_PID=1

echo ""
echo "✅ Backend server is running"
echo ""

# Wait a moment for backend to stabilize
sleep 2

# Step 2: Start frontend (Tauri Mac app)
echo "🖥️  Starting Mac application..."
echo "   (This will open a window in a few seconds...)"
echo ""

cd "$FRONTEND_DIR"

# Start Tauri in foreground (so we can see logs)
npm run tauri:dev &
FRONTEND_PID=$!

# Wait for the frontend process
wait $FRONTEND_PID

# If we get here, the frontend exited (user closed the app)
echo ""
echo "🖥️  Mac application closed"

# Cleanup will be called by trap
