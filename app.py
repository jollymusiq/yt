from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import re
import json
import sys

app = Flask(__name__)
CORS(app)

# Configuration
app.config['DOWNLOAD_FOLDER'] = 'downloads'
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

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

def get_video_info(url):
    """Get video information using yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'nocheckcertificate': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return {'error': 'Failed to fetch video info'}
            
            formats = []
            
            if 'formats' in info:
                for f in info['formats']:
                    # Skip formats without download URL
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
            
            return {
                'title': info.get('title', 'Unknown'),
                'uploader': info.get('uploader', 'Unknown'),
                'views': info.get('view_count', 0),
                'duration': info.get('duration', 0),
                'thumbnail': thumbnail,
                'formats': unique_formats
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
        
        ydl_opts = {
            'format': itag,
            'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'nocheckcertificate': True,
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

# Error handler for 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

if __name__ == '__main__':
    print("🚀 Starting YouTube Downloader...")
    print(f"📍 Visit: http://127.0.0.1:5000")
    app.run(debug=True, port=5000, host='127.0.0.1')