from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
import uuid
import json
import time
import logging
from datetime import datetime
import shutil
from pathlib import Path
import subprocess
import re
import sys

# Import our enhanced video processor
from enhanced_video_processor import EnhancedVideoProcessor
from video_processor import VideoProcessor  # Keep for fallback
from cleanup_utility import CleanupUtility
from models import JobStatus, UploadResponse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="StreamClip AI",
    description="AI-powered video highlight generator for streamers and content creators",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize enhanced video processor with ML
try:
    processor = EnhancedVideoProcessor()
    ML_ENABLED = True
    logger.info("🚀 Enhanced ML Video Processor initialized")
except Exception as e:
    logger.warning(f"Failed to initialize Enhanced Video Processor: {e}")
    logger.info("🔄 Falling back to legacy Video Processor")
    processor = VideoProcessor()
    ML_ENABLED = False

# Initialize cleanup utility
cleanup_util = CleanupUtility()

# Configuration
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB (uncapped for practical purposes)
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
JOBS_FILE = "jobs.json"
CLEANUP_HOURS = 24  # Clean up jobs older than 24 hours

# Global job storage (in production, use a database)
jobs: Dict[str, dict] = {}

class ProcessingSettings(BaseModel):
    """Settings for video processing"""
    audio_threshold: float = 0.1
    clip_duration: int = 30
    max_clips: int = 5

class TwitchVODRequest(BaseModel):
    """Request model for Twitch VOD processing"""
    twitch_url: str
    audio_threshold: float = 0.1
    clip_duration: int = 30
    max_clips: int = 5

class JobResponse(BaseModel):
    """Response model for job status"""
    id: str
    filename: str
    status: str
    progress: Optional[int] = 0
    current_phase: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    clips: List[str] = []
    timestamps: List[float] = []
    error: Optional[str] = None
    analysis: Optional[dict] = None
    stats: Optional[dict] = None
    source_type: Optional[str] = "upload"

def save_jobs():
    """Save jobs to persistent storage"""
    try:
        jobs_data = {}
        for job_id, job in jobs.items():
            # Convert any non-serializable data
            serializable_job = job.copy()
            if 'created_at' in serializable_job and isinstance(serializable_job['created_at'], datetime):
                serializable_job['created_at'] = serializable_job['created_at'].isoformat()
            if 'completed_at' in serializable_job and isinstance(serializable_job['completed_at'], datetime):
                serializable_job['completed_at'] = serializable_job['completed_at'].isoformat()
            jobs_data[job_id] = serializable_job
            
        with open(JOBS_FILE, 'w') as f:
            json.dump(jobs_data, f, indent=2)
        logger.debug("Jobs saved to persistent storage")
    except Exception as e:
        logger.error(f"Error saving jobs: {e}")

def load_jobs():
    """Load jobs from persistent storage"""
    global jobs
    try:
        if os.path.exists(JOBS_FILE):
            with open(JOBS_FILE, 'r') as f:
                jobs_data = json.load(f)
                
            # Convert datetime strings back to datetime objects
            for job_id, job in jobs_data.items():
                if 'created_at' in job and isinstance(job['created_at'], str):
                    try:
                        job['created_at'] = datetime.fromisoformat(job['created_at'])
                    except:
                        job['created_at'] = datetime.now()
                        
                if 'completed_at' in job and isinstance(job['completed_at'], str):
                    try:
                        job['completed_at'] = datetime.fromisoformat(job['completed_at'])
                    except:
                        job['completed_at'] = None
                        
            jobs = jobs_data
            logger.info(f"Loaded {len(jobs)} jobs from storage")
        else:
            jobs = {}
            logger.info("No existing jobs file found, starting fresh")
    except Exception as e:
        logger.error(f"Error loading jobs: {e}")
        jobs = {}

