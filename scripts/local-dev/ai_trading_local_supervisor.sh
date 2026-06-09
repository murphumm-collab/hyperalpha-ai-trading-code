#!/usr/bin/env bash
set -euo pipefail

DEFAULT_PROJECT_ROOT="/Users/mo/Documents/hyperalpha-ai-trading"
PROJECT_ROOT="${HYPERALPHA_PROJECT_ROOT:-$DEFAULT_PROJECT_ROOT}"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
SUPPORT_DIR="${HOME}/Library/Application Support/HyperAlpha"
LOG_DIR="${HYPERALPHA_LOCAL_DEV_LOG_DIR:-$SUPPORT_DIR/logs/local-dev}"
PID_DIR="$LOG_DIR/pids"
BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"
FRONTEND_NODE="/Users/mo/.hermes/node/bin/node"
FRONTEND_VITE_JS="$PROJECT_ROOT/node_modules/.pnpm/vite@4.5.14_@types+node@20.19.23/node_modules/vite/bin/vite.js"
START_GRACE_SECONDS=90

export PATH="/Users/mo/.hermes/node/bin:/opt/homebrew/bin:/usr/local/bin:${HOME}/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$LOG_DIR" "$PID_DIR"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_DIR/supervisor.log"
}

port_open() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

docker_ready() {
  docker info >/dev/null 2>&1
}

start_docker() {
  if docker_ready; then
    return
  fi
  log "Starting Docker Desktop"
  open -a Docker || true
  for _ in $(seq 1 120); do
    if docker_ready; then
      log "Docker is ready"
      return
    fi
    sleep 2
  done
  log "Docker did not become ready within timeout"
}

ensure_postgres() {
  start_docker
  if ! docker_ready; then
    return
  fi
  if port_open 5432; then
    return
  fi
  log "Starting compose Postgres"
  (cd "$PROJECT_ROOT" && docker compose up -d postgres) >>"$LOG_DIR/postgres.log" 2>&1 || log "Postgres start failed"
}

start_frontend() {
  stop_stale_pid_file "$PID_DIR/frontend.pid" 5174 "frontend"
  if pid_file_running "$PID_DIR/frontend.pid"; then
    return
  fi
  if port_open 5174; then
    return
  fi
  if [[ ! -x "$FRONTEND_NODE" ]]; then
    log "Frontend Node binary missing or not executable: $FRONTEND_NODE"
    return
  fi
  if [[ ! -f "$FRONTEND_VITE_JS" ]]; then
    log "Frontend Vite JS entry missing: $FRONTEND_VITE_JS"
    return
  fi
  log "Starting frontend on 5174"
  (
    cd "$FRONTEND_DIR"
    nohup "$FRONTEND_NODE" "$FRONTEND_VITE_JS" --host 127.0.0.1 --port 5174 --strictPort >>"$LOG_DIR/frontend.log" 2>&1 &
    echo $! >"$PID_DIR/frontend.pid"
  )
}

start_mock_gateway() {
  stop_stale_pid_file "$PID_DIR/mock-gateway.pid" 5621 "mock gateway"
  if pid_file_running "$PID_DIR/mock-gateway.pid"; then
    return
  fi
  if port_open 5621; then
    return
  fi
  if [[ ! -x "$BACKEND_PYTHON" ]]; then
    log "Backend Python binary missing or not executable: $BACKEND_PYTHON"
    return
  fi
  log "Starting AI Trading mock gateway on 5621"
  (
    cd "$BACKEND_DIR"
    nohup "$BACKEND_PYTHON" -m uvicorn dev_ai_trading_signal_gateway:app --port 5621 --host 127.0.0.1 >>"$LOG_DIR/mock-gateway.log" 2>&1 &
    echo $! >"$PID_DIR/mock-gateway.pid"
  )
}

start_backend() {
  stop_stale_pid_file "$PID_DIR/backend.pid" 8802 "backend"
  if pid_file_running "$PID_DIR/backend.pid"; then
    return
  fi
  if port_open 8802; then
    return
  fi
  if [[ ! -x "$BACKEND_PYTHON" ]]; then
    log "Backend Python binary missing or not executable: $BACKEND_PYTHON"
    return
  fi
  ensure_postgres
  start_mock_gateway
  log "Starting backend on 8802"
  (
    cd "$BACKEND_DIR"
    DATABASE_URL="postgresql://alpha_user:alpha_pass@127.0.0.1:5432/alpha_arena" \
    SNAPSHOT_DATABASE_URL="postgresql://alpha_user:alpha_pass@127.0.0.1:5432/alpha_snapshots" \
    AI_TRADING_SIGNAL_GATEWAY_ENABLED=true \
    AI_TRADING_SIGNAL_GATEWAY_URL="http://127.0.0.1:5621/api/ai-trading/signals" \
    AI_TRADING_SIGNAL_GATEWAY_TOKEN="local-mock-token" \
    nohup "$BACKEND_PYTHON" -m uvicorn main:app --port 8802 --host 127.0.0.1 >>"$LOG_DIR/backend.log" 2>&1 &
    echo $! >"$PID_DIR/backend.pid"
  )
}

stop_pid_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    return
  fi
  local pid
  pid="$(cat "$file" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$file"
}

pid_file_running() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    return 1
  fi
  local pid
  pid="$(cat "$file" 2>/dev/null || true)"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

stop_stale_pid_file() {
  local file="$1"
  local port="$2"
  local name="$3"
  if port_open "$port"; then
    return
  fi
  if [[ ! -f "$file" ]]; then
    return
  fi
  local pid
  pid="$(cat "$file" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
    local now
    local started
    local age
    now="$(date +%s)"
    started="$(stat -f %m "$file" 2>/dev/null || echo "$now")"
    age=$((now - started))
    if (( age < START_GRACE_SECONDS )); then
      log "Waiting for $name process $pid to open port $port (${age}s/${START_GRACE_SECONDS}s)"
      return
    fi
    log "Stopping stale $name process $pid because port $port is not listening"
    kill "$pid" >/dev/null 2>&1 || true
    sleep 2
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  fi
  rm -f "$file"
}

cleanup() {
  log "Stopping managed local services"
  stop_pid_file "$PID_DIR/backend.pid"
  stop_pid_file "$PID_DIR/mock-gateway.pid"
  stop_pid_file "$PID_DIR/frontend.pid"
}

trap cleanup INT TERM

log "HyperAlpha AI Trading local supervisor started"

while true; do
  ensure_postgres
  start_mock_gateway
  start_backend
  start_frontend
  sleep 30
done
