#!/bin/bash
# sendimg.sh - HTTP relay helper for sending images via QQ bot
# Usage:
#   ./sendimg.sh start [directory]   - Start server & list recent PNGs
#   ./sendimg.sh stop               - Stop the server

PORT=9999
PID_FILE="/tmp/sendimg_http_pid"

case "${1:-}" in
  start)
    DIR="${2:-/root}"
    if [ ! -d "$DIR" ]; then
      echo "ERROR: Directory $DIR not found"
      exit 1
    fi

    # Kill any leftover server on the same port
    if [ -f "$PID_FILE" ]; then
      OLD_PID=$(cat "$PID_FILE")
      kill "$OLD_PID" 2>/dev/null && echo "Killed stale server (PID $OLD_PID)"
      rm -f "$PID_FILE"
    fi

    cd "$DIR" || exit 1
    python3 -m http.server "$PORT" &>/tmp/sendimg_http.log &
    echo $! > "$PID_FILE"
    sleep 0.5

    if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "ERROR: Server failed to start"
      cat /tmp/sendimg_http.log
      exit 1
    fi

    IP=$(hostname -I | awk '{print $1}')
    echo "=== HTTP server started ==="
    echo "URL:    http://$IP:$PORT/"
    echo "Serving: $DIR"
    echo ""
    echo "Most recent PNGs (newest first):"
    echo "--------------------------------"
    ls -1t "$DIR"/*.png 2>/dev/null | head -10 | while read -r f; do
      TS=$(stat -c '%Y' "$f" 2>/dev/null | xargs -I{} date -d '@{}' '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
      echo "  $(basename "$f")  [$TS]"
    done
    echo ""
    echo "Server PID: $(cat "$PID_FILE")"
    echo "To stop later: ./sendimg.sh stop"
    ;;
  stop)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      kill "$PID" 2>/dev/null && echo "Server (PID $PID) stopped"
      rm -f "$PID_FILE"
    else
      pkill -f "python3 -m http.server $PORT" 2>/dev/null && echo "Stopped orphan server on port $PORT" || echo "No server found running"
    fi
    ;;
  *)
    echo "Usage: $0 {start|stop} [directory]"
    echo ""
    echo "Examples:"
    echo "  $0 start              Serve /root/ and list recent PNGs"
    echo "  $0 start /root/projects/anima/output  Serve that dir"
    echo "  $0 stop               Kill the server"
    exit 1
    ;;
esac