def cleanup_old_jobs():
    """Clean up old jobs and their files"""
    try:
        current_time = datetime.now()
        jobs_to_remove = []
        
        for job_id, job in jobs.items():
            created_at = job.get('created_at')
            if isinstance(created_at, datetime):
                hours_old = (current_time - created_at).total_seconds() / 3600
                if hours_old > CLEANUP_HOURS:
                    jobs_to_remove.append(job_id)
                    
                    # Clean up associated files
                    try:
                        video_path = job.get('video_path')
                        if video_path and os.path.exists(video_path):
                            os.remove(video_path)
                            
                        clips = job.get('clips', [])
                        for clip_path in clips:
                            if os.path.exists(clip_path):
                                os.remove(clip_path)
                    except Exception as e:
                        logger.warning(f"Error cleaning up files for job {job_id}: {e}")
        
        for job_id in jobs_to_remove:
            del jobs[job_id]
            logger.info(f"Cleaned up old job: {job_id}")
            
        if jobs_to_remove:
            save_jobs()
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def validate_file(file: UploadFile) -> Optional[str]:
    """Validate uploaded file"""
    if not file.filename:
        return "No filename provided"
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check file size (if provided)
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        return f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB"
    
    return None

async def process_video_background(job_id: str, video_path: str, settings: ProcessingSettings):
    """Background task for video processing"""
    try:
        logger.info(f"Starting background processing for job {job_id}")
        
        # Update job status
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        save_jobs()
        
        # Process the video using our AI
        logger.info(f"Processing video with settings: threshold={settings.audio_threshold}, duration={settings.clip_duration}, max_clips={settings.max_clips}")
        
        result = processor.process_video(
            video_path,
            audio_threshold=settings.audio_threshold,
            clip_duration=settings.clip_duration,
            max_clips=settings.max_clips
        )
        
        jobs[job_id]["progress"] = 90
        save_jobs()
        
        if result.get("success"):
            # Success - update job with results
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["completed_at"] = datetime.now()
            jobs[job_id]["clips"] = result.get("clips", [])
            jobs[job_id]["timestamps"] = result.get("timestamps", [])
            jobs[job_id]["analysis"] = result.get("analysis", {})
            jobs[job_id]["stats"] = result.get("stats", {})
            
            logger.info(f"Job {job_id} completed successfully with {len(result.get('clips', []))} clips")
            
        else:
            # Processing failed
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = result.get("error", "Unknown processing error")
            jobs[job_id]["completed_at"] = datetime.now()
            
            logger.error(f"Job {job_id} failed: {result.get('error')}")
            
    except Exception as e:
        # Unexpected error
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = f"Processing error: {str(e)}"
        jobs[job_id]["completed_at"] = datetime.now()
        
        logger.error(f"Unexpected error in job {job_id}: {e}")
        
    finally:
        save_jobs()
        
        # Clean up temporary files
        try:
            processor.cleanup_temp_files()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

