// src/App.tsx
import React, { useState } from 'react';

interface VideoFormat {
  format_id: string;
  ext: string;
  resolution: string;
  filesize?: number;
  note: string;
  has_video: boolean;
  has_audio: boolean;
}

interface VideoInfo {
  title: string;
  thumbnail?: string;
  duration?: number;
  formats: VideoFormat[];
}

function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<string>('');

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setError('');
    setVideoInfo(null);

    try {
      const response = await fetch('http://localhost:8000/formats', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url })
      });

      if (!response.ok) {
        throw new Error('Failed to get video information');
      }

      const data = await response.json();
      setVideoInfo(data);
      setSelectedFormat(data.formats[0]?.format_id || '');
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    setLoading(true);
    setMessage('Starting download...');
    
    try {
      const response = await fetch('http://localhost:8000/download', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          url,
          format_id: selectedFormat 
        })
      });

      if (!response.ok) {
        throw new Error('Download failed');
      }

      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition');
      const filenameMatch = contentDisposition && contentDisposition.match(/filename="(.+)"/);
      const filename = filenameMatch ? filenameMatch[1] : 'video.mp4';

      // Create blob from response
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
      
      setMessage(`Download complete: ${filename}`);
    } catch (err: any) {
      setError(err.message || 'Download failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-3xl font-bold mb-6 text-center">YouTube Downloader</h1>
        
        <form onSubmit={handleUrlSubmit} className="space-y-4">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Enter YouTube URL..."
            className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-500 text-white p-2 rounded-md hover:bg-blue-600 disabled:bg-blue-300 disabled:cursor-not-allowed"
          >
            {loading ? 'Processing...' : 'Check Formats'}
          </button>
        </form>

        {videoInfo && (
          <div className="mt-4 space-y-4">
            <h2 className="text-xl font-semibold">{videoInfo.title}</h2>
            
            <select
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md"
            >
              {videoInfo.formats.map((format) => (
                <option key={format.format_id} value={format.format_id}>
                  {format.resolution} - {format.note} ({format.ext})
                </option>
              ))}
            </select>

            <button
              onClick={handleDownload}
              disabled={loading}
              className="w-full bg-green-500 text-white p-2 rounded-md hover:bg-green-600 disabled:bg-green-300 disabled:cursor-not-allowed"
            >
              {loading ? 'Downloading...' : 'Download'}
            </button>
          </div>
        )}

        {message && (
          <div className="mt-4 p-3 bg-green-100 text-green-700 rounded-md">
            {message}
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 bg-red-100 text-red-700 rounded-md">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;