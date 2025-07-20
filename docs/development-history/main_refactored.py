"""
🚀 StreamClip AI - Refactored Main API
=====================================

Clean, focused FastAPI application that uses service modules.
Reduced from 926 lines to ~300 lines with better separation of concerns.

Author: StreamClip AI Team
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
import logging
from datetime import datetime
import shutil

# Import our service modules
from api_services import JobManager, FileValidator, TwitchVODService, BackgroundTaskService
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
    title="StreamClip AI Enhanced",
    description="AI-powered video highlight generator with ML capabilities",
    version="2.0.0-ML"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
try:
    processor = EnhancedVideoProcessor()
    ML_ENABLED = True
    logger.info("🚀 Enhanced ML Video Processor initialized")
except Exception as e:
    logger.warning(f"Failed to initialize Enhanced Video Processor: {e}")
    logger.info("🔄 Falling back to legacy Video Processor")
    processor = VideoProcessor()
    ML_ENABLED = False

# Initialize service layers
job_manager = JobManager()
file_validator = FileValidator()
cleanup_util = CleanupUtility()
task_service = BackgroundTaskService(job_manager, processor, cleanup_util)

# Configuration
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}

# Request/Response Models
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

# API Endpoints
@app.post("/upload", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    audio_threshold: float = Form(0.1),
    clip_duration: int = Form(30),
    max_clips: int = Form(5)
):
    """Upload and process a video file"""
    try:
        # Validate file
        validation_error = file_validator.validate_file(file)
        if validation_error:
            raise HTTPException(status_code=400, detail=validation_error)
        
        # Create job
        job_id = job_manager.create_job(
            filename=file.filename,
            source_type="upload"
        )
        
        # Save uploaded file
        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        
        file_path = os.path.join(uploads_dir, f"{job_id}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create processing settings
        settings = ProcessingSettings(
            audio_threshold=audio_threshold,
            clip_duration=clip_duration,
            max_clips=max_clips
        )
        
        # Start background processing
        background_tasks.add_task(
            task_service.process_video_background,
            job_id, file_path, settings
        )
        
        logger.info(f"Started processing job {job_id} for file {file.filename}")
        
        return UploadResponse(
            message="File uploaded successfully",
            job_id=job_id,
            filename=file.filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/process-twitch-vod")
async def process_twitch_vod(
    background_tasks: BackgroundTasks,
    request: TwitchVODRequest
):
    """Process a Twitch VOD URL"""
    try:
        # Validate Twitch URL
        if "twitch.tv" not in request.twitch_url:
            raise HTTPException(status_code=400, detail="Invalid Twitch URL")
        
        # Extract VOD ID for job naming
        twitch_service = TwitchVODService()
        try:
            vod_id = twitch_service.extract_vod_id(request.twitch_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Create job
        job_id = job_manager.create_job(
            filename=f"Twitch VOD {vod_id}",
            twitch_url=request.twitch_url,
            vod_id=vod_id,
            source_type="twitch_vod"
        )
        
        # Create processing settings
        settings = ProcessingSettings(
            audio_threshold=request.audio_threshold,
            clip_duration=request.clip_duration,
            max_clips=request.max_clips
        )
        
        # Start background processing
        background_tasks.add_task(
            task_service.process_twitch_vod_background,
            job_id, request.twitch_url, settings
        )
        
        logger.info(f"Started Twitch VOD processing job {job_id} for {request.twitch_url}")
        
        return {
            "message": "Twitch VOD processing started",
            "job_id": job_id,
            "vod_id": vod_id,
            "estimated_time": "Processing time varies by video length"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Twitch VOD processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get job status and results"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Convert datetime to string for JSON response
    job_copy = job.copy()
    if isinstance(job_copy.get("created_at"), datetime):
        job_copy["created_at"] = job_copy["created_at"].isoformat()
    if isinstance(job_copy.get("completed_at"), datetime):
        job_copy["completed_at"] = job_copy["completed_at"].isoformat()
    
    return JobResponse(**job_copy)

@app.get("/jobs", response_model=List[JobResponse])
async def get_all_jobs():
    """Get all jobs"""
    jobs = job_manager.get_all_jobs()
    
    # Convert datetime objects for JSON response
    job_responses = []
    for job in jobs:
        job_copy = job.copy()
        if isinstance(job_copy.get("created_at"), datetime):
            job_copy["created_at"] = job_copy["created_at"].isoformat()
        if isinstance(job_copy.get("completed_at"), datetime):
            job_copy["completed_at"] = job_copy["completed_at"].isoformat()
        
        job_responses.append(JobResponse(**job_copy))
    
    return job_responses

@app.get("/download/{filename}")
async def download_clip(filename: str):
    """Download a generated clip"""
    clips_dir = "clips"
    file_path = os.path.join(clips_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type='video/mp4',
        filename=filename
    )

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
        all_jobs = job_manager.get_all_jobs()
        
        return {
            "system_name": "StreamClip AI Enhanced",
            "version": "2.0.0-ML",
            "ml_capabilities": ml_info,
            "directory_status": dir_status,
            "active_jobs": len([j for j in all_jobs if j.get("status") == "processing"]),
            "total_jobs_processed": len(all_jobs)
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
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
        job_manager.save_jobs()
    except:
        storage_status = "error"
    
    all_jobs = job_manager.get_all_jobs()
    
    return {
        "status": "healthy",
        "processor": processor_status,
        "storage": storage_status,
        "ml_enabled": ML_ENABLED,
        "active_jobs": len([j for j in all_jobs if j.get("status") == "processing"]),
        "total_jobs": len(all_jobs)
    }

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

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    try:
        # Clean up old jobs
        job_manager.cleanup_old_jobs()
        
        # Run initial cleanup
        cleanup_util.run_full_cleanup()
        
        logger.info("🚀 StreamClip AI Enhanced startup complete")
        logger.info(f"   ML Enabled: {ML_ENABLED}")
        logger.info(f"   Jobs Loaded: {len(job_manager.get_all_jobs())}")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")

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