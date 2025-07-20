"""
🤖 Refactored ML Audio Analyzer
==============================

Clean, modular audio analyzer that uses focused components for better debugging.
Reduced from 610 lines to ~200 lines with better separation of concerns.

Author: StreamClip AI Team
"""

import librosa
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

# Import our modular components
from ml_core import SpectralAnalyzer, ExcitementDetector, BaselineCalculator, PeakDetector, validate_audio_input
from system_detector import SystemDetector, ProcessingConfig

logger = logging.getLogger(__name__)

class MLAudioAnalyzer:
    """
    Simplified ML-powered audio analyzer with modular components
    """
    
    def __init__(self, ram_optimize: bool = True):
        """
        Initialize the ML Audio Analyzer
        
        Args:
            ram_optimize: Enable RAM optimization
        """
        # Initialize system detection
        self.system_detector = SystemDetector()
        self.config = ProcessingConfig(self.system_detector)
        
        # Initialize processing components
        self.spectral_analyzer = SpectralAnalyzer(
            sample_rate=self.config.sample_rate,
            hop_length=self.config.hop_length
        )
        self.excitement_detector = ExcitementDetector()
        self.baseline_calculator = BaselineCalculator(
            window_minutes=self.config.rolling_window_minutes
        )
        self.peak_detector = PeakDetector(min_distance_seconds=10)
        
        # For compatibility with existing code
        self.available_ram_gb = self.system_detector.available_ram_gb
        self.processing_strategy = self.system_detector.processing_strategy
        self.excitement_types = self.config.get_excitement_types()
        
        logger.info("🤖 ML Audio Analyzer (Refactored) initialized")
        logger.info(f"   Strategy: {self.processing_strategy}")
        logger.info(f"   Window: {self.config.rolling_window_minutes}min")
    
    def analyze_audio_advanced(self, audio_path: str) -> Dict:
        """
        Main method: Advanced ML-powered audio analysis
        
        Args:
            audio_path: Path to audio/video file
            
        Returns:
            Dictionary with analysis results and detected segments
        """
        try:
            logger.info(f"🤖 Starting ML audio analysis: {audio_path}")
            
            # Step 1: Load and validate audio
            audio_data, sr = self._load_audio(audio_path)
            if audio_data is None:
                return {"success": False, "error": "Failed to load audio"}
            
            # Step 2: Extract spectral features
            logger.info("🔬 Extracting spectral features...")
            features = self.spectral_analyzer.extract_features(audio_data)
            if not features:
                return {"success": False, "error": "Feature extraction failed"}
            
            # Step 3: Detect excitement types
            logger.info("🎯 Detecting excitement types...")
            excitement_scores = self.excitement_detector.analyze_excitement(features)
            if not excitement_scores:
                return {"success": False, "error": "Excitement detection failed"}
            
            # Step 4: Find context-aware segments
            logger.info("📍 Finding context boundaries...")
            segments = self._detect_segments(audio_data, sr, excitement_scores)
            
            # Step 5: Rank and prepare results
            ranked_segments = self._rank_segments(segments, excitement_scores, sr)
            
            # Prepare results
            duration = len(audio_data) / sr
            analysis_results = {
                "success": True,
                "duration": duration,
                "segments_detected": len(ranked_segments),
                "processing_strategy": self.processing_strategy,
                "segments": ranked_segments,
                "excitement_stats": self._calculate_stats(excitement_scores),
                "feature_summary": self._summarize_features(features)
            }
            
            logger.info(f"✅ ML analysis complete: {len(ranked_segments)} segments detected")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in ML audio analysis: {e}")
            return {"success": False, "error": str(e)}
    
    def _load_audio(self, audio_path: str) -> Tuple[Optional[np.ndarray], int]:
        """
        Load and validate audio data
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate) or (None, 0) if failed
        """
        try:
            logger.info("📥 Loading audio data...")
            audio_data, sr = librosa.load(audio_path, sr=self.config.sample_rate)
            
            if not validate_audio_input(audio_data, sr):
                return None, 0
            
            duration = len(audio_data) / sr
            logger.info(f"🎵 Audio loaded: {duration:.1f}s at {sr}Hz")
            return audio_data, sr
            
        except Exception as e:
            logger.error(f"Failed to load audio: {e}")
            return None, 0
    
    def _detect_segments(self, audio_data: np.ndarray, sr: int, 
                        excitement_scores: Dict[str, np.ndarray]) -> List[Tuple[float, float, str]]:
        """
        Detect context-aware segments using peak detection
        
        Args:
            audio_data: Audio time series
            sr: Sample rate
            excitement_scores: Excitement scores over time
            
        Returns:
            List of (start_time, end_time, excitement_type) tuples
        """
        try:
            # Create composite excitement score
            composite_score = self._create_composite_score(excitement_scores)
            
            # Calculate adaptive baseline
            baseline = self.baseline_calculator.calculate_rolling_baseline(
                composite_score, sr, self.config.hop_length
            )
            
            # Find peaks
            peaks, _ = self.peak_detector.find_peaks(
                composite_score, baseline, sr, self.config.hop_length
            )
            
            # Convert peaks to time-based segments
            segments = self._peaks_to_segments(peaks, composite_score, excitement_scores, sr)
            
            # Merge nearby segments
            merged_segments = self._merge_segments(segments)
            
            logger.info(f"🎯 Detected {len(merged_segments)} segments")
            return merged_segments
            
        except Exception as e:
            logger.error(f"Segment detection failed: {e}")
            return []
    
    def _create_composite_score(self, excitement_scores: Dict[str, np.ndarray]) -> np.ndarray:
        """Create weighted composite excitement score"""
        composite_score = np.zeros_like(excitement_scores['rms'])
        
        for exc_type, scores in excitement_scores.items():
            if exc_type in self.excitement_types:
                weight = self.excitement_types[exc_type]['weight']
                composite_score += scores * weight
        
        return composite_score
    
    def _peaks_to_segments(self, peaks: np.ndarray, composite_score: np.ndarray,
                          excitement_scores: Dict[str, np.ndarray], sr: int) -> List[Tuple[float, float, str]]:
        """Convert peak indices to time-based segments"""
        segments = []
        times = librosa.frames_to_time(
            np.arange(len(composite_score)), sr=sr, hop_length=self.config.hop_length
        )
        
        for peak_idx in peaks:
            if peak_idx >= len(times):
                continue
                
            peak_time = times[peak_idx]
            
            # Find natural boundaries
            start_idx, end_idx = self._find_boundaries(peak_idx, composite_score, excitement_scores['speech'])
            
            start_time = max(0, times[start_idx] - self.config.context_buffer)
            end_time = min(times[-1], times[end_idx] + self.config.context_buffer)
            
            # Ensure clip length constraints
            start_time, end_time = self._adjust_clip_length(start_time, end_time, peak_time, times[-1])
            
            # Determine dominant excitement type
            excitement_type = self._get_dominant_type(excitement_scores, start_idx, end_idx)
            
            segments.append((start_time, end_time, excitement_type))
        
        return segments
    
    def _find_boundaries(self, peak_idx: int, composite_score: np.ndarray, 
                        speech_score: np.ndarray) -> Tuple[int, int]:
        """Find natural start and end boundaries around a peak"""
        # Look backwards for start
        start_idx = peak_idx
        for i in range(peak_idx, max(0, peak_idx - 100), -1):
            if (composite_score[i] < composite_score[peak_idx] * 0.3 and 
                speech_score[i] < np.mean(speech_score) * 0.5):
                start_idx = i
                break
        
        # Look forwards for end
        end_idx = peak_idx
        for i in range(peak_idx, min(len(composite_score), peak_idx + 100)):
            if (composite_score[i] < composite_score[peak_idx] * 0.3 and 
                speech_score[i] < np.mean(speech_score) * 0.5):
                end_idx = i
                break
        
        return start_idx, end_idx
    
    def _adjust_clip_length(self, start_time: float, end_time: float, 
                           peak_time: float, max_time: float) -> Tuple[float, float]:
        """Adjust clip length to meet constraints"""
        duration = end_time - start_time
        
        if duration < self.config.min_clip_length:
            # Extend to minimum length
            center_time = (start_time + end_time) / 2
            start_time = max(0, center_time - self.config.min_clip_length / 2)
            end_time = min(max_time, center_time + self.config.min_clip_length / 2)
        elif duration > self.config.max_clip_length:
            # Trim to maximum length
            start_time = max(0, peak_time - self.config.max_clip_length / 2)
            end_time = min(max_time, peak_time + self.config.max_clip_length / 2)
        
        return start_time, end_time
    
    def _get_dominant_type(self, excitement_scores: Dict[str, np.ndarray], 
                          start_idx: int, end_idx: int) -> str:
        """Determine dominant excitement type in segment"""
        try:
            segment_averages = {}
            for exc_type, scores in excitement_scores.items():
                if exc_type in self.excitement_types:
                    segment_avg = np.mean(scores[start_idx:end_idx])
                    segment_averages[exc_type] = segment_avg
            
            if segment_averages:
                return max(segment_averages.keys(), key=lambda k: segment_averages[k])
            else:
                return 'general'
        except:
            return 'general'
    
    def _merge_segments(self, segments: List[Tuple[float, float, str]]) -> List[Tuple[float, float, str]]:
        """Merge segments that are close together"""
        if not segments:
            return segments
        
        sorted_segments = sorted(segments, key=lambda x: x[0])
        merged = [sorted_segments[0]]
        
        for current in sorted_segments[1:]:
            last = merged[-1]
            gap = current[0] - last[1]
            
            if gap <= self.config.merge_threshold:
                # Merge segments
                new_type = last[2] if last[2] == current[2] else f"{last[2]}+{current[2]}"
                merged[-1] = (last[0], current[1], new_type)
            else:
                merged.append(current)
        
        return merged
    
    def _rank_segments(self, segments: List[Tuple[float, float, str]], 
                      excitement_scores: Dict[str, np.ndarray], sr: int) -> List[Dict]:
        """Rank segments by excitement level"""
        ranked_segments = []
        
        for start_time, end_time, exc_type in segments:
            # Convert to frame indices
            start_frame = int(start_time * sr / self.config.hop_length)
            end_frame = int(end_time * sr / self.config.hop_length)
            
            # Calculate segment excitement scores
            segment_excitement = {}
            total_excitement = 0
            
            for score_type, scores in excitement_scores.items():
                if score_type in self.excitement_types:
                    segment_avg = np.mean(scores[start_frame:end_frame])
                    weight = self.excitement_types[score_type]['weight']
                    weighted_score = segment_avg * weight
                    segment_excitement[score_type] = float(segment_avg)
                    total_excitement += weighted_score
            
            # Calculate social media score
            social_score = self._calculate_social_score(segment_excitement, exc_type)
            
            segment_dict = {
                "start_time": float(start_time),
                "end_time": float(end_time),
                "duration": float(end_time - start_time),
                "excitement_type": exc_type,
                "total_excitement_score": float(total_excitement),
                "excitement_breakdown": segment_excitement,
                "social_media_potential": social_score
            }
            
            ranked_segments.append(segment_dict)
        
        # Sort by total excitement score
        ranked_segments.sort(key=lambda x: x["total_excitement_score"], reverse=True)
        
        # Add ranking
        for i, segment in enumerate(ranked_segments):
            segment["rank"] = i + 1
        
        return ranked_segments
    
    def _calculate_social_score(self, excitement_breakdown: Dict[str, float], exc_type: str) -> float:
        """Calculate social media engagement potential"""
        base_score = 0
        
        # Weight by engagement potential
        if 'laughter' in excitement_breakdown:
            base_score += excitement_breakdown['laughter'] * 0.4
        if 'shock' in excitement_breakdown:
            base_score += excitement_breakdown['shock'] * 0.3
        if 'hype' in excitement_breakdown:
            base_score += excitement_breakdown['hype'] * 0.2
        if 'speech' in excitement_breakdown:
            base_score += excitement_breakdown['speech'] * 0.1
        
        # Bonus for mixed types
        if '+' in exc_type:
            base_score *= 1.2
        
        return min(1.0, max(0.0, base_score))
    
    def _calculate_stats(self, excitement_scores: Dict[str, np.ndarray]) -> Dict:
        """Calculate summary statistics"""
        stats = {}
        for exc_type, scores in excitement_scores.items():
            if exc_type in self.excitement_types:
                stats[exc_type] = {
                    "mean": float(np.mean(scores)),
                    "max": float(np.max(scores)),
                    "std": float(np.std(scores))
                }
        return stats
    
    def _summarize_features(self, features: Dict[str, np.ndarray]) -> Dict:
        """Summarize features for logging"""
        summary = {}
        for name, data in features.items():
            if isinstance(data, np.ndarray):
                if data.ndim == 1:
                    summary[name] = {"mean": float(np.mean(data)), "std": float(np.std(data))}
                else:
                    summary[name] = {"shape": data.shape, "mean": float(np.mean(data))}
            else:
                summary[name] = str(data)
        return summary 