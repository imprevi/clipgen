"""
🧹 Cleanup Utility for StreamClip AI
==================================

Automatic cleanup and organization system to prevent folder overflow with junk files.
Keeps the system organized and efficient.

Author: StreamClip AI Team
"""

import os
import time
import logging
import shutil
from datetime import datetime, timedelta
from typing import List, Dict
import glob

logger = logging.getLogger(__name__)

class CleanupUtility:
    """
    Utility for keeping the StreamClip AI system organized and clean
    """
    
    def __init__(self):
        self.temp_dir = "temp"
        self.clips_dir = "clips"
        self.uploads_dir = "uploads"
        
        # Cleanup thresholds
        self.temp_file_max_age_hours = 2     # Remove temp files older than 2 hours
        self.clips_max_age_days = 7          # Remove clips older than 7 days
        self.uploads_max_age_days = 3        # Remove uploads older than 3 days
        self.max_files_per_dir = 100         # Maximum files per directory
        
        # File patterns to clean
        self.temp_file_patterns = [
            "temp_*.m4a",
            "temp_*.wav",
            "*TEMP_MPY_wvf_snd.*",
            "*.tmp",
            ".moviepy_*",
            "*_preview.mp4"
        ]
        
        logger.info("🧹 Cleanup Utility initialized")
    
    def cleanup_temp_files(self, force: bool = False) -> Dict[str, int]:
        """
        Clean up temporary files
        
        Args:
            force: If True, remove all temp files regardless of age
            
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {"removed": 0, "errors": 0, "size_freed_mb": 0}
        
        try:
            if not os.path.exists(self.temp_dir):
                return stats
            
            current_time = time.time()
            cutoff_time = current_time - (self.temp_file_max_age_hours * 3600)
            
            # Clean specific temp file patterns
            for pattern in self.temp_file_patterns:
                file_paths = glob.glob(os.path.join(self.temp_dir, pattern))
                for file_path in file_paths:
                    try:
                        if force or os.path.getmtime(file_path) < cutoff_time:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            stats["removed"] += 1
                            stats["size_freed_mb"] += file_size / (1024 * 1024)
                            logger.debug(f"Removed temp file: {os.path.basename(file_path)}")
                    except Exception as e:
                        stats["errors"] += 1
                        logger.warning(f"Could not remove temp file {file_path}: {e}")
            
            # Clean any other temp files in temp directory
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        if force or os.path.getmtime(file_path) < cutoff_time:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            stats["removed"] += 1
                            stats["size_freed_mb"] += file_size / (1024 * 1024)
                            logger.debug(f"Removed temp file: {filename}")
                    except Exception as e:
                        stats["errors"] += 1
                        logger.warning(f"Could not remove temp file {file_path}: {e}")
            
            if stats["removed"] > 0:
                logger.info(f"🧹 Cleaned up {stats['removed']} temp files, freed {stats['size_freed_mb']:.1f}MB")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
            stats["errors"] += 1
            return stats
    
    def cleanup_old_clips(self, max_age_days: int = None) -> Dict[str, int]:
        """
        Clean up old clip files
        
        Args:
            max_age_days: Maximum age in days (uses default if None)
            
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {"removed": 0, "errors": 0, "size_freed_mb": 0}
        
        try:
            if not os.path.exists(self.clips_dir):
                return stats
            
            max_age = max_age_days or self.clips_max_age_days
            cutoff_time = time.time() - (max_age * 24 * 3600)
            
            for filename in os.listdir(self.clips_dir):
                if filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    file_path = os.path.join(self.clips_dir, filename)
                    try:
                        if os.path.getmtime(file_path) < cutoff_time:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            stats["removed"] += 1
                            stats["size_freed_mb"] += file_size / (1024 * 1024)
                            logger.debug(f"Removed old clip: {filename}")
                    except Exception as e:
                        stats["errors"] += 1
                        logger.warning(f"Could not remove old clip {file_path}: {e}")
            
            if stats["removed"] > 0:
                logger.info(f"🧹 Cleaned up {stats['removed']} old clips, freed {stats['size_freed_mb']:.1f}MB")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error during clip cleanup: {e}")
            stats["errors"] += 1
            return stats
    
    def cleanup_old_uploads(self, max_age_days: int = None) -> Dict[str, int]:
        """
        Clean up old uploaded files
        
        Args:
            max_age_days: Maximum age in days (uses default if None)
            
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {"removed": 0, "errors": 0, "size_freed_mb": 0}
        
        try:
            if not os.path.exists(self.uploads_dir):
                return stats
            
            max_age = max_age_days or self.uploads_max_age_days
            cutoff_time = time.time() - (max_age * 24 * 3600)
            
            for filename in os.listdir(self.uploads_dir):
                file_path = os.path.join(self.uploads_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        if os.path.getmtime(file_path) < cutoff_time:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            stats["removed"] += 1
                            stats["size_freed_mb"] += file_size / (1024 * 1024)
                            logger.debug(f"Removed old upload: {filename}")
                    except Exception as e:
                        stats["errors"] += 1
                        logger.warning(f"Could not remove old upload {file_path}: {e}")
            
            if stats["removed"] > 0:
                logger.info(f"🧹 Cleaned up {stats['removed']} old uploads, freed {stats['size_freed_mb']:.1f}MB")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error during upload cleanup: {e}")
            stats["errors"] += 1
            return stats
    
    def organize_clips(self) -> Dict[str, int]:
        """
        Organize clips by date and type
        
        Returns:
            Dictionary with organization statistics
        """
        stats = {"organized": 0, "errors": 0}
        
        try:
            if not os.path.exists(self.clips_dir):
                return stats
            
            # Create date-based subdirectories
            today = datetime.now().strftime("%Y-%m-%d")
            today_dir = os.path.join(self.clips_dir, today)
            os.makedirs(today_dir, exist_ok=True)
            
            # Move today's clips to date folder
            for filename in os.listdir(self.clips_dir):
                if filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    file_path = os.path.join(self.clips_dir, filename)
                    if os.path.isfile(file_path):
                        file_date = datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d")
                        if file_date == today:
                            target_path = os.path.join(today_dir, filename)
                            try:
                                if not os.path.exists(target_path):
                                    shutil.move(file_path, target_path)
                                    stats["organized"] += 1
                                    logger.debug(f"Organized clip: {filename}")
                            except Exception as e:
                                stats["errors"] += 1
                                logger.warning(f"Could not organize clip {filename}: {e}")
            
            if stats["organized"] > 0:
                logger.info(f"📁 Organized {stats['organized']} clips")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error during clip organization: {e}")
            stats["errors"] += 1
            return stats
    
    def check_directory_limits(self) -> Dict[str, Dict]:
        """
        Check if directories are approaching file limits
        
        Returns:
            Dictionary with directory status
        """
        status = {}
        
        directories = [
            (self.temp_dir, "temp"),
            (self.clips_dir, "clips"),
            (self.uploads_dir, "uploads")
        ]
        
        for dir_path, dir_name in directories:
            if os.path.exists(dir_path):
                file_count = len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
                total_size = sum(os.path.getsize(os.path.join(dir_path, f)) 
                               for f in os.listdir(dir_path) 
                               if os.path.isfile(os.path.join(dir_path, f)))
                
                status[dir_name] = {
                    "file_count": file_count,
                    "size_mb": total_size / (1024 * 1024),
                    "approaching_limit": file_count > self.max_files_per_dir * 0.8,
                    "over_limit": file_count > self.max_files_per_dir
                }
                
                if status[dir_name]["over_limit"]:
                    logger.warning(f"⚠️ {dir_name} directory over file limit: {file_count} files")
                elif status[dir_name]["approaching_limit"]:
                    logger.info(f"📊 {dir_name} directory approaching limit: {file_count} files")
            else:
                status[dir_name] = {"file_count": 0, "size_mb": 0, "approaching_limit": False, "over_limit": False}
        
        return status
    
    def run_full_cleanup(self, force_temp: bool = False) -> Dict[str, Dict]:
        """
        Run complete cleanup of all directories
        
        Args:
            force_temp: Force cleanup of all temp files regardless of age
            
        Returns:
            Dictionary with comprehensive cleanup statistics
        """
        logger.info("🧹 Starting full cleanup...")
        
        results = {
            "temp_files": self.cleanup_temp_files(force=force_temp),
            "old_clips": self.cleanup_old_clips(),
            "old_uploads": self.cleanup_old_uploads(),
            "organization": self.organize_clips(),
            "directory_status": self.check_directory_limits()
        }
        
        # Calculate totals
        total_removed = (results["temp_files"]["removed"] + 
                        results["old_clips"]["removed"] + 
                        results["old_uploads"]["removed"])
        
        total_freed_mb = (results["temp_files"]["size_freed_mb"] + 
                         results["old_clips"]["size_freed_mb"] + 
                         results["old_uploads"]["size_freed_mb"])
        
        total_errors = (results["temp_files"]["errors"] + 
                       results["old_clips"]["errors"] + 
                       results["old_uploads"]["errors"] + 
                       results["organization"]["errors"])
        
        results["summary"] = {
            "total_files_removed": total_removed,
            "total_size_freed_mb": total_freed_mb,
            "total_errors": total_errors,
            "files_organized": results["organization"]["organized"]
        }
        
        logger.info(f"✅ Cleanup complete: {total_removed} files removed, {total_freed_mb:.1f}MB freed")
        
        if total_errors > 0:
            logger.warning(f"⚠️ {total_errors} errors occurred during cleanup")
        
        return results
    
    def schedule_cleanup(self):
        """
        Schedule regular cleanup (to be called from main application)
        
        Note: This should be integrated into the main application's background tasks
        """
        logger.info("⏰ Scheduled cleanup triggered")
        return self.run_full_cleanup()

def cleanup_background_job():
    """
    Background job function for regular cleanup
    Can be called from the main application
    """
    try:
        cleanup_util = CleanupUtility()
        results = cleanup_util.run_full_cleanup()
        
        # Log summary for monitoring
        summary = results["summary"]
        logger.info(f"🧹 Background cleanup: {summary['total_files_removed']} files removed, "
                   f"{summary['total_size_freed_mb']:.1f}MB freed")
        
        return results
        
    except Exception as e:
        logger.error(f"Background cleanup failed: {e}")
        return {"error": str(e)} 