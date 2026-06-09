#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/Users/mo/Documents/hyperalpha-ai-trading"
LABEL="com.hyperalpha.ai-trading-local"
SOURCE_PLIST="$PROJECT_ROOT/scripts/local-dev/$LABEL.plist"
SOURCE_SUPERVISOR="$PROJECT_ROOT/scripts/local-dev/ai_trading_local_supervisor.sh"
SUPPORT_DIR="$HOME/Library/Application Support/HyperAlpha"
TARGET_SUPERVISOR="$SUPPORT_DIR/ai_trading_local_supervisor.sh"
TARGET_PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
TARGET_LOG_DIR="$SUPPORT_DIR/logs/local-dev"
RUNTIME_ROOT="$SUPPORT_DIR/runtime/hyperalpha-ai-trading"
RUNTIME_BACKEND="$RUNTIME_ROOT/backend"
RUNTIME_SITE_PACKAGES="$RUNTIME_BACKEND/.venv/lib/python3.13/site-packages"

mkdir -p "$HOME/Library/LaunchAgents" "$SUPPORT_DIR" "$TARGET_LOG_DIR" "$RUNTIME_ROOT"

rsync -a --delete \
  --exclude ".git" \
  --exclude "logs/local-dev" \
  --exclude "frontend/node_modules/.vite" \
  "$PROJECT_ROOT/" "$RUNTIME_ROOT/"

if [[ -f "$RUNTIME_SITE_PACKAGES/_editable_impl_hyper_alpha_arena_backend.pth" ]]; then
  printf '%s\n' "$RUNTIME_BACKEND" >"$RUNTIME_SITE_PACKAGES/_editable_impl_hyper_alpha_arena_backend.pth"
fi

if [[ -f "$RUNTIME_SITE_PACKAGES/hyper_alpha_arena_backend-0.9.12.dist-info/direct_url.json" ]]; then
  printf '{"url":"file://%s","dir_info":{"editable":true}}\n' "$RUNTIME_BACKEND" >"$RUNTIME_SITE_PACKAGES/hyper_alpha_arena_backend-0.9.12.dist-info/direct_url.json"
fi

cp -X "$SOURCE_SUPERVISOR" "$TARGET_SUPERVISOR"
chmod +x "$TARGET_SUPERVISOR"
cp "$SOURCE_PLIST" "$TARGET_PLIST"

launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed and started $LABEL"
