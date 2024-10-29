from yt_dlp import YoutubeDL
from io import BytesIO
import asyncio

async def download_video(url: str):
    try:
        buffer = BytesIO()
        ydl_opts = {
            'format': 'best',
            'outtmpl': '-',
            'logtostderr': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info['title']
            # Stream to memory instead of disk
            ydl.download([url])
            
        buffer.seek(0)
        safe_filename = f"{title}.mp4".replace(" ", "_")
        return buffer, safe_filename
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")