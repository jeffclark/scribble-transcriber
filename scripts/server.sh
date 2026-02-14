#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Show usage
usage() {
    cat << EOF
Video Transcription Backend Server Manager

Usage: $0 <command>

Commands:
    start       Start the backend server
    stop        Stop the backend server
    restart     Restart the backend server
    status      Show server status
    logs        Tail server logs
    help        Show this help message

Examples:
    $0 start        # Start server
    $0 stop         # Stop server
    $0 status       # Check if running
    $0 logs         # View live logs

EOF
    exit 0
}

# Parse command
COMMAND="${1:-help}"

case "$COMMAND" in
    start)
        "$SCRIPT_DIR/start-server.sh"
        ;;

    stop)
        "$SCRIPT_DIR/stop-server.sh"
        ;;

    restart)
        echo "Restarting server..."
        "$SCRIPT_DIR/stop-server.sh"
        sleep 2
        "$SCRIPT_DIR/start-server.sh"
        ;;

    status)
        "$SCRIPT_DIR/status-server.sh"
        ;;

    logs)
        PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
        LOG_FILE="$PROJECT_ROOT/backend/server.log"

        if [ ! -f "$LOG_FILE" ]; then
            echo "❌ Log file not found: $LOG_FILE"
            echo "Server may not be running"
            exit 1
        fi

        echo "Tailing logs (Ctrl+C to exit)..."
        tail -f "$LOG_FILE"
        ;;

    help|--help|-h)
        usage
        ;;

    *)
        echo "❌ Unknown command: $COMMAND"
        echo ""
        usage
        ;;
esac
