"""
🤖 ML-Enhanced Audio Analyzer for StreamClip AI
==============================================

Advanced audio analysis using machine learning and spectral analysis to detect:
- 😂 Funny moments (laughter, reactions)
- 😱 Shock/surprise moments (dramatic reactions)
- 🎉 Excitement peaks (hype moments)
- 💬 Context boundaries for variable-length clips
- 🔄 Reference detection for cross-timeline linking

Author: StreamClip AI Team
"""

import numpy as np
import librosa
import scipy.signal
from scipy import stats
import psutil
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import logging
from typing import List, Tuple, Dict, Optional
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

# Set up logging
logger = logging.getLogger(__name__)

class MLAudioAnalyzer:
    """
    Advanced ML-powered audio analyzer for detecting exciting moments and context boundaries
    """
    
    def __init__(self, ram_optimize: bool = True):
        """
        Initialize the ML Audio Analyzer
        
        Args:
            ram_optimize: Auto-detect and optimize for available RAM
        """
        self.ram_optimize = ram_optimize
        self.available_ram_gb = self._detect_available_ram()
        self.processing_strategy = self._determine_processing_strategy()
        
        # Audio analysis parameters
        self.sample_rate = 22050  # Standard for librosa
        self.hop_length = 512
        self.frame_length = 2048
        self.rolling_window_minutes = 15  # Rolling baseline window
        
        # Excitement detection thresholds (will be adaptive)
        self.excitement_types = {
            'laughter': {'freq_range': (300, 3000), 'weight': 1.2},  # Human laughter frequency
            'shock': {'freq_range': (1000, 8000), 'weight': 1.1},   # High-pitched reactions
            'hype': {'freq_range': (100, 1000), 'weight': 1.0},     # Deep excitement/bass
            'speech': {'freq_range': (85, 255), 'weight': 0.8}      # Speech fundamental frequency
        }
        
        # Context detection parameters
        self.min_clip_length = 20  # Minimum 20 seconds
        self.max_clip_length = 180  # Maximum 3 minutes
        self.context_buffer = 3    # 3-second buffer for smooth transitions
        self.merge_threshold = 30  # Merge clips within 30 seconds
        
        logger.info(f"🤖 ML Audio Analyzer initialized")
        logger.info(f"   RAM Strategy: {self.processing_strategy}")
        logger.info(f"   Available RAM: {self.available_ram_gb:.1f}GB")
    
    def _detect_available_ram(self) -> float:
        """Detect available system RAM in GB"""
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            total_gb = memory.total / (1024**3)
            
            logger.info(f"💾 RAM Detection: {available_gb:.1f}GB available / {total_gb:.1f}GB total")
            return available_gb
        except Exception as e:
            logger.warning(f"Could not detect RAM: {e}. Assuming 16GB.")
            return 16.0
    
    def _determine_processing_strategy(self) -> str:
        """Determine optimal processing strategy based on available RAM"""
        if self.available_ram_gb >= 32:
            return "high_memory"     # Load entire audio, parallel processing
        elif self.available_ram_gb >= 16:
            return "balanced"        # Chunk processing with reasonable buffers
        else:
            return "conservative"    # Stream processing, minimal memory usage
    
    def extract_spectral_features(self, audio_data: np.ndarray, sr: int) -> Dict[str, np.ndarray]:
        """
        Extract spectral features for ML analysis
        
        Args:
            audio_data: Audio time series
            sr: Sample rate
            
        Returns:
            Dictionary of spectral features
        """
        try:
            # Core spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=audio_data, sr=sr, hop_length=self.hop_length)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio_data, sr=sr, hop_length=self.hop_length)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio_data, sr=sr, hop_length=self.hop_length)[0]
            zero_crossing_rate = librosa.feature.zero_crossing_rate(audio_data, hop_length=self.hop_length)[0]
            
            # MFCC features (for voice/speech detection)
            mfccs = librosa.feature.mfcc(y=audio_data, sr=sr, n_mfcc=13, hop_length=self.hop_length)
            
            # RMS energy (our current baseline)
            rms = librosa.feature.rms(y=audio_data, hop_length=self.hop_length)[0]
            
            # Tempo and beat tracking for rhythm analysis
            tempo, beats = librosa.beat.beat_track(y=audio_data, sr=sr, hop_length=self.hop_length)
            
            # Onset detection (sudden sound events)
            onset_strength = librosa.onset.onset_strength(y=audio_data, sr=sr, hop_length=self.hop_length)
            
            features = {
                'spectral_centroid': spectral_centroids,
                'spectral_rolloff': spectral_rolloff,
                'spectral_bandwidth': spectral_bandwidth,
                'zero_crossing_rate': zero_crossing_rate,
                'mfccs': mfccs,
                'rms': rms,
                'tempo': tempo,
                'beats': beats,
                'onset_strength': onset_strength
            }
            
            logger.debug(f"Extracted {len(features)} spectral feature types")
            return features
            
        except Exception as e:
            logger.error(f"Error extracting spectral features: {e}")
            return {}
    
    def detect_excitement_types(self, features: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Classify different types of excitement using spectral features
        
        Args:
            features: Spectral features from extract_spectral_features
            
        Returns:
            Dictionary with excitement type scores over time
        """
        excitement_scores = {}
        
        try:
            # Get time axis length
            time_frames = len(features['rms'])
            
            # Laughter detection (high spectral centroid + irregular patterns)
            laughter_score = (
                features['spectral_centroid'] * 0.4 +
                features['zero_crossing_rate'] * 0.3 +
                features['spectral_bandwidth'] * 0.3
            )
            excitement_scores['laughter'] = laughter_score
            
            # Shock/surprise detection (sudden onset + high frequencies)
            shock_score = (
                features['onset_strength'] * 0.5 +
                features['spectral_rolloff'] * 0.3 +
                features['rms'] * 0.2
            )
            excitement_scores['shock'] = shock_score
            
            # Hype/excitement detection (strong bass + high energy)
            hype_score = (
                features['rms'] * 0.6 +
                features['onset_strength'] * 0.2 +
                np.mean(features['mfccs'][:3], axis=0) * 0.2  # Low MFCC coefficients
            )
            excitement_scores['hype'] = hype_score
            
            # Speech detection (MFCC patterns typical of speech)
            speech_score = np.mean(features['mfccs'][1:5], axis=0)  # Mid MFCC coefficients
            excitement_scores['speech'] = speech_score
            
            logger.debug(f"Detected {len(excitement_scores)} excitement types")
            return excitement_scores
            
        except Exception as e:
            logger.error(f"Error detecting excitement types: {e}")
            return {}
    
    def calculate_rolling_baseline(self, values: np.ndarray, window_minutes: int = 15, sr: int = 22050) -> np.ndarray:
        """
        Calculate rolling baseline for adaptive thresholding
        
        Args:
            values: Time series values
            window_minutes: Window size in minutes
            sr: Sample rate
            
        Returns:
            Rolling baseline values
        """
        try:
            # Convert window size to frames
            frames_per_second = sr / self.hop_length
            window_frames = int(window_minutes * 60 * frames_per_second)
            
            # Calculate rolling mean with same length as input
            baseline = np.convolve(values, np.ones(window_frames)/window_frames, mode='same')
            
            # Handle edge effects
            baseline[:window_frames//2] = baseline[window_frames//2]
            baseline[-window_frames//2:] = baseline[-window_frames//2]
            
            logger.debug(f"Calculated rolling baseline with {window_minutes}min window")
            return baseline
            
        except Exception as e:
            logger.error(f"Error calculating rolling baseline: {e}")
            return np.ones_like(values) * np.mean(values)
    
    def detect_context_boundaries(self, audio_data: np.ndarray, sr: int, excitement_scores: Dict[str, np.ndarray]) -> List[Tuple[float, float, str]]:
        """
        Detect natural context boundaries for variable-length clips
        
        Args:
            audio_data: Audio time series
            sr: Sample rate
            excitement_scores: Excitement type scores
            
        Returns:
            List of (start_time, end_time, excitement_type) tuples
        """
        try:
            # Convert frame indices to time
            times = librosa.frames_to_time(np.arange(len(excitement_scores['rms'])), sr=sr, hop_length=self.hop_length)
            
            # Combine all excitement scores into a composite score
            composite_score = np.zeros_like(excitement_scores['rms'])
            for exc_type, scores in excitement_scores.items():
                weight = self.excitement_types.get(exc_type, {}).get('weight', 1.0)
                composite_score += scores * weight
            
            # Calculate rolling baseline for adaptive thresholding
            baseline = self.calculate_rolling_baseline(composite_score, self.rolling_window_minutes, sr)
            adaptive_threshold = baseline * 1.2  # 20% above rolling average
            
            # Find peaks above adaptive threshold
            peaks, properties = scipy.signal.find_peaks(
                composite_score,
                height=adaptive_threshold,
                distance=int(10 * sr / self.hop_length),  # Minimum 10 seconds between peaks
                prominence=np.std(composite_score) * 0.5
            )
            
            # Convert peaks to context segments
            segments = []
            for peak_idx in peaks:
                peak_time = times[peak_idx]
                
                # Find context boundaries around peak
                start_idx, end_idx = self._find_context_boundaries(
                    composite_score, peak_idx, excitement_scores['speech']
                )
                
                start_time = max(0, times[start_idx] - self.context_buffer)
                end_time = min(times[-1], times[end_idx] + self.context_buffer)
                
                # Ensure minimum and maximum clip lengths
                duration = end_time - start_time
                if duration < self.min_clip_length:
                    # Extend clip to minimum length
                    center_time = (start_time + end_time) / 2
                    start_time = max(0, center_time - self.min_clip_length / 2)
                    end_time = min(times[-1], center_time + self.min_clip_length / 2)
                elif duration > self.max_clip_length:
                    # Trim clip to maximum length
                    center_time = peak_time
                    start_time = max(0, center_time - self.max_clip_length / 2)
                    end_time = min(times[-1], center_time + self.max_clip_length / 2)
                
                # Determine dominant excitement type for this segment
                segment_start_idx = max(0, start_idx - 10)
                segment_end_idx = min(len(times), end_idx + 10)
                dominant_type = self._get_dominant_excitement_type(excitement_scores, segment_start_idx, segment_end_idx)
                
                segments.append((start_time, end_time, dominant_type))
            
            logger.info(f"🎯 Detected {len(segments)} context-aware segments")
            return segments
            
        except Exception as e:
            logger.error(f"Error detecting context boundaries: {e}")
            return []
    
    def _find_context_boundaries(self, composite_score: np.ndarray, peak_idx: int, speech_score: np.ndarray) -> Tuple[int, int]:
        """
        Find natural start and end points around a peak
        
        Args:
            composite_score: Overall excitement score
            peak_idx: Index of the peak
            speech_score: Speech detection score
            
        Returns:
            (start_idx, end_idx) tuple
        """
        try:
            # Look backwards for start boundary
            start_idx = peak_idx
            for i in range(peak_idx, max(0, peak_idx - 100), -1):  # Look back up to ~45 seconds
                # Look for natural breaks: low energy + low speech activity
                if (composite_score[i] < composite_score[peak_idx] * 0.3 and 
                    speech_score[i] < np.mean(speech_score) * 0.5):
                    start_idx = i
                    break
            
            # Look forwards for end boundary
            end_idx = peak_idx
            for i in range(peak_idx, min(len(composite_score), peak_idx + 100)):  # Look ahead up to ~45 seconds
                # Look for natural breaks: low energy + low speech activity
                if (composite_score[i] < composite_score[peak_idx] * 0.3 and 
                    speech_score[i] < np.mean(speech_score) * 0.5):
                    end_idx = i
                    break
            
            return start_idx, end_idx
            
        except Exception as e:
            logger.error(f"Error finding context boundaries: {e}")
            return peak_idx - 50, peak_idx + 50  # Fallback to fixed window
    
    def _get_dominant_excitement_type(self, excitement_scores: Dict[str, np.ndarray], start_idx: int, end_idx: int) -> str:
        """
        Determine the dominant type of excitement in a segment
        
        Args:
            excitement_scores: All excitement type scores
            start_idx: Segment start index
            end_idx: Segment end index
            
        Returns:
            Dominant excitement type string
        """
        try:
            segment_averages = {}
            for exc_type, scores in excitement_scores.items():
                if exc_type in self.excitement_types:
                    segment_avg = np.mean(scores[start_idx:end_idx])
                    segment_averages[exc_type] = segment_avg
            
            if segment_averages:
                dominant_type = max(segment_averages.keys(), key=lambda k: segment_averages[k])
                return dominant_type
            else:
                return 'general'
                
        except Exception as e:
            logger.error(f"Error determining dominant excitement type: {e}")
            return 'general'
    
    def merge_nearby_segments(self, segments: List[Tuple[float, float, str]]) -> List[Tuple[float, float, str]]:
        """
        Merge segments that are close together for better context
        
        Args:
            segments: List of (start_time, end_time, excitement_type) tuples
            
        Returns:
            List of merged segments
        """
        if not segments:
            return segments
        
        try:
            # Sort segments by start time
            sorted_segments = sorted(segments, key=lambda x: x[0])
            merged_segments = [sorted_segments[0]]
            
            for current_segment in sorted_segments[1:]:
                last_merged = merged_segments[-1]
                
                # Check if segments should be merged (within merge_threshold seconds)
                gap = current_segment[0] - last_merged[1]
                if gap <= self.merge_threshold:
                    # Merge segments
                    new_start = last_merged[0]
                    new_end = current_segment[1]
                    
                    # Choose the more exciting type or combine if different
                    if last_merged[2] == current_segment[2]:
                        new_type = last_merged[2]
                    else:
                        new_type = f"{last_merged[2]}+{current_segment[2]}"
                    
                    merged_segments[-1] = (new_start, new_end, new_type)
                    logger.debug(f"Merged segments: {gap:.1f}s gap -> {new_type}")
                else:
                    merged_segments.append(current_segment)
            
            logger.info(f"🔗 Merged {len(segments)} segments into {len(merged_segments)}")
            return merged_segments
            
        except Exception as e:
            logger.error(f"Error merging segments: {e}")
            return segments
    
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
            
            # Load audio with librosa
            logger.info("📥 Loading audio data...")
            audio_data, sr = librosa.load(audio_path, sr=self.sample_rate)
            duration = len(audio_data) / sr
            
            logger.info(f"🎵 Audio loaded: {duration:.1f}s at {sr}Hz")
            
            # Extract spectral features
            logger.info("🔬 Extracting spectral features...")
            features = self.extract_spectral_features(audio_data, sr)
            
            if not features:
                logger.error("Failed to extract features")
                return {"success": False, "error": "Feature extraction failed"}
            
            # Detect different types of excitement
            logger.info("🎯 Detecting excitement types...")
            excitement_scores = self.detect_excitement_types(features)
            
            # Find context-aware segments
            logger.info("📍 Detecting context boundaries...")
            segments = self.detect_context_boundaries(audio_data, sr, excitement_scores)
            
            # Merge nearby segments for better context
            logger.info("🔗 Merging nearby segments...")
            merged_segments = self.merge_nearby_segments(segments)
            
            # Rank segments by excitement score
            ranked_segments = self._rank_segments_by_excitement(merged_segments, excitement_scores, sr)
            
            # Prepare analysis results
            analysis_results = {
                "success": True,
                "duration": duration,
                "segments_detected": len(ranked_segments),
                "processing_strategy": self.processing_strategy,
                "segments": ranked_segments,
                "excitement_stats": self._calculate_excitement_stats(excitement_scores),
                "feature_summary": self._summarize_features(features)
            }
            
            logger.info(f"✅ ML analysis complete: {len(ranked_segments)} segments detected")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in ML audio analysis: {e}")
            return {"success": False, "error": str(e)}
    
    def _rank_segments_by_excitement(self, segments: List[Tuple[float, float, str]], 
                                   excitement_scores: Dict[str, np.ndarray], sr: int) -> List[Dict]:
        """
        Rank segments by their excitement level for clip selection
        
        Args:
            segments: List of segments
            excitement_scores: Excitement scores over time
            sr: Sample rate
            
        Returns:
            Ranked list of segment dictionaries
        """
        try:
            ranked_segments = []
            
            for start_time, end_time, exc_type in segments:
                # Convert times to frame indices
                start_frame = int(start_time * sr / self.hop_length)
                end_frame = int(end_time * sr / self.hop_length)
                
                # Calculate average excitement for this segment
                segment_excitement = {}
                total_excitement = 0
                
                for score_type, scores in excitement_scores.items():
                    if score_type in self.excitement_types:
                        segment_avg = np.mean(scores[start_frame:end_frame])
                        weight = self.excitement_types[score_type]['weight']
                        weighted_score = segment_avg * weight
                        segment_excitement[score_type] = float(segment_avg)
                        total_excitement += weighted_score
                
                # Create segment dictionary
                segment_dict = {
                    "start_time": float(start_time),
                    "end_time": float(end_time),
                    "duration": float(end_time - start_time),
                    "excitement_type": exc_type,
                    "total_excitement_score": float(total_excitement),
                    "excitement_breakdown": segment_excitement,
                    "social_media_potential": self._calculate_social_media_score(segment_excitement, exc_type)
                }
                
                ranked_segments.append(segment_dict)
            
            # Sort by total excitement score (highest first)
            ranked_segments.sort(key=lambda x: x["total_excitement_score"], reverse=True)
            
            # Add ranking
            for i, segment in enumerate(ranked_segments):
                segment["rank"] = i + 1
            
            return ranked_segments
            
        except Exception as e:
            logger.error(f"Error ranking segments: {e}")
            return []
    
    def _calculate_social_media_score(self, excitement_breakdown: Dict[str, float], exc_type: str) -> float:
        """
        Calculate social media engagement potential score
        
        Args:
            excitement_breakdown: Breakdown of excitement types
            exc_type: Primary excitement type
            
        Returns:
            Social media potential score (0-1)
        """
        try:
            # Base score from excitement levels
            base_score = 0
            
            # Laughter is highly engaging on social media
            if 'laughter' in excitement_breakdown:
                base_score += excitement_breakdown['laughter'] * 0.4
            
            # Shock/surprise moments go viral
            if 'shock' in excitement_breakdown:
                base_score += excitement_breakdown['shock'] * 0.3
            
            # Hype moments are good for engagement
            if 'hype' in excitement_breakdown:
                base_score += excitement_breakdown['hype'] * 0.2
            
            # Speech adds context
            if 'speech' in excitement_breakdown:
                base_score += excitement_breakdown['speech'] * 0.1
            
            # Bonus for mixed excitement types (more engaging)
            if '+' in exc_type:
                base_score *= 1.2
            
            # Normalize to 0-1 range
            social_score = min(1.0, max(0.0, base_score))
            
            return float(social_score)
            
        except Exception as e:
            logger.error(f"Error calculating social media score: {e}")
            return 0.5
    
    def _calculate_excitement_stats(self, excitement_scores: Dict[str, np.ndarray]) -> Dict:
        """Calculate summary statistics for excitement detection"""
        try:
            stats = {}
            for exc_type, scores in excitement_scores.items():
                if exc_type in self.excitement_types:
                    stats[exc_type] = {
                        "mean": float(np.mean(scores)),
                        "max": float(np.max(scores)),
                        "std": float(np.std(scores)),
                        "peaks_detected": int(len(scipy.signal.find_peaks(scores, height=np.mean(scores) * 1.5)[0]))
                    }
            return stats
        except Exception as e:
            logger.error(f"Error calculating excitement stats: {e}")
            return {}
    
    def _summarize_features(self, features: Dict[str, np.ndarray]) -> Dict:
        """Summarize extracted features for logging"""
        try:
            summary = {}
            for feature_name, feature_data in features.items():
                if isinstance(feature_data, np.ndarray):
                    if feature_data.ndim == 1:
                        summary[feature_name] = {
                            "mean": float(np.mean(feature_data)),
                            "std": float(np.std(feature_data))
                        }
                    else:
                        summary[feature_name] = {
                            "shape": feature_data.shape,
                            "mean": float(np.mean(feature_data))
                        }
                else:
                    summary[feature_name] = str(feature_data)
            return summary
        except Exception as e:
            logger.error(f"Error summarizing features: {e}")
            return {} 