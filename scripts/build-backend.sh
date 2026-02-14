#!/bin/bash
set -e

echo "Building Python backend for macOS..."

cd backend

# Ensure virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies including PyInstaller
echo "Installing dependencies..."
pip install -r requirements.txt

# Create output directory
mkdir -p ../frontend/src-tauri/binaries

# Build for Apple Silicon (arm64)
echo "Building for Apple Silicon (arm64)..."
# Modify spec file to target arm64
sed -i.bak "s/target_arch='[^']*'/target_arch='arm64'/" backend.spec
pyinstaller --clean backend.spec
cp dist/scribble-backend/scribble-backend ../frontend/src-tauri/binaries/scribble-backend-aarch64-apple-darwin
chmod +x ../frontend/src-tauri/binaries/scribble-backend-aarch64-apple-darwin

# Build for Intel (x86_64)
echo "Building for Intel (x86_64)..."
# Modify spec file to target x86_64
sed -i.bak "s/target_arch='[^']*'/target_arch='x86_64'/" backend.spec
pyinstaller --clean backend.spec
cp dist/scribble-backend/scribble-backend ../frontend/src-tauri/binaries/scribble-backend-x86_64-apple-darwin
chmod +x ../frontend/src-tauri/binaries/scribble-backend-x86_64-apple-darwin

# Restore original spec file
rm backend.spec.bak

deactivate

echo "Backend binaries built successfully:"
ls -lh ../frontend/src-tauri/binaries/scribble-backend-*
