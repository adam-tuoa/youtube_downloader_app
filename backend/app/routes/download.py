from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.util.youtube import download_video
from pydantic import BaseModel

router = APIRouter()

class DownloadRequest(BaseModel):
    url: str

@router.post("/api/download")
async def download_youtube_video(request: DownloadRequest):
    try:
        video_stream, filename = await download_video(request.url)
        return StreamingResponse(
            video_stream,
            media_type="video/mp4",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))