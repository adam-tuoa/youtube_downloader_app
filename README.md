# YouTube Downloader

A modern web application for downloading YouTube videos, built with React and FastAPI.

## Setup

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Features
- Modern UI with shadcn/ui components
- Video download functionality
- Error handling
- Loading states

## Tech Stack
- Frontend: React, TypeScript, Tailwind CSS
- Backend: FastAPI, yt-dlp~