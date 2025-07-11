import cv2
import numpy as np
from moviepy.editor import VideoFileClip
import os
from typing import List, Tuple
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.temp_dir = "temp"
        self.clips_dir = "clips"
        
        # Create directories if they don't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.clips_dir, exist_ok=True)
        
    def extract_audio_peaks(self, video_path: str, threshold: float = 0.1) -> List[float]:
        """
        Find moments with high audio energy that indicate exciting content
        
        Args:
            video_path: Path to the video file
            threshold: Audio energy threshold (0.1 = moderate excitement)
            
        Returns:
            List of timestamps where audio peaks occur
        """
        try:
            logger.info(f"Analyzing audio peaks in {video_path}")
            clip = VideoFileClip(video_path)
            
            if not clip.audio:
                logger.warning("No audio track found in video")
                clip.close()
                return []
                
            audio = clip.audio
            duration = clip.duration
            timestamps = []
            
            # Sample audio at 1-second intervals
            for t in range(0, int(duration), 1):
                try:
                    # Extract 1-second audio chunk
                    end_time = min(t + 1, duration)
                    chunk = audio.subclip(t, end_time)
                    
                    # Get audio array and calculate RMS (Root Mean Square) energy
                    audio_array = chunk.to_soundarray()
                    
                    # Handle mono vs stereo audio
                    if len(audio_array.shape) > 1:
                        # Stereo - average the channels
                        rms = np.sqrt(np.mean(audio_array ** 2))
                    else:
                        # Mono
                        rms = np.sqrt(np.mean(audio_array ** 2))
                    
                    # If this moment has high audio energy, it's likely exciting
                    if rms > threshold:
                        timestamps.append(t)
                        logger.debug(f"Audio peak detected at {t}s with RMS: {rms:.4f}")
                        
                    chunk.close()
                    
                except Exception as e:
                    logger.warning(f"Error processing audio chunk at {t}s: {e}")
                    continue
                    
            audio.close()
            clip.close()
            
            logger.info(f"Found {len(timestamps)} audio peaks")
            return timestamps
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return []
    
    def extract_clips(self, video_path: str, timestamps: List[float], 
                     clip_duration: int = 30, max_clips: int = 5) -> List[str]:
        """
        Extract video clips around interesting timestamps
        
        Args:
            video_path: Path to the video file
            timestamps: List of exciting moments (seconds)
            clip_duration: Length of each clip in seconds
            max_clips: Maximum number of clips to generate
            
        Returns:
            List of paths to generated clip files
        """
        clips = []
        
        try:
            logger.info(f"Extracting clips from {video_path}")
            video = VideoFileClip(video_path)
            
            # Sort timestamps and remove duplicates
            unique_timestamps = sorted(set(timestamps))
            
            # Limit to max_clips
            selected_timestamps = unique_timestamps[:max_clips]
            
            for i, timestamp in enumerate(selected_timestamps):
                try:
                    # Calculate clip boundaries
                    start_time = max(0, timestamp - clip_duration // 2)
                    end_time = min(video.duration, timestamp + clip_duration // 2)
                    
                    # Skip if clip would be too short
                    if end_time - start_time < 10:  # Minimum 10 seconds
                        logger.warning(f"Skipping short clip at {timestamp}s")
                        continue
                    
                    # Extract the clip
                    clip = video.subclip(start_time, end_time)
                    
                    # Generate unique filename
                    clip_id = uuid.uuid4().hex[:8]
                    clip_filename = f"clip_{clip_id}_{int(timestamp)}s.mp4"
                    clip_path = os.path.join(self.clips_dir, clip_filename)
                    
                    # Write the clip with optimized settings for social media
                    clip.write_videofile(
                        clip_path,
                        codec='libx264',
                        audio_codec='aac',
                        temp_audiofile=os.path.join(self.temp_dir, f'temp_audio_{clip_id}.m4a'),
                        remove_temp=True,
                        verbose=False,
                        logger=None
                    )
                    
                    clips.append(clip_path)
                    clip.close()
                    
                    logger.info(f"Generated clip {i+1}/{len(selected_timestamps)}: {clip_filename}")
                    
                except Exception as e:
                    logger.error(f"Error creating clip at {timestamp}s: {e}")
                    continue
                    
            video.close()
            logger.info(f"Successfully generated {len(clips)} clips")
            return clips
            
        except Exception as e:
            logger.error(f"Error extracting clips: {e}")
            return []
    
    def analyze_video_quality(self, video_path: str) -> dict:
        """
        Analyze video properties to ensure it's suitable for processing
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with video analysis results
        """
        try:
            clip = VideoFileClip(video_path)
            
            analysis = {
                "duration": clip.duration,
                "fps": clip.fps,
                "resolution": f"{clip.w}x{clip.h}",
                "has_audio": clip.audio is not None,
                "file_size": os.path.getsize(video_path),
                "suitable_for_processing": True,
                "warnings": []
            }
            
            # Check for common issues
            if clip.duration < 60:  # Less than 1 minute
                analysis["warnings"].append("Video is very short - may not have enough content for highlights")
            
            if clip.duration > 3600:  # More than 1 hour
                analysis["warnings"].append("Video is very long - processing may take a while")
            
            if not clip.audio:
                analysis["warnings"].append("No audio track - will use visual analysis only")
                analysis["suitable_for_processing"] = False
            
            if clip.fps < 15:
                analysis["warnings"].append("Low frame rate detected")
            
            clip.close()
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing video: {e}")
            return {
                "suitable_for_processing": False,
                "error": str(e)
            }
    
    def process_video(self, video_path: str, clip_duration: int = 30, 
                     max_clips: int = 5, audio_threshold: float = 0.1) -> dict:
        """
        Main processing function that analyzes video and generates highlight clips
        
        Args:
            video_path: Path to the video file
            clip_duration: Length of each clip in seconds
            max_clips: Maximum number of clips to generate
            audio_threshold: Sensitivity for audio peak detection
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Starting video processing: {video_path}")
            
            # Step 1: Check if file exists
            if not os.path.exists(video_path):
                return {"error": f"Video file not found: {video_path}"}
            
            # Step 2: Analyze video quality
            analysis = self.analyze_video_quality(video_path)
            if not analysis.get("suitable_for_processing", False):
                return {
                    "error": "Video is not suitable for processing",
                    "analysis": analysis
                }
            
            # Step 3: Find interesting moments using audio analysis
            timestamps = self.extract_audio_peaks(video_path, threshold=audio_threshold)
            
            if not timestamps:
                logger.warning("No interesting moments found - trying lower threshold")
                # Try with lower threshold
                timestamps = self.extract_audio_peaks(video_path, threshold=audio_threshold * 0.5)
                
                if not timestamps:
                    return {
                        "error": "No interesting moments found in video",
                        "analysis": analysis,
                        "suggestion": "Try uploading a video with more varied audio content"
                    }
            
            # Step 4: Extract clips around interesting moments
            clips = self.extract_clips(video_path, timestamps, clip_duration, max_clips)
            
            if not clips:
                return {
                    "error": "Failed to generate clips",
                    "analysis": analysis,
                    "timestamps": timestamps
                }
            
            # Step 5: Return success with results
            result = {
                "success": True,
                "clips": clips,
                "timestamps": timestamps[:len(clips)],
                "analysis": analysis,
                "stats": {
                    "total_peaks_found": len(timestamps),
                    "clips_generated": len(clips),
                    "processing_time": "calculated_separately"
                }
            }
            
            logger.info(f"Processing complete: {len(clips)} clips generated")
            return result
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return {"error": f"Processing failed: {str(e)}"}
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            for file in os.listdir(self.temp_dir):
                if file.startswith('temp_'):
                    os.remove(os.path.join(self.temp_dir, file))
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning temp files: {e}") 