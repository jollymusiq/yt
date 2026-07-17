// script.js
class YouTubeDownloader {
    constructor() {
        this.apiUrl = 'http://localhost:5000/api';
        this.currentVideoInfo = null;
        
        // DOM elements
        this.urlInput = document.getElementById('urlInput');
        this.fetchBtn = document.getElementById('fetchBtn');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.errorMessage = document.getElementById('errorMessage');
        this.videoInfo = document.getElementById('videoInfo');
        this.progressContainer = document.getElementById('progressContainer');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        
        // Video details elements
        this.thumbnail = document.getElementById('thumbnail');
        this.title = document.getElementById('title');
        this.uploader = document.getElementById('uploader');
        this.views = document.getElementById('views');
        this.description = document.getElementById('description');
        this.duration = document.getElementById('duration');
        
        // Format containers
        this.videoFormats = document.getElementById('videoFormats');
        this.audioFormats = document.getElementById('audioFormats');
        
        // Event listeners
        this.fetchBtn.addEventListener('click', () => this.fetchVideoInfo());
        this.urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.fetchVideoInfo();
            }
        });
        
        // Check if URL is valid on paste
        this.urlInput.addEventListener('paste', () => {
            setTimeout(() => {
                const url = this.urlInput.value.trim();
                if (this.isYouTubeUrl(url)) {
                    this.fetchVideoInfo();
                }
            }, 100);
        });
    }
    
    isYouTubeUrl(url) {
        const pattern = /(https?:\/\/)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\/(watch\?v=|embed\/|v\/|.+\?v=)?([^&=%\?]{11})/;
        return pattern.test(url);
    }
    
    async fetchVideoInfo() {
        const url = this.urlInput.value.trim();
        
        if (!url) {
            this.showError('Please enter a YouTube URL');
            return;
        }
        
        if (!this.isYouTubeUrl(url)) {
            this.showError('Please enter a valid YouTube URL');
            return;
        }
        
        this.setLoading(true);
        this.hideError();
        this.hideVideoInfo();
        this.hideProgress();
        
        try {
            const response = await fetch(`${this.apiUrl}/info`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to fetch video information');
            }
            
            this.currentVideoInfo = data;
            this.displayVideoInfo(data);
            this.showVideoInfo();
            
        } catch (error) {
            this.showError(error.message || 'Failed to fetch video information. Please try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    displayVideoInfo(data) {
        // Set thumbnail
        this.thumbnail.src = data.thumbnail || 'https://via.placeholder.com/320x180?text=No+Thumbnail';
        this.thumbnail.alt = data.title;
        
        // Set video details
        this.title.textContent = data.title;
        this.uploader.textContent = data.uploader || 'Unknown';
        this.views.textContent = this.formatNumber(data.views);
        this.description.textContent = data.description || 'No description available';
        this.duration.textContent = this.formatDuration(data.duration);
        
        // Display formats
        this.displayFormats(data.formats, this.videoFormats, false);
        this.displayFormats(data.audio_formats, this.audioFormats, true);
    }
    
    displayFormats(formats, container, isAudio) {
        container.innerHTML = '';
        
        if (!formats || formats.length === 0) {
            container.innerHTML = '<p class="no-formats">No formats available</p>';
            return;
        }
        
        // Sort formats
        const sortedFormats = [...formats];
        if (!isAudio) {
            sortedFormats.sort((a, b) => {
                const aQual = parseInt(a.quality.replace('p', ''));
                const bQual = parseInt(b.quality.replace('p', ''));
                return bQual - aQual;
            });
        } else {
            sortedFormats.sort((a, b) => {
                const aBit = parseInt(a.bitrate);
                const bBit = parseInt(b.bitrate);
                return bBit - aBit;
            });
        }
        
        sortedFormats.forEach(format => {
            const btn = document.createElement('button');
            btn.className = `format-btn ${isAudio ? 'audio' : ''}`;
            
            if (isAudio) {
                btn.innerHTML = `
                    <span class="ext">${format.ext.toUpperCase()}</span>
                    <span class="quality">${format.bitrate}</span>
                    <span class="size">${this.formatFileSize(format.filesize)}</span>
                `;
            } else {
                btn.innerHTML = `
                    <span class="quality">${format.quality}</span>
                    <span class="ext">${format.ext.toUpperCase()}</span>
                    <span class="size">${this.formatFileSize(format.filesize)}</span>
                    ${format.note ? `<span class="note">${format.note}</span>` : ''}
                `;
            }
            
            btn.addEventListener('click', () => this.downloadVideo(format.format_id));
            container.appendChild(btn);
        });
    }
    
    async downloadVideo(formatId) {
        const url = this.urlInput.value.trim();
        
        if (!url || !this.currentVideoInfo) {
            this.showError('No video information available');
            return;
        }
        
        this.setLoading(true);
        this.hideError();
        this.showProgress();
        
        try {
            const response = await fetch(`${this.apiUrl}/download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    url, 
                    format_id: formatId 
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Download failed');
            }
            
            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'video.mp4';
            if (contentDisposition) {
                const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
                if (matches && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '');
                }
            }
            
            // Create download link
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);
            
            // Update progress
            this.updateProgress(100);
            setTimeout(() => this.hideProgress(), 2000);
            
        } catch (error) {
            this.showError(error.message || 'Download failed. Please try again.');
            this.hideProgress();
        } finally {
            this.setLoading(false);
        }
    }
    
    // Utility functions
    formatDuration(seconds) {
        if (!seconds) return '0:00';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
    
    formatNumber(num) {
        if (!num) return '0';
        if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B';
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }
    
    formatFileSize(bytes) {
        if (!bytes || bytes === 0) return 'Unknown';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // UI helper functions
    setLoading(loading) {
        this.fetchBtn.disabled = loading;
        this.urlInput.disabled = loading;
        if (loading) {
            this.loadingIndicator.classList.remove('hidden');
            this.fetchBtn.textContent = 'Loading...';
        } else {
            this.loadingIndicator.classList.add('hidden');
            this.fetchBtn.textContent = 'Get Video Info';
        }
    }
    
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.classList.remove('hidden');
    }
    
    hideError() {
        this.errorMessage.classList.add('hidden');
        this.errorMessage.textContent = '';
    }
    
    showVideoInfo() {
        this.videoInfo.classList.remove('hidden');
    }
    
    hideVideoInfo() {
        this.videoInfo.classList.add('hidden');
    }
    
    showProgress() {
        this.progressContainer.classList.remove('hidden');
        this.updateProgress(0);
    }
    
    hideProgress() {
        this.progressContainer.classList.add('hidden');
        this.updateProgress(0);
    }
    
    updateProgress(percent) {
        this.progressFill.style.width = `${percent}%`;
        this.progressText.textContent = `Downloading... ${Math.round(percent)}%`;
        
        if (percent >= 100) {
            this.progressText.textContent = 'Download complete! ✓';
        }
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new YouTubeDownloader();
});