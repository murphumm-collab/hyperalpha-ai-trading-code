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
RUNTIME_SYNC_METADATA="$RUNTIME_ROOT/.hyperalpha-runtime-sync.json"

source_tree_digest() {
  python3 - "$PROJECT_ROOT" <<'PY'
import hashlib
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
result = subprocess.run(
    ["git", "-C", str(root), "ls-files", "-z"],
    check=True,
    capture_output=True,
)
paths = [path.decode("utf-8", errors="surrogateescape") for path in result.stdout.split(b"\0") if path]
digest = hashlib.sha256()
for relative_path in sorted(paths):
    path = root / relative_path
    if not path.is_file():
        continue
    digest.update(relative_path.encode("utf-8", errors="surrogateescape"))
    digest.update(b"\0")
    digest.update(path.read_bytes())
    digest.update(b"\0")
print(digest.hexdigest())
PY
}

mkdir -p "$HOME/Library/LaunchAgents" "$SUPPORT_DIR" "$TARGET_LOG_DIR" "$RUNTIME_ROOT"

SOURCE_GIT_BRANCH="$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || true)"
SOURCE_GIT_COMMIT="$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || true)"
SOURCE_TREE_DIGEST="$(source_tree_digest)"
SYNCED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

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

python3 - "$RUNTIME_SYNC_METADATA" "$PROJECT_ROOT" "$RUNTIME_ROOT" "$SOURCE_GIT_BRANCH" "$SOURCE_GIT_COMMIT" "$SOURCE_TREE_DIGEST" "$SYNCED_AT" <<'PY'
import json
import sys
from pathlib import Path

metadata_path = Path(sys.argv[1])
payload = {
    "version": "hyperalpha.local_runtime_sync.v1",
    "source_root": sys.argv[2],
    "runtime_root": sys.argv[3],
    "source_git_branch": sys.argv[4],
    "source_git_commit": sys.argv[5],
    "source_tree_digest": sys.argv[6],
    "synced_at": sys.argv[7],
}
metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

cp -X "$SOURCE_SUPERVISOR" "$TARGET_SUPERVISOR"
chmod +x "$TARGET_SUPERVISOR"
cp "$SOURCE_PLIST" "$TARGET_PLIST"

launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed and started $LABEL"
