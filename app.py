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
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0'
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

def get_video_info_method1(url):
    """Method 1: Standard yt-dlp with mobile client"""
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
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'no-cache',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'ios'],
                    'skip': ['dash', 'hls'],
                    'use_ios_api': True,
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        print(f"Method 1 failed: {str(e)}")
        return None

def get_video_info_method2(url):
    """Method 2: Using yt-dlp with cookies and different client"""
    try:
        # Use a different approach with more permissive settings
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'ignoreerrors': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                    'skip': ['dash', 'hls'],
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        print(f"Method 2 failed: {str(e)}")
        return None

def get_video_info_method3(url):
    """Method 3: Using yt-dlp with --no-playlist and different format"""
    try:
        # Use subprocess to run yt-dlp directly with more options
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
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            info = json.loads(result.stdout)
            return info
        return None
    except Exception as e:
        print(f"Method 3 failed: {str(e)}")
        return None

def get_video_info_method4(url):
    """Method 4: Using yt-dlp with cookies from browser (if available)"""
    try:
        # Try to use browser cookies if available (Chrome, Firefox, etc.)
        cookie_paths = [
            os.path.expanduser('~/.config/google-chrome/Default/Cookies'),
            os.path.expanduser('~/.mozilla/firefox/*/cookies.sqlite'),
            os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Cookies'),
        ]
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'nocheckcertificate': True,
            'user_agent': get_random_user_agent(),
        }
        
        # Try to use cookies if they exist
        for cookie_path in cookie_paths:
            if os.path.exists(cookie_path.replace('*', 'default')):
                ydl_opts['cookiefile'] = cookie_path
                break
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        print(f"Method 4 failed: {str(e)}")
        return None

def get_video_info(url):
    """Get video information using multiple methods"""
    
    # Try different methods in order
    methods = [
        get_video_info_method1,
        get_video_info_method2,
        get_video_info_method3,
        get_video_info_method4
    ]
    
    info = None
    for i, method in enumerate(methods, 1):
        print(f"Trying method {i}...")
        info = method(url)
        if info:
            print(f"Method {i} succeeded!")
            break
        time.sleep(random.uniform(0.5, 1.0))
    
    if not info:
        return {'error': 'Unable to fetch video info. The video might be private, age-restricted, or unavailable. Try a different video.'}
    
    # Process the info
    try:
        formats = []
        
        if 'formats' in info:
            for f in info['formats']:
                if not f.get('url'):
                    continue
                    
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
                
                # Audio only
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    bitrate = f.get('abr', '')
                    quality = f'Audio {bitrate}kbps' if bitrate else 'Audio'
                    
                    size = f.get('filesize') or f.get('filesize_approx', 0)
                    size_str = f'{round(size / 1024 / 1024, 1)} MB' if size else 'Unknown'
                    
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
        
        # Sort formats by quality
        quality_order = ['4K', '2K', '1080p', '720p', '480p', '360p', '240p', '144p']
        unique_formats.sort(key=lambda x: (
            0 if x['type'] == 'video' else 1,
            quality_order.index(x['quality']) if x['quality'] in quality_order else 999
        ))
        
        # Get thumbnail
        thumbnail = info.get('thumbnail', '')
        if not thumbnail and 'thumbnails' in info:
            thumbnails = info.get('thumbnails', [])
            if thumbnails:
                thumbnail = thumbnails[-1].get('url', '')
        
        # Get video ID
        video_id = info.get('id', '')
        if not video_id:
            video_id = extract_video_id(url)
        
        return {
            'title': info.get('title', 'Unknown'),
            'uploader': info.get('uploader', 'Unknown'),
            'views': info.get('view_count', 0),
            'duration': info.get('duration', 0),
            'thumbnail': thumbnail,
            'formats': unique_formats,
            'video_id': video_id
        }
        
    except Exception as e:
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
        
        # Random delay
        time.sleep(random.uniform(0.5, 1.0))
        
        # Use a unique filename
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
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if not info:
                return jsonify({'error': 'Failed to download video'}), 500
            
            # Find the downloaded file
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
    print("📥 Using multiple extraction methods...")
    app.run(host='0.0.0.0', port=port, debug=True)