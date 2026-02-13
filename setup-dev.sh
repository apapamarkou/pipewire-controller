#!/bin/bash
# Quick setup script for PipeWire Controller development

set -e

echo "🎛️  PipeWire Controller - Development Setup"
echo "==========================================="
echo

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.10+ required. Found: $python_version"
    exit 1
fi
echo "✅ Python $python_version"

# Check PipeWire
echo
echo "📋 Checking PipeWire installation..."
if ! command -v pw-metadata &> /dev/null; then
    echo "❌ pw-metadata not found. Please install PipeWire."
    exit 1
fi
echo "✅ PipeWire installed"

# Create virtual environment
echo
echo "🔧 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi

# Activate and install
echo
echo "📦 Installing dependencies..."

# If shell is bash,zsh:
source venv/bin/activate
# If shell is fish:
# source venv/bin/activate.fish

pip install --upgrade pip
pip install -e ".[dev]"
pip install build twine

echo
echo "✅ Setup complete!"
echo
echo "Next steps:"
echo "  1. Activate environment: source venv/bin/activate"
echo "  2. Run tests: pytest"
echo "  3. Run application: pipewire-controller"
echo "  4. Format code: black src/ tests/"
echo "  5. Lint code: ruff check src/ tests/"
echo
