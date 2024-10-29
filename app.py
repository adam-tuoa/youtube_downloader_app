from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from yt_dlp import YoutubeDL
from io import BytesIO
import asyncio

app = FastAPI()

async def download_to_memory(url):
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
    return buffer, title

@app.post("/api/download")
async def download_video(url: str):
    try:
        buffer, title = await download_to_memory(url)
        return StreamingResponse(
            buffer,
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{title}.mp4"'}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))