def extract_twitch_vod_id(url: str) -> str:
    """Extract Twitch VOD ID from various URL formats"""
    # Handle different Twitch URL formats
    patterns = [
        r'twitch\.tv/videos/(\d+)',
        r'twitch\.tv/\w+/v/(\d+)',
        r'twitch\.tv/\w+/video/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no pattern matches, try to extract just the numeric part
    numeric_match = re.search(r'(\d+)', url)
    if numeric_match:
        return numeric_match.group(1)
    
    raise ValueError(f"Could not extract VOD ID from URL: {url}")

def download_twitch_vod(url: str, output_dir: str = "temp") -> dict:
    """Download Twitch VOD using yt-dlp and return info"""
    try:
        import yt_dlp
        
        vod_id = extract_twitch_vod_id(url)
        output_filename = f"twitch_vod_{vod_id}.%(ext)s"
        output_path = os.path.join(output_dir, output_filename)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[height<=1080]',  # Download best quality up to 1080p
            'outtmpl': output_path,
            'nocheckcertificate': True,  # Handle SSL issues
        }
        
        logger.info(f"Starting download of Twitch VOD: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get info first
            info = ydl.extract_info(url, download=False)
            expected_filename = ydl.prepare_filename(info)
            
            # Download the video
            ydl.download([url])
        
        if not os.path.exists(expected_filename):
            raise FileNotFoundError(f"Downloaded file not found: {expected_filename}")
        
        # Get file info
        file_size = os.path.getsize(expected_filename)
        
        logger.info(f"Successfully downloaded VOD to: {expected_filename} ({file_size / 1024 / 1024:.2f}MB)")
        
        return {
            "success": True,
            "file_path": expected_filename,
            "file_size": file_size,
            "vod_id": vod_id
        }
        
    except Exception as e:
        error_msg = f"Download failed: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

async def process_twitch_vod_background(job_id: str, twitch_url: str, settings: ProcessingSettings):
    """Background task for Twitch VOD processing"""
    try:
        logger.info(f"Starting Twitch VOD processing for job {job_id}: {twitch_url}")
        
        # Update job status - starting download
        jobs[job_id]["status"] = "downloading"
        jobs[job_id]["progress"] = 5
        jobs[job_id]["current_phase"] = "Downloading VOD from Twitch..."
        save_jobs()
        
        # Download the VOD
        download_result = download_twitch_vod(twitch_url)
        
        if not download_result.get("success"):
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = download_result.get("error", "Download failed")
            jobs[job_id]["completed_at"] = datetime.now()
            save_jobs()
            return
        
        video_path = download_result["file_path"]
        jobs[job_id]["video_path"] = video_path
        jobs[job_id]["progress"] = 30
        jobs[job_id]["current_phase"] = "Download complete, starting AI analysis..."
        save_jobs()
        
        # Process the video using our AI
        logger.info(f"Processing downloaded VOD with settings: threshold={settings.audio_threshold}, duration={settings.clip_duration}, max_clips={settings.max_clips}")
        
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 40
        jobs[job_id]["current_phase"] = "AI analyzing video for exciting moments..."
        save_jobs()
        
        result = processor.process_video(
            video_path,
            audio_threshold=settings.audio_threshold,
            clip_duration=settings.clip_duration,
            max_clips=settings.max_clips
        )
        
        jobs[job_id]["progress"] = 90
        jobs[job_id]["current_phase"] = "Finalizing clips..."
        save_jobs()
        
        if result.get("success"):
            # Success - update job with results
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["current_phase"] = "Complete!"
            jobs[job_id]["completed_at"] = datetime.now()
            jobs[job_id]["clips"] = result.get("clips", [])
            jobs[job_id]["timestamps"] = result.get("timestamps", [])
            jobs[job_id]["analysis"] = result.get("analysis", {})
            jobs[job_id]["stats"] = result.get("stats", {})
            
            logger.info(f"Twitch VOD job {job_id} completed successfully with {len(result.get('clips', []))} clips")
            
        else:
            # Processing failed
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = result.get("error", "Unknown processing error")
            jobs[job_id]["completed_at"] = datetime.now()
            
            logger.error(f"Twitch VOD job {job_id} failed: {result.get('error')}")
            
    except Exception as e:
        # Unexpected error
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = f"Processing error: {str(e)}"
        jobs[job_id]["completed_at"] = datetime.now()
        
        logger.error(f"Unexpected error in Twitch VOD job {job_id}: {e}")
        
    finally:
        save_jobs()
        
        # Clean up downloaded VOD file (auto-delete as requested)
        try:
            if "video_path" in jobs[job_id] and os.path.exists(jobs[job_id]["video_path"]):
                os.remove(jobs[job_id]["video_path"])
                logger.info(f"Cleaned up downloaded VOD: {jobs[job_id]['video_path']}")
        except Exception as e:
            logger.warning(f"Error cleaning up VOD file: {e}")
        
        # Clean up temporary files
        try:
            processor.cleanup_temp_files()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

# Load existing jobs on startup
load_jobs()

@app.on_event("startup")
async def startup_event():
    """Run cleanup on startup"""
    logger.info("StreamClip AI starting up...")
    cleanup_old_jobs()

@app.post("/upload", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    audio_threshold: float = Form(0.1),
    clip_duration: int = Form(30),
    max_clips: int = Form(5)
):
    """
    Upload a video file for processing
    
    - **file**: Video file (MP4, AVI, MOV, MKV, WebM, FLV)
    - **audio_threshold**: Sensitivity for detecting exciting moments (0.01-0.5)
    - **clip_duration**: Length of each clip in seconds (10-120)
    - **max_clips**: Maximum number of clips to generate (1-15)
    """
    
    # Validate file
    validation_error = validate_file(file)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)
    
    # Validate parameters
    if not 0.01 <= audio_threshold <= 0.5:
        raise HTTPException(status_code=400, detail="audio_threshold must be between 0.01 and 0.5")
    if not 10 <= clip_duration <= 120:
        raise HTTPException(status_code=400, detail="clip_duration must be between 10 and 120 seconds")
    if not 1 <= max_clips <= 15:
        raise HTTPException(status_code=400, detail="max_clips must be between 1 and 15")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    try:
        # Save uploaded file
        file_extension = Path(file.filename).suffix.lower()
        safe_filename = f"{job_id}_{uuid.uuid4().hex[:8]}{file_extension}"
        file_path = os.path.join("uploads", safe_filename)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        file_size = len(content)
        logger.info(f"Uploaded file {file.filename} ({file_size / 1024 / 1024:.2f}MB) as {safe_filename}")
        
        # Create job record
        settings = ProcessingSettings(
            audio_threshold=audio_threshold,
            clip_duration=clip_duration,
            max_clips=max_clips
        )
        
        jobs[job_id] = {
            "id": job_id,
            "filename": file.filename,
            "safe_filename": safe_filename,
            "status": "queued",
            "progress": 0,
            "video_path": file_path,
            "file_size": file_size,
            "created_at": datetime.now(),
            "completed_at": None,
            "clips": [],
            "timestamps": [],
            "error": None,
            "analysis": None,
            "stats": None,
            "settings": settings.dict()
        }
        
        save_jobs()
        
        # Start background processing
        background_tasks.add_task(process_video_background, job_id, file_path, settings)
        
        logger.info(f"Created job {job_id} for file {file.filename}")
        
        return UploadResponse(job_id=job_id, status="queued")
        
    except Exception as e:
        # Clean up file if job creation failed
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
                
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing upload: {str(e)}")

