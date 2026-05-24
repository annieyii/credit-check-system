#!/bin/bash

cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

# 找一個沒在用的 port（從 8000 開始往上找）
BACKEND_PORT=8000
while lsof -ti:$BACKEND_PORT > /dev/null 2>&1; do
  BACKEND_PORT=$((BACKEND_PORT + 1))
done

# 找一個沒在用的 port（從 3000 開始往上找）
FRONTEND_PORT=3000
while lsof -ti:$FRONTEND_PORT > /dev/null 2>&1; do
  FRONTEND_PORT=$((FRONTEND_PORT + 1))
done

unset VIRTUAL_ENV

echo "[backend]  Starting FastAPI  → http://localhost:$BACKEND_PORT"
uv run uvicorn backend.main:app --port $BACKEND_PORT --reload &
BACKEND_PID=$!

echo "[frontend] Starting Next.js  → http://localhost:$FRONTEND_PORT"
cd frontend && pnpm dev --port $FRONTEND_PORT &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
