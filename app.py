from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import re
import random
import time
import json
import subprocess
import sys

app = Flask(__name__)
CORS(app)

# Configuration
app.config['DOWNLOAD_FOLDER'] = '/tmp/downloads'
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# List of User-Agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([^&?#]+)',
        r'(?:youtu\.be\/)([^&?#]+)',
        r'(?:youtube\.com\/embed\/)([^&?#]+)',
        r'(?:youtube\.com\/v\/)([^&?#]+)',
        r'(?:youtube\.com\/shorts\/)([^&?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_video_info_ytdlp(url):
    """Get video info using yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'nocheckcertificate': True,
            'user_agent': get_random_user_agent(),
            'headers': {
                'User-Agent': get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['dash', 'hls'],
                }
            },
            'cookiefile': None,
            'socket_timeout': 30,
            'retries': 5,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        print(f"yt-dlp method failed: {str(e)}")
        return None

def get_video_info_subprocess(url):
    """Get video info using subprocess (fallback)"""
    try:
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '--no-warnings',
            '--ignore-errors',
            '--no-playlist',
            '--extractor-args', 'youtube:player_client=android,web',
            '--dump-json',
            '--skip-download',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and result.stdout:
            info = json.loads(result.stdout)
            return info
        return None
    except Exception as e:
        print(f"Subprocess failed: {str(e)}")
        return None

def get_video_info(url):
    """Get video information using multiple methods"""
    
    info = get_video_info_ytdlp(url)
    
    if not info:
        print("Primary method failed, trying subprocess fallback...")
        info = get_video_info_subprocess(url)
    
    if not info:
        return {'error': 'Unable to fetch video info. The video might be private, age-restricted, or unavailable.'}
    
    try:
        formats = []
        
        if 'formats' in info:
            for f in info['formats']:
                if not f.get('url'):
                    continue
                
                # Debug: Print format info
                print(f"Format: {f.get('format_id')} - vcodec: {f.get('vcodec')} - acodec: {f.get('acodec')}")
                    
                # Video with audio
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    height = f.get('height', 0)
                    if height >= 2160:
                        quality = '4K'
                    elif height >= 1440:
                        quality = '2K'
                    elif height >= 1080:
                        quality = '1080p'
                    elif height >= 720:
                        quality = '720p'
                    elif height >= 480:
                        quality = '480p'
                    elif height >= 360:
                        quality = '360p'
                    elif height >= 240:
                        quality = '240p'
                    elif height >= 144:
                        quality = '144p'
                    else:
                        quality = f'{height}p' if height else 'Video'
                    
                    size = f.get('filesize') or f.get('filesize_approx', 0)
                    size_str = f'{round(size / 1024 / 1024, 1)} MB' if size else 'Unknown'
                    
                    formats.append({
                        'itag': str(f.get('format_id', '')),
                        'quality': quality,
                        'size': size_str,
                        'type': 'video',
                        'ext': f.get('ext', 'mp4')
                    })
                
                # Audio only - Fix: Check for audio without video
                elif f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    bitrate = f.get('abr', '')
                    # Try to get quality from format note or use bitrate
                    if bitrate:
                        quality = f'Audio {bitrate}kbps'
                    else:
                        # Try to get quality from format note
                        format_note = f.get('format_note', '')
                        if format_note:
                            quality = f'Audio {format_note}'
                        else:
                            quality = 'Audio'
                    
                    size = f.get('filesize') or f.get('filesize_approx', 0)
                    size_str = f'{round(size / 1024 / 1024, 1)} MB' if size else 'Unknown'
                    
                    formats.append({
                        'itag': str(f.get('format_id', '')),
                        'quality': quality,
                        'size': size_str,
                        'type': 'audio',
                        'ext': f.get('ext', 'm4a')
                    })
                
                # Also add best audio-only formats that might be in a different format
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    # This is already handled above, but let's make sure we catch all
                    pass
        
        # Also look for audio formats in a different structure
        if not any(f['type'] == 'audio' for f in formats):
            # Try to extract audio formats from the formats list again with different criteria
            for f in info['formats']:
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('url'):
                    bitrate = f.get('abr', '')
                    quality = f'Audio {bitrate}kbps' if bitrate else 'Audio'
                    size = f.get('filesize') or f.get('filesize_approx', 0)
                    size_str = f'{round(size / 1024 / 1024, 1)} MB' if size else 'Unknown'
                    
                    # Check if this itag already exists
                    if not any(f2['itag'] == str(f.get('format_id', '')) for f2 in formats):
                        formats.append({
                            'itag': str(f.get('format_id', '')),
                            'quality': quality,
                            'size': size_str,
                            'type': 'audio',
                            'ext': f.get('ext', 'm4a')
                        })
        
        # Remove duplicates
        seen = set()
        unique_formats = []
        for f in formats:
            key = f"{f['type']}_{f['quality']}"
            if key not in seen:
                unique_formats.append(f)
                seen.add(key)
        
        # Sort formats: videos first, then audio
        video_formats = [f for f in unique_formats if f['type'] == 'video']
        audio_formats = [f for f in unique_formats if f['type'] == 'audio']
        
        # Sort video formats by quality
        quality_order = ['4K', '2K', '1080p', '720p', '480p', '360p', '240p', '144p']
        video_formats.sort(key=lambda x: quality_order.index(x['quality']) if x['quality'] in quality_order else 999)
        
        # Sort audio formats by bitrate (highest first)
        audio_formats.sort(key=lambda x: int(re.search(r'(\d+)', x['quality']).group(1)) if re.search(r'(\d+)', x['quality']) else 0, reverse=True)
        
        all_formats = video_formats + audio_formats
        
        # Get thumbnail
        thumbnail = info.get('thumbnail', '')
        if not thumbnail and 'thumbnails' in info:
            thumbnails = info.get('thumbnails', [])
            if thumbnails:
                thumbnail = thumbnails[-1].get('url', '')
        
        return {
            'title': info.get('title', 'Unknown'),
            'uploader': info.get('uploader', 'Unknown'),
            'views': info.get('view_count', 0),
            'duration': info.get('duration', 0),
            'thumbnail': thumbnail,
            'formats': all_formats
        }
        
    except Exception as e:
        print(f"Error processing info: {str(e)}")
        return {'error': str(e)}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/info')
def get_info():
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({'error': 'URL parameter is required'}), 400
        
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        result = get_video_info(url)
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download')
def download_video():
    try:
        url = request.args.get('url')
        itag = request.args.get('itag')
        
        if not url or not itag:
            return jsonify({'error': 'URL and itag are required'}), 400
        
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        time.sleep(random.uniform(0.5, 1.0))
        
        temp_filename = f"{video_id}_{itag}"
        output_template = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{temp_filename}.%(ext)s")
        
        ydl_opts = {
            'format': itag,
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'nocheckcertificate': True,
            'user_agent': get_random_user_agent(),
            'headers': {
                'User-Agent': get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'DNT': '1',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['dash', 'hls'],
                }
            },
            'cookiefile': None,
            'retries': 5,
            'fragment_retries': 5,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if not info:
                return jsonify({'error': 'Failed to download video'}), 500
            
            filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                ext = os.path.splitext(filename)[1]
                safe_filename = re.sub(r'[^\w\s-]', '', info.get('title', 'video'))
                safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
                safe_filename = f"{safe_filename}{ext}"
                
                return send_file(
                    filename,
                    as_attachment=True,
                    download_name=safe_filename,
                    mimetype='video/mp4'
                )
            else:
                return jsonify({'error': 'File not found'}), 404
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Starting YouTube Downloader...")
    print(f"📍 Visit: http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)