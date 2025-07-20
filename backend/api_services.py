"""
🌐 API Services for StreamClip AI
===============================

Extracted service layer for job management, file validation, and background processing.
Reduces main.py complexity and improves separation of concerns.

Author: StreamClip AI Team
"""

import os
import uuid
import json
import time
import logging
import subprocess
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import shutil

logger = logging.getLogger(__name__)

class JobManager:
    """Manages job storage, retrieval, and cleanup"""
    
    def __init__(self, jobs_file: str = "jobs.json", cleanup_hours: int = 24):
        self.jobs_file = jobs_file
        self.cleanup_hours = cleanup_hours
        self.jobs: Dict[str, dict] = {}
        self.load_jobs()
    
    def save_jobs(self):
        """Save jobs to persistent storage"""
        try:
            # Convert datetime objects to strings for JSON serialization
            serializable_jobs = {}
            for job_id, job_data in self.jobs.items():
                serializable_job = job_data.copy()
                
                # Convert datetime objects to ISO strings
                if isinstance(serializable_job.get("created_at"), datetime):
                    serializable_job["created_at"] = serializable_job["created_at"].isoformat()
                if isinstance(serializable_job.get("completed_at"), datetime):
                    serializable_job["completed_at"] = serializable_job["completed_at"].isoformat()
                
                serializable_jobs[job_id] = serializable_job
            
            with open(self.jobs_file, 'w') as f:
                json.dump(serializable_jobs, f, indent=2)
            
            logger.debug(f"Saved {len(self.jobs)} jobs to {self.jobs_file}")
            
        except Exception as e:
            logger.error(f"Failed to save jobs: {e}")
    
    def load_jobs(self):
        """Load jobs from persistent storage"""
        try:
            if os.path.exists(self.jobs_file):
                with open(self.jobs_file, 'r') as f:
                    loaded_jobs = json.load(f)
                
                # Convert ISO strings back to datetime objects
                for job_id, job_data in loaded_jobs.items():
                    if isinstance(job_data.get("created_at"), str):
                        job_data["created_at"] = datetime.fromisoformat(job_data["created_at"])
                    if isinstance(job_data.get("completed_at"), str):
                        job_data["completed_at"] = datetime.fromisoformat(job_data["completed_at"])
                
                self.jobs = loaded_jobs
                logger.info(f"Loaded {len(self.jobs)} jobs from storage")
            else:
                logger.info("No existing jobs file found, starting fresh")
                
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}")
            self.jobs = {}
    
    def create_job(self, filename: str, **kwargs) -> str:
        """
        Create a new job
        
        Args:
            filename: Original filename
            **kwargs: Additional job data
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        # Create safe filename for storage
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        
        job_data = {
            "id": job_id,
            "filename": filename,
            "safe_filename": safe_filename,
            "status": "queued",
            "progress": 0,
            "current_phase": "Queued for processing...",
            "created_at": datetime.now(),
            "completed_at": None,
            "clips": [],
            "timestamps": [],
            "error": None,
            "analysis": None,
            **kwargs
        }
        
        self.jobs[job_id] = job_data
        self.save_jobs()
        
        logger.info(f"Created job {job_id}: {filename}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    def update_job(self, job_id: str, **updates):
        """Update job data"""
        if job_id in self.jobs:
            self.jobs[job_id].update(updates)
            self.save_jobs()
        else:
            logger.warning(f"Attempted to update non-existent job: {job_id}")
    
    def get_all_jobs(self) -> List[dict]:
        """Get all jobs sorted by creation time (newest first)"""
        all_jobs = list(self.jobs.values())
        all_jobs.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        return all_jobs
    
    def cleanup_old_jobs(self):
        """Clean up jobs older than cleanup_hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.cleanup_hours)
            jobs_to_remove = []
            
            for job_id, job_data in self.jobs.items():
                created_at = job_data.get("created_at")
                if isinstance(created_at, datetime) and created_at < cutoff_time:
                    # Only remove completed or failed jobs
                    if job_data.get("status") in ["completed", "failed"]:
                        jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                logger.info(f"Cleaned up old job: {job_id}")
            
            if jobs_to_remove:
                self.save_jobs()
                
        except Exception as e:
            logger.error(f"Error during job cleanup: {e}")

