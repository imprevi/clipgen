from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class JobStatus(BaseModel):
    id: str
    filename: str
    status: str  # queued, processing, completed, failed
    video_path: str
    clips: List[str] = []
    timestamps: List[float] = []
    created_at: str
    error: Optional[str] = None

class UploadResponse(BaseModel):
    job_id: str
    status: str 