#!/bin/bash
# Double-click: starts Ask Albert (the live demo of the help-centre answerer) and opens it in the browser.
# Keep this window open during the demo; close it (or press Ctrl+C) to stop.
cd "$(dirname "$0")"
PORT=8000
if curl -s "http://localhost:$PORT/api/info" >/dev/null; then
  open "http://localhost:$PORT"; echo "Ask Albert is already running: opened in the browser."; exit 0
fi
.venv/bin/python -m src.web --port $PORT 2> >(grep -v "Loading weights\|HF_TOKEN\|Redirects are currently\|W[0-9]\{4\}" >&2) &
SERVER=$!
for i in $(seq 1 90); do
  curl -s "http://localhost:$PORT/api/info" >/dev/null && { open "http://localhost:$PORT"; break; }
  sleep 1
done
wait $SERVER
