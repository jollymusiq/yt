#!/bin/bash

# GitHub Workspaces Setup Script

echo "🚀 Setting up YouTube Downloader for GitHub Workspaces..."

# Update package list
sudo apt-get update

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Install yt-dlp
echo "📦 Installing yt-dlp..."
pip install yt-dlp --upgrade

# Create directories
mkdir -p templates static downloads

# Check if index.html exists
if [ ! -f "templates/index.html" ]; then
    echo "⚠️  templates/index.html not found. Creating placeholder..."
    cat > templates/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head><title>YouTube Downloader</title></head>
<body>
    <h1>🎬 YouTube Downloader</h1>
    <p>Please add your index.html to the templates directory.</p>
</body>
</html>
EOF
fi

echo "✅ Setup complete!"
echo "🚀 Run: python app.py"
echo "🌐 Access: http://localhost:5000"