@app.post("/process-twitch-vod", response_model=UploadResponse)
async def process_twitch_vod(
    background_tasks: BackgroundTasks,
    request: TwitchVODRequest
):
    """
    Process a Twitch VOD from URL
    
    - **twitch_url**: Full Twitch VOD URL (e.g., https://www.twitch.tv/videos/123456789)
    - **audio_threshold**: Sensitivity for detecting exciting moments (0.01-0.5)
    - **clip_duration**: Length of each clip in seconds (10-120)
    - **max_clips**: Maximum number of clips to generate (1-15)
    """
    
    # Validate Twitch URL
    if not request.twitch_url or "twitch.tv" not in request.twitch_url.lower():
        raise HTTPException(status_code=400, detail="Invalid Twitch URL. Must contain 'twitch.tv'")
    
    # Validate parameters
    if not 0.01 <= request.audio_threshold <= 0.5:
        raise HTTPException(status_code=400, detail="audio_threshold must be between 0.01 and 0.5")
    if not 10 <= request.clip_duration <= 120:
        raise HTTPException(status_code=400, detail="clip_duration must be between 10 and 120 seconds")
    if not 1 <= request.max_clips <= 15:
        raise HTTPException(status_code=400, detail="max_clips must be between 1 and 15")
    
    # Extract VOD ID for filename
    try:
        vod_id = extract_twitch_vod_id(request.twitch_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    try:
        # Create job record
        settings = ProcessingSettings(
            audio_threshold=request.audio_threshold,
            clip_duration=request.clip_duration,
            max_clips=request.max_clips
        )
        
        jobs[job_id] = {
            "id": job_id,
            "filename": f"Twitch VOD {vod_id}",
            "safe_filename": f"twitch_vod_{vod_id}",
            "status": "queued",
            "progress": 0,
            "current_phase": "Queued for processing...",
            "twitch_url": request.twitch_url,
            "vod_id": vod_id,
            "video_path": None,  # Will be set after download
            "file_size": None,   # Will be set after download
            "created_at": datetime.now(),
            "completed_at": None,
            "clips": [],
            "timestamps": [],
            "error": None,
            "analysis": None,
            "stats": None,
            "settings": settings.dict(),
            "source_type": "twitch_vod"
        }
        
        save_jobs()
        
        # Start background processing
        background_tasks.add_task(process_twitch_vod_background, job_id, request.twitch_url, settings)
        
        logger.info(f"Created Twitch VOD job {job_id} for URL: {request.twitch_url}")
        
        return UploadResponse(job_id=job_id, status="queued")
        
    except Exception as e:
        logger.error(f"Error creating Twitch VOD job: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing Twitch VOD: {str(e)}")

@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get the status of a processing job"""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    # Convert to response model
    response = JobResponse(
        id=job["id"],
        filename=job["filename"],
        status=job["status"],
        progress=job.get("progress", 0),
        current_phase=job.get("current_phase"),
        created_at=job["created_at"].isoformat() if isinstance(job["created_at"], datetime) else str(job["created_at"]),
        completed_at=job["completed_at"].isoformat() if job.get("completed_at") and isinstance(job["completed_at"], datetime) else None,
        clips=[os.path.basename(clip) for clip in job.get("clips", [])],  # Return just filenames for security
        timestamps=job.get("timestamps", []),
        error=job.get("error"),
        analysis=job.get("analysis"),
        stats=job.get("stats"),
        source_type=job.get("source_type", "upload")
    )
    
    return response

@app.get("/jobs")
async def list_jobs(limit: int = 50, status: Optional[str] = None):
    """
    List processing jobs
    
    - **limit**: Maximum number of jobs to return (1-100)
    - **status**: Filter by status (queued, processing, completed, failed)
    """
    
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    
    if status and status not in ["queued", "processing", "completed", "failed"]:
        raise HTTPException(status_code=400, detail="status must be one of: queued, processing, completed, failed")
    
    # Filter and sort jobs
    filtered_jobs = []
    for job in jobs.values():
        if status is None or job.get("status") == status:
            filtered_jobs.append(job)
    
    # Sort by creation date (newest first)
    filtered_jobs.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
    
    # Limit results
    limited_jobs = filtered_jobs[:limit]
    
    # Convert to response format
    response_jobs = []
    for job in limited_jobs:
        response_jobs.append({
            "id": job["id"],
            "filename": job["filename"],
            "status": job["status"],
            "progress": job.get("progress", 0),
            "created_at": job["created_at"].isoformat() if isinstance(job["created_at"], datetime) else str(job["created_at"]),
            "completed_at": job["completed_at"].isoformat() if job.get("completed_at") and isinstance(job["completed_at"], datetime) else None,
            "clips_count": len(job.get("clips", [])),
            "error": job.get("error")
        })
    
    return {
        "jobs": response_jobs,
        "total": len(response_jobs),
        "filtered_total": len(filtered_jobs)
    }

@app.get("/download/{filename}")
async def download_clip(filename: str):
    """Download a generated clip file"""
    
    # Security: only allow downloading files from clips directory
    # and ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = os.path.join("clips", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify this file belongs to a valid job (security measure)
    file_belongs_to_job = False
    for job in jobs.values():
        job_clips = job.get("clips", [])
        if file_path in job_clips or any(clip.endswith(filename) for clip in job_clips):
            file_belongs_to_job = True
            break
    
    if not file_belongs_to_job:
        raise HTTPException(status_code=403, detail="File access denied")
    
    return FileResponse(
        file_path,
        filename=filename,
        media_type='video/mp4'
    )

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its associated files"""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    try:
        # Delete associated files
        video_path = job.get("video_path")
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
        
        clips = job.get("clips", [])
        for clip_path in clips:
            if os.path.exists(clip_path):
                os.remove(clip_path)
        
        # Remove job from memory and storage
        del jobs[job_id]
        save_jobs()
        
        logger.info(f"Deleted job {job_id} and associated files")
        
        return {"message": "Job deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting job: {str(e)}")

@app.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str, background_tasks: BackgroundTasks):
    """Retry a failed job"""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] not in ["failed", "completed"]:
        raise HTTPException(status_code=400, detail="Can only retry failed or completed jobs")
    
    video_path = job.get("video_path")
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="Original video file not found")
    
    # Reset job status
    job["status"] = "queued"
    job["progress"] = 0
    job["error"] = None
    job["clips"] = []
    job["timestamps"] = []
    job["analysis"] = None
    job["stats"] = None
    job["completed_at"] = None
    
    save_jobs()
    
    # Restart processing
    settings = ProcessingSettings(**job.get("settings", {}))
    background_tasks.add_task(process_video_background, job_id, video_path, settings)
    
    logger.info(f"Retrying job {job_id}")
    
    return {"message": "Job retry started", "job_id": job_id, "status": "queued"}

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    
    total_jobs = len(jobs)
    status_counts = {}
    total_clips = 0
    total_processing_time = 0
    
    for job in jobs.values():
        status = job.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        total_clips += len(job.get("clips", []))
        
        # Calculate processing time for completed jobs
        if job.get("completed_at") and job.get("created_at"):
            if isinstance(job["completed_at"], datetime) and isinstance(job["created_at"], datetime):
                processing_time = (job["completed_at"] - job["created_at"]).total_seconds()
                total_processing_time += processing_time
    
    return {
        "total_jobs": total_jobs,
        "status_breakdown": status_counts,
        "total_clips_generated": total_clips,
        "average_clips_per_job": total_clips / max(total_jobs, 1),
        "total_processing_time_hours": total_processing_time / 3600,
        "system_status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    # Check if processor is working
    processor_status = "healthy"
    try:
        # Quick validation
        test_result = processor.analyze_video_quality("nonexistent.mp4")
        if "error" not in test_result:
            processor_status = "error"
    except:
        pass  # Expected for nonexistent file
    
    # Check storage
    storage_status = "healthy"
    try:
        save_jobs()
    except:
        storage_status = "error"
    
    return {
        "status": "healthy",
        "processor": processor_status,
        "storage": storage_status,
        "active_jobs": len([j for j in jobs.values() if j.get("status") == "processing"]),
        "total_jobs": len(jobs)
    }

@app.get("/system-status")
async def system_status():
    """Get detailed system status including ML capabilities"""
    try:
        ml_info = {}
        if ML_ENABLED and hasattr(processor, 'ml_analyzer'):
            ml_info = {
                "ml_enabled": True,
                "processing_strategy": processor.ml_analyzer.processing_strategy,
                "available_ram_gb": processor.ml_analyzer.available_ram_gb,
                "excitement_types": list(processor.ml_analyzer.excitement_types.keys()),
                "features": [
                    "Funny moment detection",
                    "Variable-length clips",
                    "Social media optimization",
                    "Context-aware boundaries",
                    "Rolling baseline analysis"
                ]
            }
        else:
            ml_info = {
                "ml_enabled": False,
                "fallback_mode": "Legacy audio processing",
                "features": ["Fixed-length clips", "Basic audio peak detection"]
            }
        
        # Directory status
        dir_status = cleanup_util.check_directory_limits()
        
        return {
            "system_name": "StreamClip AI Enhanced",
            "version": "2.0.0-ML",
            "ml_capabilities": ml_info,
            "directory_status": dir_status,
            "active_jobs": len([j for j in jobs.values() if j.get("status") == "processing"]),
            "total_jobs_processed": len(jobs)
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {"error": "Failed to get system status", "ml_enabled": ML_ENABLED}

@app.post("/cleanup")
async def manual_cleanup():
    """Manually trigger system cleanup"""
    try:
        logger.info("🧹 Manual cleanup triggered")
        results = cleanup_util.run_full_cleanup(force_temp=True)
        
        return {
            "success": True,
            "cleanup_results": results,
            "message": f"Cleaned up {results['summary']['total_files_removed']} files, freed {results['summary']['total_size_freed_mb']:.1f}MB"
        }
    except Exception as e:
        logger.error(f"Manual cleanup failed: {e}")
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    """API root endpoint with welcome message"""
    return {
        "message": "🚀 StreamClip AI Enhanced - Video Highlight Generator",
        "version": "2.0.0-ML",
        "status": "ML Enhancement Complete - Full System Integration",
        "ml_enabled": ML_ENABLED,
        "features": [
            "🤖 ML-powered funny moment detection" if ML_ENABLED else "📊 Audio peak detection",
            "📏 Variable-length clips" if ML_ENABLED else "⏱️ Fixed-length clips",
            "🎯 Social media optimization" if ML_ENABLED else "🎬 Standard video clips",
            "💾 RAM-optimized processing",
            "🧹 Automatic cleanup system",
            "🔄 Background job processing",
            "📊 Real-time progress tracking",
            "🌐 RESTful API"
        ],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "system_status": "/system-status",
            "cleanup": "/cleanup (POST)"
        }
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 