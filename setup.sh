#!/bin/bash

# Simple run script for YouTube Downloader

echo "🚀 Starting YouTube Downloader..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if requirements are installed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update requirements
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p templates static downloads

# Run the application
echo "🚀 Starting server..."
python3 app.py