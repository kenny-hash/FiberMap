#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_HOST="${FIBERMAP_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${FIBERMAP_BACKEND_PORT:-8000}"
FRONTEND_HOST="${FIBERMAP_FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FIBERMAP_FRONTEND_PORT:-5173}"
SKIP_INSTALL="${FIBERMAP_SKIP_INSTALL:-0}"

BACKEND_PID=""
FRONTEND_PID=""
CLEANED_UP=0

log() {
  printf '\033[1;34m[快速启动]\033[0m %s\n' "$*"
}

error() {
  printf '\033[1;31m[快速启动]\033[0m %s\n' "$*" >&2
}

require_command() {
  local command_name="$1"
  local install_hint="$2"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    error "缺少命令：$command_name"
    error "$install_hint"
    exit 1
  fi
}

cleanup() {
  if [[ "$CLEANED_UP" == "1" ]]; then
    return
  fi
  CLEANED_UP=1

  log "正在停止本地服务..."
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local retries="${3:-40}"

  for _ in $(seq 1 "$retries"); do
    if curl --silent --fail "$url" >/dev/null 2>&1; then
      log "$name 已就绪：$url"
      return 0
    fi
    sleep 0.5
  done

  error "$name 启动超时：$url"
  return 1
}

trap cleanup EXIT INT TERM

require_command uv "请先安装 uv：https://docs.astral.sh/uv/getting-started/installation/"
require_command npm "请先安装 Node.js/npm：https://nodejs.org/"
require_command curl "请先安装 curl 后重试。"

cd "$ROOT_DIR"

if [[ "$SKIP_INSTALL" != "1" ]]; then
  log "同步后端 Python 依赖..."
  uv sync --dev

  log "安装/更新前端依赖..."
  npm --prefix "$FRONTEND_DIR" install
else
  log "已设置 FIBERMAP_SKIP_INSTALL=1，跳过依赖安装。"
fi

log "启动后端：http://$BACKEND_HOST:$BACKEND_PORT"
uv run uvicorn app.main:app \
  --app-dir "$ROOT_DIR/backend" \
  --host "$BACKEND_HOST" \
  --port "$BACKEND_PORT" \
  --reload &
BACKEND_PID="$!"

wait_for_url "http://$BACKEND_HOST:$BACKEND_PORT/api/health" "后端"

log "启动前端：http://localhost:$FRONTEND_PORT"
VITE_API_BASE="http://$BACKEND_HOST:$BACKEND_PORT" \
  npm --prefix "$FRONTEND_DIR" run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" &
FRONTEND_PID="$!"

cat <<INFO

FiberMap 本地开发环境已启动：
  - 前端：http://localhost:$FRONTEND_PORT
  - 后端：http://$BACKEND_HOST:$BACKEND_PORT
  - 健康检查：http://$BACKEND_HOST:$BACKEND_PORT/api/health

按 Ctrl+C 可同时停止前后端服务。
如需跳过依赖安装：FIBERMAP_SKIP_INSTALL=1 ./scripts/start_local.sh

INFO

wait -n "$BACKEND_PID" "$FRONTEND_PID"
