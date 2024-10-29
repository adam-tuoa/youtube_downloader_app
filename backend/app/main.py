# backend/app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from yt_dlp import YoutubeDL
import os
import tempfile
import shutil
from typing import List, Optional

# Define base models first
class VideoURL(BaseModel):
    url: str
    format_id: Optional[str] = None

class VideoFormat(BaseModel):
    format_id: str
    ext: str
    resolution: str
    filesize: Optional[int]
    note: str
    has_video: bool
    has_audio: bool
    quality: str = ""

# Initialize FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_filesize(size_bytes: Optional[int]) -> str:
    """Convert bytes to human readable format"""
    if not size_bytes:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"

def get_ydl_opts(format_id=None):
    """Get YouTube-DL options with better format handling."""
    if format_id:
        # If specific format is requested, use it
        format_spec = format_id
    else:
        # Otherwise use format specification that ensures we get both video and audio
        format_spec = 'bv*+ba/b'  # Best video + best audio / fallback to best combined format
        
    return {
        'format': format_spec,
        'format_sort': ['res', 'ext:mp4:m4a', 'size', 'br'],
        'merge_output_format': 'mp4',  # Force merge into MP4
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',  # Ensure final format is MP4
        }],
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        },
    }

@app.get("/")
async def read_root():
    return {"message": "YouTube Downloader API is running"}

@app.post("/formats")
async def get_formats(video: VideoURL):
    try:
        ydl_opts = get_ydl_opts()
        
        with YoutubeDL(ydl_opts) as ydl:
            print(f"Extracting info for URL: {video.url}")
            info = ydl.extract_info(video.url, download=False)
            
            formats = []
            # First collect complete formats (those with both video and audio)
            complete_formats = [f for f in info['formats'] 
                              if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
            
            # Then collect best video-only formats
            video_formats = [f for f in info['formats'] 
                           if f.get('vcodec') != 'none' and f.get('acodec') == 'none']
            
            # Get the best audio format
            audio_formats = [f for f in info['formats'] 
                           if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
            best_audio = max(audio_formats, key=lambda x: x.get('filesize', 0)) if audio_formats else None
            
            # Process complete formats
            for f in complete_formats:
                resolution = f.get('resolution', 'N/A')
                height = f.get('height', 0)
                width = f.get('width', 0)
                
                if resolution == 'N/A' and height:
                    resolution = f"{width}x{height}"
                
                quality_parts = []
                if f.get('format_note'):
                    quality_parts.append(f.get('format_note'))
                if f.get('fps'):
                    quality_parts.append(f"{f.get('fps')}fps")
                
                quality = " - ".join(filter(None, quality_parts))
                
                format_info = VideoFormat(
                    format_id=f['format_id'],
                    ext=f.get('ext', 'mp4'),
                    resolution=resolution,
                    filesize=f.get('filesize'),
                    note=f"{format_filesize(f.get('filesize'))} - {quality} (Complete)",
                    has_video=True,
                    has_audio=True,
                    quality=quality
                )
                formats.append(format_info)
            
            # Process video formats that need to be merged with audio
            if best_audio:
                for f in video_formats:
                    resolution = f.get('resolution', 'N/A')
                    height = f.get('height', 0)
                    width = f.get('width', 0)
                    
                    if resolution == 'N/A' and height:
                        resolution = f"{width}x{height}"
                    
                    quality_parts = []
                    if f.get('format_note'):
                        quality_parts.append(f.get('format_note'))
                    if f.get('fps'):
                        quality_parts.append(f"{f.get('fps')}fps")
                    
                    quality = " - ".join(filter(None, quality_parts))
                    
                    # Calculate combined filesize
                    combined_size = (f.get('filesize', 0) or 0) + (best_audio.get('filesize', 0) or 0)
                    
                    format_info = VideoFormat(
                        format_id=f"{f['format_id']}+{best_audio['format_id']}",
                        ext='mp4',  # Will be merged to MP4
                        resolution=resolution,
                        filesize=combined_size,
                        note=f"{format_filesize(combined_size)} - {quality} (Merged)",
                        has_video=True,
                        has_audio=True,
                        quality=quality
                    )
                    formats.append(format_info)
            
            # Sort formats by resolution and filesize
            formats.sort(
                key=lambda x: (
                    int(x.resolution.split('x')[1]) if 'x' in x.resolution and x.resolution.split('x')[1].isdigit() else 0,
                    x.filesize or 0
                ),
                reverse=True
            )
            
            return {
                "title": info.get('title', 'Unknown Title'),
                "duration": info.get('duration'),
                "formats": formats
            }
            
    except Exception as e:
        print(f"Error in get_formats: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
async def download_video(video: VideoURL):
    temp_dir = tempfile.mkdtemp()
    try:
        format_id = video.format_id or 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        ydl_opts = get_ydl_opts(format_id)
        ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
        
        print(f"Starting download with format {format_id}")
        
        with YoutubeDL(ydl_opts) as ydl:
            try:
                print("Extracting video info...")
                info = ydl.extract_info(video.url, download=True)
                print("Download completed, preparing file...")
                
                title = info['title']
                ext = info.get('ext', 'mp4')
                
                files = os.listdir(temp_dir)
                if not files:
                    raise Exception("Download failed: No file created")
                
                downloaded_file = os.path.join(temp_dir, files[0])
                print(f"File found at: {downloaded_file}")
                
                if not os.path.exists(downloaded_file):
                    raise Exception("File not found after download")
                
                file_size = os.path.getsize(downloaded_file)
                if file_size == 0:
                    raise Exception("Downloaded file is empty")
                
                print(f"File size: {format_filesize(file_size)}")
                
                safe_title = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in title)
                safe_filename = f"{safe_title}.{ext}"
                
                def cleanup():
                    try:
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                    except Exception as e:
                        print(f"Cleanup error: {e}")

                def file_iterator():
                    try:
                        with open(downloaded_file, 'rb') as f:
                            while chunk := f.read(8192):
                                yield chunk
                    finally:
                        cleanup()

                print(f"Streaming file: {safe_filename}")
                return StreamingResponse(
                    file_iterator(),
                    media_type="video/mp4",
                    headers={
                        "Content-Disposition": f'attachment; filename="{safe_filename}"',
                        "Content-Length": str(file_size)
                    }
                )
                
            except Exception as e:
                print(f"Download error: {str(e)}")
                raise Exception(f"Download failed: {str(e)}")
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=400, detail=str(e))