class FileValidator:
    """Validates uploaded files and system constraints"""
    
    def __init__(self, max_file_size: int = 5 * 1024 * 1024 * 1024, 
                 allowed_extensions: set = None):
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions or {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
    
    def validate_file(self, file) -> Optional[str]:
        """
        Validate uploaded file
        
        Args:
            file: UploadFile object
            
        Returns:
            Error message if invalid, None if valid
        """
        if not hasattr(file, 'filename') or not file.filename:
            return "No filename provided"
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            return f"Unsupported file type. Allowed: {', '.join(self.allowed_extensions)}"
        
        # Check file size (if provided)
        if hasattr(file, 'size') and file.size and file.size > self.max_file_size:
            size_mb = self.max_file_size // 1024 // 1024
            return f"File too large. Maximum size: {size_mb}MB"
        
        return None
    
    def validate_path(self, file_path: str) -> bool:
        """Validate that file path exists and is accessible"""
        try:
            return os.path.exists(file_path) and os.path.isfile(file_path)
        except:
            return False

class TwitchVODService:
    """Handles Twitch VOD download and processing"""
    
    def __init__(self, output_dir: str = "temp"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def extract_vod_id(self, url: str) -> str:
        """
        Extract Twitch VOD ID from various URL formats
        
        Args:
            url: Twitch VOD URL
            
        Returns:
            VOD ID string
            
        Raises:
            ValueError: If VOD ID cannot be extracted
        """
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
        numeric_match = re.search(r'(\d{8,})', url)  # VOD IDs are typically 8+ digits
        if numeric_match:
            return numeric_match.group(1)
        
        raise ValueError(f"Could not extract VOD ID from URL: {url}")
    
    def download_vod(self, url: str) -> dict:
        """
        Download Twitch VOD using yt-dlp
        
        Args:
            url: Twitch VOD URL
            
        Returns:
            Dictionary with download results
        """
        try:
            import yt_dlp
            
            vod_id = self.extract_vod_id(url)
            output_filename = f"twitch_vod_{vod_id}.%(ext)s"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'best[height<=1080]',  # Best quality up to 1080p
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
            
            logger.info(f"Successfully downloaded VOD: {expected_filename} ({file_size / 1024 / 1024:.2f}MB)")
            
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
    
    def cleanup_vod_file(self, file_path: str):
        """Clean up downloaded VOD file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up VOD file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not clean up VOD file {file_path}: {e}")

class BackgroundTaskService:
    """Manages background processing tasks"""
    
    def __init__(self, job_manager: JobManager, processor, cleanup_util):
        self.job_manager = job_manager
        self.processor = processor
        self.cleanup_util = cleanup_util
    
    async def process_video_background(self, job_id: str, video_path: str, settings):
        """Background task for video processing"""
        try:
            logger.info(f"Starting background processing for job {job_id}")
            
            # Update job status
            self.job_manager.update_job(
                job_id,
                status="processing",
                progress=10,
                current_phase="Analyzing video..."
            )
            
            # Process the video
            result = self.processor.process_video(
                video_path,
                audio_threshold=settings.audio_threshold,
                clip_duration=settings.clip_duration,
                max_clips=settings.max_clips
            )
            
            if result.get("success"):
                # Success
                self.job_manager.update_job(
                    job_id,
                    status="completed",
                    progress=100,
                    current_phase="Processing complete!",
                    completed_at=datetime.now(),
                    clips=result.get("clips", []),
                    timestamps=result.get("timestamps", []),
                    analysis=result.get("analysis"),
                    stats=result.get("stats")
                )
                
                logger.info(f"Job {job_id} completed successfully with {len(result.get('clips', []))} clips")
            else:
                # Processing failed
                error_msg = result.get("error", "Unknown processing error")
                self.job_manager.update_job(
                    job_id,
                    status="failed",
                    error=error_msg,
                    completed_at=datetime.now()
                )
                
                logger.error(f"Job {job_id} failed: {error_msg}")
                
        except Exception as e:
            # Unexpected error
            self.job_manager.update_job(
                job_id,
                status="failed",
                error=f"Processing error: {str(e)}",
                completed_at=datetime.now()
            )
            
            logger.error(f"Unexpected error in job {job_id}: {e}")
            
        finally:
            # Clean up temporary files
            try:
                if hasattr(self.processor, 'cleanup_temp_files'):
                    self.processor.cleanup_temp_files()
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
    
    async def process_twitch_vod_background(self, job_id: str, twitch_url: str, settings):
        """Background task for Twitch VOD processing"""
        twitch_service = TwitchVODService()
        
        try:
            logger.info(f"Starting Twitch VOD processing for job {job_id}: {twitch_url}")
            
            # Phase 1: Download VOD
            self.job_manager.update_job(
                job_id,
                status="processing",
                progress=5,
                current_phase="📥 Downloading Twitch VOD..."
            )
            
            download_result = twitch_service.download_vod(twitch_url)
            
            if not download_result["success"]:
                self.job_manager.update_job(
                    job_id,
                    status="failed",
                    error=download_result["error"],
                    completed_at=datetime.now()
                )
                return
            
            video_path = download_result["file_path"]
            vod_id = download_result["vod_id"]
            
            # Update job with download info
            self.job_manager.update_job(
                job_id,
                progress=20,
                current_phase="✅ Download complete, starting AI analysis...",
                video_path=video_path,
                file_size=download_result["file_size"]
            )
            
            # Phase 2: Process the downloaded video
            result = self.processor.process_video(
                video_path,
                audio_threshold=settings.audio_threshold,
                clip_duration=settings.clip_duration,
                max_clips=settings.max_clips
            )
            
            if result.get("success"):
                # Success
                self.job_manager.update_job(
                    job_id,
                    status="completed",
                    progress=100,
                    current_phase="🎉 Processing complete!",
                    completed_at=datetime.now(),
                    clips=result.get("clips", []),
                    timestamps=result.get("timestamps", []),
                    analysis=result.get("analysis"),
                    stats=result.get("stats")
                )
                
                logger.info(f"Twitch VOD job {job_id} completed with {len(result.get('clips', []))} clips")
            else:
                # Processing failed
                self.job_manager.update_job(
                    job_id,
                    status="failed",
                    error=result.get("error", "Unknown processing error"),
                    completed_at=datetime.now()
                )
                
                logger.error(f"Twitch VOD job {job_id} failed: {result.get('error')}")
            
            # Clean up downloaded VOD file
            twitch_service.cleanup_vod_file(video_path)
            
        except Exception as e:
            # Unexpected error
            self.job_manager.update_job(
                job_id,
                status="failed",
                error=f"Processing error: {str(e)}",
                completed_at=datetime.now()
            )
            
            logger.error(f"Unexpected error in Twitch VOD job {job_id}: {e}")
            
            # Try to clean up VOD file
            try:
                if 'video_path' in locals():
                    twitch_service.cleanup_vod_file(video_path)
            except:
                pass 