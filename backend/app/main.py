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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoFormat(BaseModel):
    format_id: str
    ext: str
    resolution: str
    filesize: Optional[int]
    note: str
    has_video: bool
    has_audio: bool

class VideoURL(BaseModel):
    url: str
    format_id: Optional[str] = None

def get_ydl_opts(format_id=None):
    """Get YouTube-DL options with simplified settings."""
    return {
        'format': format_id if format_id else 'best[height<=720]',
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        },
        'socket_timeout': 30,
        'youtube_include_dash_manifest': False,  # Disable DASH manifests
        'prefer_insecure': True,
    }

@app.post("/formats")
async def get_formats(video: VideoURL):
    try:
        ydl_opts = get_ydl_opts()
        
        with YoutubeDL(ydl_opts) as ydl:
            print(f"Extracting info for URL: {video.url}")
            info = ydl.extract_info(video.url, download=False)
            
            formats = []
            for f in info['formats']:
                # Only include formats with both video and audio
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    resolution = f.get('resolution', 'N/A')
                    if resolution == 'N/A' and f.get('height'):
                        resolution = f"{f.get('width', 'N/A')}x{f.get('height')}"
                    
                    format_info = VideoFormat(
                        format_id=f['format_id'],
                        ext=f.get('ext', 'N/A'),
                        resolution=resolution,
                        filesize=f.get('filesize'),
                        note=f.get('format_note', ''),
                        has_video=True,
                        has_audio=True
                    )
                    formats.append(format_info)
            
            # Sort formats by resolution
            formats.sort(
                key=lambda x: int(x.resolution.split('x')[1]) 
                if 'x' in x.resolution and x.resolution.split('x')[1].isdigit() 
                else 0, 
                reverse=True
            )
            
            return {
                "title": info.get('title', 'Unknown Title'),
                "formats": formats
            }
            
    except Exception as e:
        print(f"Error in get_formats: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
async def download_video(video: VideoURL):
    temp_dir = tempfile.mkdtemp()
    try:
        format_id = video.format_id or 'best[height<=720]'
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
                
                # Find the downloaded file
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

@app.get("/")
async def read_root():
    return {"message": "YouTube Downloader API is running"}