"""
🚀 Enhanced Video Processor with ML Integration
============================================

Advanced video processing that combines:
- 🤖 ML-powered audio analysis for funny moment detection
- 📏 Variable-length clips with context boundaries
- 🎯 Social media engagement optimization
- 💾 RAM-aware processing strategies
- 🔄 Cross-timeline reference detection (Phase 2)

Author: StreamClip AI Team
"""

import os
import logging
import uuid
from typing import List, Dict, Optional, Tuple
from moviepy.editor import VideoFileClip
import numpy as np

# Import our refactored ML analyzer
from ml_audio_analyzer import MLAudioAnalyzer

# Set up logging
logger = logging.getLogger(__name__)

class EnhancedVideoProcessor:
    """
    Enhanced video processor with ML-powered funny moment detection
    """
    
    def __init__(self, ram_optimize: bool = True):
        """
        Initialize the Enhanced Video Processor
        
        Args:
            ram_optimize: Enable RAM optimization
        """
        self.temp_dir = "temp"
        self.clips_dir = "clips"
        
        # Create directories if they don't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.clips_dir, exist_ok=True)
        
        # Initialize ML analyzer
        self.ml_analyzer = MLAudioAnalyzer(ram_optimize=ram_optimize)
        
        # Processing parameters
        self.max_segments_to_process = 50  # Reasonable limit for processing
        
        # Check FFmpeg availability
        self._check_ffmpeg_availability()
        
        logger.info("🚀 Enhanced Video Processor with ML initialized")
        logger.info(f"   Processing Strategy: {self.ml_analyzer.processing_strategy}")
    
    def _check_ffmpeg_availability(self):
        """Check if FFmpeg is available and accessible"""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("✅ FFmpeg is available and working")
            else:
                logger.warning("⚠️ FFmpeg may not be properly installed")
        except Exception as e:
            logger.error(f"❌ FFmpeg not found: {e}")
    
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
                "warnings": [],
                "ml_enhancement_available": True
            }
            
            # Check for common issues
            if clip.duration < 60:  # Less than 1 minute
                analysis["warnings"].append("Video is very short - may not have enough content for highlights")
            
            if clip.duration > 14400:  # More than 4 hours
                analysis["warnings"].append("Video is very long - ML analysis may take significant time")
            
            if not clip.audio:
                analysis["warnings"].append("No audio track - ML features will be limited")
                analysis["suitable_for_processing"] = False
                analysis["ml_enhancement_available"] = False
            
            if clip.fps < 15:
                analysis["warnings"].append("Low frame rate detected")
            
            clip.close()
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing video: {e}")
            return {
                "suitable_for_processing": False,
                "ml_enhancement_available": False,
                "error": str(e)
            }
    
    def process_video_ml(self, video_path: str, max_clips: int = None, 
                        audio_threshold: float = None, clip_duration: int = None) -> dict:
        """
        Main ML-enhanced video processing function
        
        Args:
            video_path: Path to the video file
            max_clips: Maximum clips to generate (optional - will use all best segments)
            audio_threshold: Legacy parameter (ignored - ML determines optimal segments)
            clip_duration: Legacy parameter (ignored - ML determines optimal lengths)
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"🚀 Starting ML-enhanced video processing: {video_path}")
            
            # Step 1: Validate video
            if not os.path.exists(video_path):
                return {"success": False, "error": f"Video file not found: {video_path}"}
            
            # Step 2: Analyze video quality
            video_analysis = self.analyze_video_quality(video_path)
            if not video_analysis["suitable_for_processing"]:
                return {
                    "success": False, 
                    "error": "Video not suitable for processing",
                    "analysis": video_analysis
                }
            
            # Step 3: Run ML audio analysis
            logger.info("🤖 Running ML audio analysis...")
            ml_results = self.ml_analyzer.analyze_audio_advanced(video_path)
            
            if not ml_results["success"]:
                return {
                    "success": False,
                    "error": f"ML analysis failed: {ml_results.get('error', 'Unknown error')}",
                    "analysis": video_analysis
                }
            
            # Step 4: Select best segments for clip generation
            best_segments = self._select_best_segments(ml_results["segments"], max_clips)
            
            if not best_segments:
                # Fallback to legacy processing if no ML segments found
                logger.warning("No ML segments detected, falling back to legacy processing")
                return self._fallback_to_legacy_processing(video_path, max_clips or 5, audio_threshold or 0.1, clip_duration or 30)
            
            # Step 5: Generate variable-length clips
            logger.info(f"🎬 Generating {len(best_segments)} variable-length clips...")
            clips = self._generate_variable_clips(video_path, best_segments)
            
            # Step 6: Prepare results
            result = {
                "success": True,
                "clips": clips,
                "timestamps": [seg["start_time"] for seg in best_segments],
                "analysis": {
                    "video_info": video_analysis,
                    "ml_analysis": ml_results,
                    "clips_generated": len(clips),
                    "segments_analyzed": len(ml_results["segments"]),
                    "processing_strategy": ml_results["processing_strategy"]
                },
                "stats": {
                    "total_segments_detected": ml_results["segments_detected"],
                    "clips_generated": len(clips),
                    "average_clip_duration": np.mean([seg["duration"] for seg in best_segments]) if best_segments else 0,
                    "excitement_types_detected": list(set([seg["excitement_type"] for seg in best_segments])),
                    "social_media_potential": np.mean([seg["social_media_potential"] for seg in best_segments]) if best_segments else 0
                }
            }
            
            logger.info(f"✅ ML processing complete: {len(clips)} clips generated")
            return result
            
        except Exception as e:
            logger.error(f"Error in ML video processing: {e}")
            return {"success": False, "error": str(e)}
    
    def _select_best_segments(self, segments: List[Dict], max_clips: Optional[int]) -> List[Dict]:
        """
        Select the best segments for clip generation
        
        Args:
            segments: List of detected segments from ML analysis
            max_clips: Maximum number of clips to generate
            
        Returns:
            List of selected segments
        """
        try:
            if not segments:
                return []
            
            # Segments are already ranked by excitement score from ML analyzer
            # Filter segments with good social media potential
            quality_segments = [
                seg for seg in segments 
                if seg["social_media_potential"] > 0.3 and seg["duration"] >= 20
            ]
            
            if not quality_segments:
                # If no high-quality segments, use top segments anyway
                quality_segments = segments[:min(len(segments), 10)]
            
            # If max_clips is specified, limit selection
            if max_clips is not None:
                selected_segments = quality_segments[:max_clips]
            else:
                # Use all quality segments up to our processing limit
                selected_segments = quality_segments[:self.max_segments_to_process]
            
            logger.info(f"🎯 Selected {len(selected_segments)} segments from {len(segments)} detected")
            
            # Log segment info for debugging
            for i, seg in enumerate(selected_segments[:5]):  # Log top 5
                logger.info(f"   #{i+1}: {seg['excitement_type']} | {seg['duration']:.1f}s | Score: {seg['total_excitement_score']:.2f} | Social: {seg['social_media_potential']:.2f}")
            
            return selected_segments
            
        except Exception as e:
            logger.error(f"Error selecting best segments: {e}")
            return segments[:max_clips] if max_clips else segments[:5]
    
    def _generate_variable_clips(self, video_path: str, segments: List[Dict]) -> List[str]:
        """
        Generate variable-length clips from selected segments
        
        Args:
            video_path: Path to the source video
            segments: List of segments to create clips from
            
        Returns:
            List of paths to generated clip files
        """
        clips = []
        
        try:
            logger.info(f"🎬 Generating clips from {video_path}")
            video = VideoFileClip(video_path)
            
            for i, segment in enumerate(segments):
                try:
                    start_time = segment["start_time"]
                    end_time = segment["end_time"]
                    excitement_type = segment["excitement_type"]
                    social_score = segment["social_media_potential"]
                    
                    # Validate segment boundaries
                    if end_time > video.duration:
                        end_time = video.duration
                    if start_time >= end_time:
                        logger.warning(f"Invalid segment {i+1}: start={start_time}, end={end_time}")
                        continue
                    
                    # Extract the clip
                    clip = video.subclip(start_time, end_time)
                    
                    # Generate descriptive filename
                    duration = end_time - start_time
                    clip_filename = f"clip_{i+1:02d}_{excitement_type}_{duration:.0f}s_{social_score:.2f}social.mp4"
                    clip_path = os.path.join(self.clips_dir, clip_filename)
                    
                    # Write the clip with optimized settings for social media
                    try:
                        clip.write_videofile(
                            clip_path,
                            codec='libx264',
                            audio_codec='aac',
                            temp_audiofile=os.path.join(self.temp_dir, f'temp_audio_{i+1:02d}.m4a'),
                            remove_temp=True,
                            verbose=False,
                            logger=None
                        )
                        
                        clips.append(clip_path)
                        clip.close()
                        
                        logger.info(f"✅ Generated clip {i+1}/{len(segments)}: {clip_filename}")
                        
                    except Exception as ffmpeg_error:
                        logger.warning(f"FFmpeg error for segment {i+1}: {ffmpeg_error}")
                        logger.info("Trying with basic video settings...")
                        
                        try:
                            clip.write_videofile(
                                clip_path,
                                verbose=False,
                                logger=None
                            )
                            clips.append(clip_path)
                            clip.close()
                            logger.info(f"✅ Generated clip {i+1} with basic settings")
                        except Exception as basic_error:
                            logger.error(f"Failed to create clip {i+1}: {basic_error}")
                            clip.close()
                            continue
                
                except Exception as e:
                    logger.error(f"Error creating clip {i+1}: {e}")
                    continue
            
            video.close()
            
            # Log final results
            logger.info(f"🎉 Successfully generated {len(clips)} clips from {len(segments)} segments")
            
            return clips
            
        except Exception as e:
            logger.error(f"Error generating variable clips: {e}")
            return []
    
    def _fallback_to_legacy_processing(self, video_path: str, max_clips: int, 
                                     audio_threshold: float, clip_duration: int) -> dict:
        """
        Fallback to legacy processing if ML analysis fails
        
        Args:
            video_path: Path to video file
            max_clips: Number of clips to generate
            audio_threshold: Audio threshold for peak detection
            clip_duration: Fixed clip duration
            
        Returns:
            Processing results in legacy format
        """
        try:
            logger.info("🔄 Using legacy processing as fallback")
            
            # Import legacy processor
            from video_processor import VideoProcessor
            legacy_processor = VideoProcessor()
            
            # Run legacy processing
            result = legacy_processor.process_video(
                video_path=video_path,
                clip_duration=clip_duration,
                max_clips=max_clips,
                audio_threshold=audio_threshold
            )
            
            # Add note about fallback
            if result.get("success"):
                if "analysis" not in result:
                    result["analysis"] = {}
                result["analysis"]["ml_processing"] = False
                result["analysis"]["fallback_reason"] = "ML analysis failed or no segments detected"
            
            return result
            
        except Exception as e:
            logger.error(f"Legacy fallback processing failed: {e}")
            return {"success": False, "error": f"Both ML and legacy processing failed: {str(e)}"}
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            temp_files = os.listdir(self.temp_dir)
            for file in temp_files:
                if file.startswith("temp_") or file.endswith(".m4a"):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        os.remove(file_path)
                        logger.debug(f"Cleaned up temp file: {file}")
                    except Exception as e:
                        logger.warning(f"Could not remove temp file {file}: {e}")
            
            logger.info("🧹 Temporary files cleaned up")
            
        except Exception as e:
            logger.warning(f"Error during temp file cleanup: {e}")
    
    # Backward compatibility methods
    def extract_audio_peaks(self, video_path: str, threshold: float = 0.1) -> List[float]:
        """
        Legacy method for backward compatibility
        
        Note: This method is deprecated. Use process_video_ml() for enhanced functionality.
        """
        logger.warning("extract_audio_peaks() is deprecated. Use process_video_ml() for ML-enhanced processing.")
        
        try:
            # Run ML analysis and extract timestamps for compatibility
            ml_results = self.ml_analyzer.analyze_audio_advanced(video_path)
            if ml_results["success"] and ml_results["segments"]:
                timestamps = [seg["start_time"] for seg in ml_results["segments"]]
                return timestamps[:10]  # Limit to reasonable number
            else:
                return []
        except Exception as e:
            logger.error(f"Error in legacy extract_audio_peaks: {e}")
            return []
    
    def extract_clips(self, video_path: str, timestamps: List[float], 
                     clip_duration: int = 30, max_clips: int = 5) -> List[str]:
        """
        Legacy method for backward compatibility
        
        Note: This method is deprecated. Use process_video_ml() for enhanced functionality.
        """
        logger.warning("extract_clips() is deprecated. Use process_video_ml() for ML-enhanced processing.")
        
        try:
            # Convert timestamps to segments and use ML processing
            segments = []
            for i, timestamp in enumerate(timestamps[:max_clips]):
                segments.append({
                    "start_time": max(0, timestamp - clip_duration // 2),
                    "end_time": timestamp + clip_duration // 2,
                    "duration": clip_duration,
                    "excitement_type": "legacy",
                    "social_media_potential": 0.5
                })
            
            return self._generate_variable_clips(video_path, segments)
            
        except Exception as e:
            logger.error(f"Error in legacy extract_clips: {e}")
            return []
    
    def process_video(self, video_path: str, clip_duration: int = 30, 
                     max_clips: int = 5, audio_threshold: float = 0.1) -> dict:
        """
        Legacy interface for backward compatibility
        
        Args:
            video_path: Path to the video file
            clip_duration: Ignored - ML determines optimal lengths
            max_clips: Maximum number of clips to generate
            audio_threshold: Ignored - ML determines optimal thresholds
            
        Returns:
            Dictionary with processing results
        """
        logger.info("🔄 Legacy process_video() called - routing to ML-enhanced processing")
        return self.process_video_ml(video_path, max_clips, audio_threshold, clip_duration) 