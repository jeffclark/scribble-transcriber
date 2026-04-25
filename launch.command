#!/bin/bash
# Double-click this file in Finder to build (if needed) and launch Scribble.
# Rebuilds only when source files are newer than the built .app or bundled binaries.

set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

BACKEND_BIN="frontend/src-tauri/binaries/scribble-backend-aarch64-apple-darwin"
FFMPEG_BIN="frontend/src-tauri/binaries/ffmpeg-aarch64-apple-darwin"
APP_PATH="frontend/src-tauri/target/release/bundle/macos/Scribble.app"
APP_EXE="$APP_PATH/Contents/MacOS/Scribble"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
step() { printf '\n\033[1;34m▶ %s\033[0m\n' "$*"; }
ok()   { printf '\033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!\033[0m %s\n' "$*"; }

pause_on_exit() {
  local code=$?
  if [ "$code" -ne 0 ]; then
    printf '\n\033[31m✗ Launch failed (exit %d).\033[0m Press any key to close.\n' "$code"
    read -rsn 1 || true
  fi
}
trap pause_on_exit EXIT

is_stale() {
  local target="$1"; shift
  [ ! -e "$target" ] && return 0
  local src
  for src in "$@"; do
    [ -e "$src" ] || continue
    if [ -n "$(find "$src" -type f -newer "$target" -print -quit 2>/dev/null)" ]; then
      return 0
    fi
  done
  return 1
}

require() {
  local name="$1" hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    warn "Missing prerequisite: $name"
    echo "  Install: $hint"
    exit 1
  fi
}

bold "Scribble launcher — building from $ROOT"

step "Checking prerequisites"
require python3 "brew install python@3.11"
require node    "brew install node"
require npm     "brew install node"
require cargo   "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
ok "Toolchain present"

step "Backend binary"
if is_stale "$BACKEND_BIN" backend/src backend/requirements.txt backend/backend.spec; then
  (
    cd backend
    if [ ! -d .venv ]; then
      echo "Creating backend/.venv"
      python3 -m venv .venv
    fi
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    sed -i.bak "s/target_arch='[^']*'/target_arch='arm64'/" backend.spec
    pyinstaller --clean --noconfirm backend.spec
    mv backend.spec.bak backend.spec
    mkdir -p ../frontend/src-tauri/binaries
    cp dist/scribble-backend/scribble-backend "../$BACKEND_BIN"
    chmod +x "../$BACKEND_BIN"
    deactivate
  )
  ok "Built scribble-backend (arm64)"
else
  ok "scribble-backend up to date"
fi

step "ffmpeg binary"
if [ ! -e "$FFMPEG_BIN" ]; then
  ./scripts/download-ffmpeg.sh
  ok "Downloaded ffmpeg"
else
  ok "ffmpeg already present"
fi

step "Ad-hoc signing bundled binaries"
./scripts/adhoc-sign-binaries.sh >/dev/null
ok "Signed"

step "Tauri app bundle"
APP_SOURCES=(
  frontend/src
  frontend/src-tauri/src
  frontend/src-tauri/Cargo.toml
  frontend/src-tauri/tauri.conf.json
  frontend/package.json
  frontend/index.html
  "$BACKEND_BIN"
  "$FFMPEG_BIN"
)
if is_stale "$APP_EXE" "${APP_SOURCES[@]}"; then
  (
    cd frontend
    if [ ! -d node_modules ]; then
      echo "Installing npm dependencies"
      npm ci 2>/dev/null || npm install
    fi
    npm run tauri:build
  )
  ok "Built Scribble.app"
else
  ok "Scribble.app up to date"
fi

step "Launching Scribble"
open "$APP_PATH"
ok "Launched — closing this window"
