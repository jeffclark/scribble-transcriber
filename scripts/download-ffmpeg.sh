#!/bin/bash
set -e

echo "Downloading FFmpeg static binaries for macOS..."

BINARIES_DIR="frontend/src-tauri/binaries"
mkdir -p "$BINARIES_DIR"

# FFmpeg SHA-256 checksums (update these with actual values from evermeet.cx)
# These should be verified against the official checksums
FFMPEG_ARM64_SHA256="PLACEHOLDER_UPDATE_WITH_ACTUAL_CHECKSUM"
FFMPEG_X64_SHA256="PLACEHOLDER_UPDATE_WITH_ACTUAL_CHECKSUM"

# Download for Apple Silicon (arm64)
if [ ! -f "$BINARIES_DIR/ffmpeg-aarch64-apple-darwin" ]; then
    echo "Downloading FFmpeg for Apple Silicon..."
    curl -L https://evermeet.cx/ffmpeg/getrelease/arm64/ffmpeg/zip -o ffmpeg-arm64.zip

    # Verify checksum
    if [ "$FFMPEG_ARM64_SHA256" != "PLACEHOLDER_UPDATE_WITH_ACTUAL_CHECKSUM" ]; then
        echo "Verifying checksum..."
        echo "$FFMPEG_ARM64_SHA256  ffmpeg-arm64.zip" | shasum -a 256 -c - || {
            echo "❌ FFmpeg checksum mismatch! Possible tampering detected."
            echo "Expected: $FFMPEG_ARM64_SHA256"
            echo "If you trust the source, update the checksum in this script."
            rm ffmpeg-arm64.zip
            exit 1
        }
        echo "✓ Checksum verified"
    else
        echo "⚠️  WARNING: Checksum verification skipped (placeholder value)"
        echo "⚠️  Update FFMPEG_ARM64_SHA256 in this script with actual checksum"
    fi

    unzip -o ffmpeg-arm64.zip
    mv ffmpeg "$BINARIES_DIR/ffmpeg-aarch64-apple-darwin"
    chmod +x "$BINARIES_DIR/ffmpeg-aarch64-apple-darwin"
    rm ffmpeg-arm64.zip
    echo "✓ Apple Silicon FFmpeg downloaded"
else
    echo "✓ Apple Silicon FFmpeg already exists"
fi

# Download for Intel (x86_64)
if [ ! -f "$BINARIES_DIR/ffmpeg-x86_64-apple-darwin" ]; then
    echo "Downloading FFmpeg for Intel..."
    curl -L https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip -o ffmpeg-x64.zip

    # Verify checksum
    if [ "$FFMPEG_X64_SHA256" != "PLACEHOLDER_UPDATE_WITH_ACTUAL_CHECKSUM" ]; then
        echo "Verifying checksum..."
        echo "$FFMPEG_X64_SHA256  ffmpeg-x64.zip" | shasum -a 256 -c - || {
            echo "❌ FFmpeg checksum mismatch! Possible tampering detected."
            echo "Expected: $FFMPEG_X64_SHA256"
            echo "If you trust the source, update the checksum in this script."
            rm ffmpeg-x64.zip
            exit 1
        }
        echo "✓ Checksum verified"
    else
        echo "⚠️  WARNING: Checksum verification skipped (placeholder value)"
        echo "⚠️  Update FFMPEG_X64_SHA256 in this script with actual checksum"
    fi

    unzip -o ffmpeg-x64.zip
    mv ffmpeg "$BINARIES_DIR/ffmpeg-x86_64-apple-darwin"
    chmod +x "$BINARIES_DIR/ffmpeg-x86_64-apple-darwin"
    rm ffmpeg-x64.zip
    echo "✓ Intel FFmpeg downloaded"
else
    echo "✓ Intel FFmpeg already exists"
fi

echo "FFmpeg binaries ready:"
ls -lh "$BINARIES_DIR/ffmpeg-*"
echo ""
echo "⚠️  SECURITY NOTE: Update checksums in this script before production use"
echo "   Get official checksums from: https://evermeet.cx/ffmpeg/"
