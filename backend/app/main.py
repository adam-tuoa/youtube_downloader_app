from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.download import router as download_router

app = FastAPI(title="YouTube Downloader API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(download_router, prefix="/api")