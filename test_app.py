# test_smart.py
import requests
import json

def get_available_formats():
    """Get available formats for the video"""
    print("📋 Getting available formats...")
    
    response = requests.post(
        "http://127.0.0.1:5000/api/info",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            formats = data.get('formats', [])
            print(f"\n📊 Available formats for this video:")
            print("-" * 60)
            for fmt in formats[:10]:  # Show first 10 formats
                has_audio = "🎵" if fmt.get('has_audio') else "🔇"
                size_mb = fmt.get('filesize', 0) / (1024 * 1024) if fmt.get('filesize') else 0
                print(f"   {has_audio} {fmt['quality']} | Format ID: {fmt['format_id']} | Ext: {fmt['ext']} | {size_mb:.1f} MB")
            return formats
    else:
        print(f"❌ Error: {response.text}")
        return []

def test_download_with_audio():
    """Test download with smart format selection"""
    
    print("=" * 60)
    print("🎬 Testing video with audio - Smart Selection")
    print("=" * 60)
    
    # First, get available formats
    formats = get_available_formats()
    
    if not formats:
        print("❌ No formats found!")
        return
    
    # Test different formats
    test_formats = [
        ("best", "Best Quality"),
        ("18", "360p"),
        ("22", "720p"),
        ("37", "1080p"),
    ]
    
    print("\n📥 Testing downloads with audio:")
    print("-" * 60)
    
    for format_id, quality in test_formats:
        print(f"\n🔍 Testing {quality} (format_id: {format_id})")
        
        try:
            response = requests.post(
                "http://127.0.0.1:5000/api/download",
                json={
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "format_id": format_id
                },
                timeout=180
            )
            
            if response.status_code == 200:
                filename = f"smart_{format_id}.mp4"
                with open(filename, "wb") as f:
                    f.write(response.content)
                
                size = len(response.content) / (1024 * 1024)
                print(f"   ✅ SUCCESS!")
                print(f"      📁 {filename} ({size:.1f} MB)")
                print(f"      🎵 Audio included (using best audio merge)")
                break  # Stop on first success
            else:
                error = response.json()
                print(f"   ❌ Error: {error.get('error', 'Unknown')[:100]}")
                print(f"   🔄 Trying next format...")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
            print(f"   🔄 Trying next format...")
    
    print("\n" + "=" * 60)
    print("✅ Test complete! Check the downloaded file for audio.")
    print("💡 If the file has no audio, check that ffmpeg.exe is in the folder.")
    print("=" * 60)

if __name__ == "__main__":
    test_download_with_audio()