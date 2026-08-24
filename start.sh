#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "  🚀 Starting Automated Video Dubbing Engine...          "
echo "=========================================================="

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg is not installed. Installing FFmpeg..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y ffmpeg
    else
        echo "❌ Please install FFmpeg on your operating system."
        exit 1
    fi
fi

# Check Python Dependencies
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "📦 Installing Python requirements..."
pip install -r requirements.txt

# Run server
echo "🌟 Launching Server on http://0.0.0.0:8000"
python run.py