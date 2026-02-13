#!/bin/bash
# Run tests in headless mode locally

set -e

echo "🧪 Running tests in headless mode..."
echo

# Check if xvfb is available
if command -v xvfb-run &> /dev/null; then
    echo "✓ Using xvfb-run for headless testing"
    xvfb-run -a --server-args="-screen 0 1920x1080x24" pytest "$@"
else
    echo "⚠ xvfb not found, using offscreen platform"
    QT_QPA_PLATFORM=offscreen pytest "$@"
fi
