"""
💾 System Detection and Configuration
===================================

Handles RAM detection, processing strategy selection, and system optimization.
Separated for easier testing and debugging.

Author: StreamClip AI Team
"""

import psutil
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class SystemDetector:
    """Detects system capabilities and determines optimal processing strategies"""
    
    def __init__(self):
        self.available_ram_gb = self.detect_available_ram()
        self.processing_strategy = self.determine_processing_strategy()
        
        logger.info(f"💾 System Detection Complete:")
        logger.info(f"   RAM: {self.available_ram_gb:.1f}GB available")  
        logger.info(f"   Strategy: {self.processing_strategy}")
    
    def detect_available_ram(self) -> float:
        """
        Detect available system RAM in GB
        
        Returns:
            Available RAM in GB
        """
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            total_gb = memory.total / (1024**3)
            
            logger.debug(f"RAM: {available_gb:.1f}GB available / {total_gb:.1f}GB total")
            return available_gb
            
        except Exception as e:
            logger.warning(f"Could not detect RAM: {e}. Assuming 16GB.")
            return 16.0
    
    def determine_processing_strategy(self) -> str:
        """
        Determine optimal processing strategy based on available RAM
        
        Returns:
            Processing strategy name
        """
        if self.available_ram_gb >= 32:
            return "high_memory"     # Load entire audio, parallel processing
        elif self.available_ram_gb >= 16:  
            return "balanced"        # Chunk processing with reasonable buffers
        else:
            return "conservative"    # Stream processing, minimal memory usage
    
    def get_chunk_size(self) -> int:
        """
        Get optimal chunk size for processing based on strategy
        
        Returns:
            Chunk size in seconds
        """
        strategy_chunks = {
            "high_memory": 300,     # 5 minutes
            "balanced": 120,        # 2 minutes  
            "conservative": 60      # 1 minute
        }
        
        return strategy_chunks.get(self.processing_strategy, 60)
    
    def get_max_concurrent_jobs(self) -> int:
        """
        Get maximum concurrent processing jobs based on system resources
        
        Returns:
            Maximum concurrent jobs
        """
        if self.processing_strategy == "high_memory":
            return 3
        elif self.processing_strategy == "balanced":
            return 2
        else:
            return 1
    
    def should_use_parallel_processing(self) -> bool:
        """
        Determine if parallel processing should be used
        
        Returns:
            True if parallel processing is recommended
        """
        return self.processing_strategy in ["high_memory", "balanced"]
    
    def get_memory_limit_mb(self) -> int:
        """
        Get memory limit for individual operations in MB
        
        Returns:
            Memory limit in MB
        """
        limits = {
            "high_memory": 8192,    # 8GB
            "balanced": 4096,       # 4GB
            "conservative": 2048    # 2GB
        }
        
        return limits.get(self.processing_strategy, 2048)

class ProcessingConfig:
    """Configuration settings for audio processing based on system capabilities"""
    
    def __init__(self, detector: SystemDetector):
        self.detector = detector
        
        # Audio processing parameters
        self.sample_rate = 22050  # Standard for librosa
        self.hop_length = 512
        self.frame_length = 2048
        
        # Analysis parameters based on system
        self.rolling_window_minutes = self._get_window_size()
        self.min_clip_length = 20    # Minimum 20 seconds
        self.max_clip_length = 180   # Maximum 3 minutes
        self.context_buffer = 3      # 3-second buffer
        self.merge_threshold = 30    # Merge clips within 30 seconds
        
        # Processing limits
        self.max_segments_to_process = self._get_max_segments()
        
    def _get_window_size(self) -> int:
        """Get rolling window size based on processing strategy"""
        windows = {
            "high_memory": 20,      # 20 minutes
            "balanced": 15,         # 15 minutes
            "conservative": 10      # 10 minutes
        }
        
        return windows.get(self.detector.processing_strategy, 15)
    
    def _get_max_segments(self) -> int:
        """Get maximum segments to process based on system capabilities"""
        limits = {
            "high_memory": 100,     # Can handle many segments
            "balanced": 50,         # Reasonable limit
            "conservative": 25      # Conservative limit
        }
        
        return limits.get(self.detector.processing_strategy, 50)
    
    def get_excitement_types(self) -> dict:
        """
        Get excitement type configuration
        
        Returns:
            Dictionary of excitement types and their parameters
        """
        return {
            'laughter': {'freq_range': (300, 3000), 'weight': 1.2},
            'shock': {'freq_range': (1000, 8000), 'weight': 1.1},
            'hype': {'freq_range': (100, 1000), 'weight': 1.0},
            'speech': {'freq_range': (85, 255), 'weight': 0.8}
        }
    
    def should_use_detailed_logging(self) -> bool:
        """Determine if detailed logging should be enabled"""
        # Enable detailed logging for development and debugging
        return self.detector.processing_strategy != "conservative"

def get_system_info() -> dict:
    """
    Get comprehensive system information for debugging
    
    Returns:
        System information dictionary
    """
    try:
        detector = SystemDetector()
        config = ProcessingConfig(detector)
        
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        return {
            "ram": {
                "available_gb": detector.available_ram_gb,
                "strategy": detector.processing_strategy,
                "chunk_size_seconds": detector.get_chunk_size(),
                "max_concurrent_jobs": detector.get_max_concurrent_jobs(),
                "memory_limit_mb": detector.get_memory_limit_mb()
            },
            "cpu": {
                "logical_cores": cpu_count,
                "current_freq_mhz": cpu_freq.current if cpu_freq else None,
                "max_freq_mhz": cpu_freq.max if cpu_freq else None
            },
            "processing": {
                "parallel_processing": detector.should_use_parallel_processing(),
                "rolling_window_minutes": config.rolling_window_minutes,
                "max_segments": config.max_segments_to_process,
                "detailed_logging": config.should_use_detailed_logging()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {"error": str(e)} 