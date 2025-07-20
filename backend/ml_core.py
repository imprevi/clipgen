"""
🧠 Core ML Functionality for Audio Analysis
==========================================

Separated core ML algorithms for easier debugging and testing.
Contains spectral analysis and excitement detection logic.

Author: StreamClip AI Team
"""

import numpy as np
import librosa
import scipy.signal
from typing import Dict, Tuple
import logging

# Import performance optimizations
from performance_optimizer import cached, timed, memory_manager

logger = logging.getLogger(__name__)

class SpectralAnalyzer:
    """Core spectral analysis functionality"""
    
    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.frame_length = 2048
        
    @cached(persist=True)
    @timed
    def extract_features(self, audio_data: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Extract spectral features from audio data
        
        Args:
            audio_data: Audio time series
            
        Returns:
            Dictionary of spectral features
        """
        try:
            logger.debug("Extracting spectral features...")
            
            features = {}
            
            # Core spectral features
            features['spectral_centroid'] = librosa.feature.spectral_centroid(
                y=audio_data, sr=self.sample_rate, hop_length=self.hop_length)[0]
            
            features['spectral_rolloff'] = librosa.feature.spectral_rolloff(
                y=audio_data, sr=self.sample_rate, hop_length=self.hop_length)[0]
            
            features['spectral_bandwidth'] = librosa.feature.spectral_bandwidth(
                y=audio_data, sr=self.sample_rate, hop_length=self.hop_length)[0]
            
            features['zero_crossing_rate'] = librosa.feature.zero_crossing_rate(
                audio_data, hop_length=self.hop_length)[0]
            
            # MFCC features for voice detection
            features['mfccs'] = librosa.feature.mfcc(
                y=audio_data, sr=self.sample_rate, n_mfcc=13, hop_length=self.hop_length)
            
            # Energy features
            features['rms'] = librosa.feature.rms(
                y=audio_data, hop_length=self.hop_length)[0]
            
            # Rhythm features
            tempo, beats = librosa.beat.beat_track(
                y=audio_data, sr=self.sample_rate, hop_length=self.hop_length)
            features['tempo'] = tempo
            features['beats'] = beats
            
            # Onset detection
            features['onset_strength'] = librosa.onset.onset_strength(
                y=audio_data, sr=self.sample_rate, hop_length=self.hop_length)
            
            logger.debug(f"Extracted {len(features)} feature types")
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return {}

class ExcitementDetector:
    """Detects different types of excitement from spectral features"""
    
    def __init__(self):
        self.excitement_weights = {
            'laughter': {'weight': 1.2, 'freq_range': (300, 3000)},
            'shock': {'weight': 1.1, 'freq_range': (1000, 8000)},
            'hype': {'weight': 1.0, 'freq_range': (100, 1000)},
            'speech': {'weight': 0.8, 'freq_range': (85, 255)}
        }
    
    def analyze_excitement(self, features: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Classify excitement types from spectral features
        
        Args:
            features: Spectral features dictionary
            
        Returns:
            Dictionary with excitement scores over time
        """
        try:
            excitement_scores = {}
            
            # Laughter detection: high spectral features + irregular patterns
            laughter_score = (
                self._normalize(features['spectral_centroid']) * 0.4 +
                self._normalize(features['zero_crossing_rate']) * 0.3 +
                self._normalize(features['spectral_bandwidth']) * 0.3
            )
            excitement_scores['laughter'] = laughter_score
            
            # Shock detection: sudden onsets + high frequencies  
            shock_score = (
                self._normalize(features['onset_strength']) * 0.5 +
                self._normalize(features['spectral_rolloff']) * 0.3 +
                self._normalize(features['rms']) * 0.2
            )
            excitement_scores['shock'] = shock_score
            
            # Hype detection: strong energy + bass
            hype_score = (
                self._normalize(features['rms']) * 0.6 +
                self._normalize(features['onset_strength']) * 0.2 +
                self._normalize(np.mean(features['mfccs'][:3], axis=0)) * 0.2
            )
            excitement_scores['hype'] = hype_score
            
            # Speech detection: MFCC patterns
            speech_score = self._normalize(np.mean(features['mfccs'][1:5], axis=0))
            excitement_scores['speech'] = speech_score
            
            logger.debug(f"Generated {len(excitement_scores)} excitement types")
            return excitement_scores
            
        except Exception as e:
            logger.error(f"Excitement analysis failed: {e}")
            return {}
    
    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """Normalize data to 0-1 range"""
        try:
            if np.std(data) == 0:
                return np.zeros_like(data)
            return (data - np.min(data)) / (np.max(data) - np.min(data))
        except:
            return np.zeros_like(data)

class BaselineCalculator:
    """Calculates rolling baseline for adaptive thresholding"""
    
    def __init__(self, window_minutes: int = 15):
        self.window_minutes = window_minutes
    
    def calculate_rolling_baseline(self, values: np.ndarray, 
                                 sample_rate: int = 22050, 
                                 hop_length: int = 512) -> np.ndarray:
        """
        Calculate rolling baseline for adaptive thresholding
        
        Args:
            values: Time series values
            sample_rate: Audio sample rate
            hop_length: Hop length for frame calculation
            
        Returns:
            Rolling baseline values
        """
        try:
            # Convert window size to frames
            frames_per_second = sample_rate / hop_length
            window_frames = int(self.window_minutes * 60 * frames_per_second)
            
            if window_frames >= len(values):
                # Window too large, use mean
                return np.full_like(values, np.mean(values))
            
            # Calculate rolling mean
            baseline = np.convolve(values, np.ones(window_frames)/window_frames, mode='same')
            
            # Handle edge effects
            half_window = window_frames // 2
            baseline[:half_window] = baseline[half_window]
            baseline[-half_window:] = baseline[-half_window]
            
            logger.debug(f"Calculated rolling baseline with {self.window_minutes}min window")
            return baseline
            
        except Exception as e:
            logger.error(f"Baseline calculation failed: {e}")
            return np.ones_like(values) * np.mean(values)

class PeakDetector:
    """Detects peaks in excitement signals"""
    
    def __init__(self, min_distance_seconds: int = 10):
        self.min_distance_seconds = min_distance_seconds
    
    def find_peaks(self, signal: np.ndarray, baseline: np.ndarray,
                   sample_rate: int = 22050, hop_length: int = 512) -> Tuple[np.ndarray, Dict]:
        """
        Find peaks above adaptive baseline
        
        Args:
            signal: Input signal
            baseline: Adaptive baseline
            sample_rate: Audio sample rate  
            hop_length: Hop length for frame calculation
            
        Returns:
            Tuple of (peak_indices, peak_properties)
        """
        try:
            # Calculate adaptive threshold
            adaptive_threshold = baseline * 1.2  # 20% above baseline
            
            # Calculate minimum distance in frames
            frames_per_second = sample_rate / hop_length
            min_distance_frames = int(self.min_distance_seconds * frames_per_second)
            
            # Find peaks
            peaks, properties = scipy.signal.find_peaks(
                signal,
                height=adaptive_threshold,
                distance=min_distance_frames,
                prominence=np.std(signal) * 0.5
            )
            
            logger.debug(f"Found {len(peaks)} peaks")
            return peaks, properties
            
        except Exception as e:
            logger.error(f"Peak detection failed: {e}")
            return np.array([]), {}

def validate_audio_input(audio_data: np.ndarray, sample_rate: int) -> bool:
    """
    Validate audio input for processing
    
    Args:
        audio_data: Audio time series
        sample_rate: Sample rate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if audio_data is None or len(audio_data) == 0:
            logger.warning("Empty audio data")
            return False
        
        if sample_rate <= 0:
            logger.warning("Invalid sample rate")
            return False
        
        duration = len(audio_data) / sample_rate
        if duration < 10:  # Less than 10 seconds
            logger.warning(f"Audio too short: {duration:.1f}s")
            return False
        
        if duration > 14400:  # More than 4 hours
            logger.warning(f"Audio very long: {duration/3600:.1f}h - may take significant time")
        
        return True
        
    except Exception as e:
        logger.error(f"Audio validation failed: {e}")
        return False 