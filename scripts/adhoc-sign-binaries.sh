#!/usr/bin/env bash
# Ad-hoc sign the bundled binaries that get embedded into the Scribble .app.
#
# Why: On recent macOS (especially arm64), executables without *any* signature
# are killed by the kernel. Ad-hoc signing (`codesign --sign -`) satisfies that
# check without requiring an Apple Developer cert. This does NOT fix Gatekeeper
# warnings on first launch — that requires Developer ID + notarization — but it
# does prevent silent runtime kills of the Python backend and ffmpeg subprocess.
#
# Run this before `npm run tauri:build`. The release workflow also runs it.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BINARIES_DIR="$REPO_ROOT/frontend/src-tauri/binaries"

if [ ! -d "$BINARIES_DIR" ]; then
    echo "error: binaries directory not found at $BINARIES_DIR" >&2
    exit 1
fi

sign_if_present() {
    local bin="$1"
    if [ -f "$bin" ]; then
        echo "ad-hoc signing: $bin"
        codesign --force --sign - --timestamp=none --options runtime "$bin"
    else
        echo "skip (not found): $bin"
    fi
}

sign_if_present "$BINARIES_DIR/scribble-backend-aarch64-apple-darwin"
sign_if_present "$BINARIES_DIR/ffmpeg-aarch64-apple-darwin"

echo "done."
