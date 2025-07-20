"""
⚡ Performance Optimizer for StreamClip AI
=========================================

High-performance optimizations including caching, parallel processing,
memory management, and performance monitoring.

Author: StreamClip AI Team
"""

import time
import functools
import hashlib
import pickle
import os
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict, Any, Optional, Callable, List
import logging
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PerformanceCache:
    """High-performance caching system for expensive computations"""
    
    def __init__(self, max_size: int = 100, ttl_hours: int = 24):
        self.max_size = max_size
        self.ttl_hours = ttl_hours
        self.cache: Dict[str, Dict] = {}
        self.access_times: Dict[str, datetime] = {}
        self.lock = threading.RLock()
        
        # Create cache directory
        self.cache_dir = "cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        logger.info(f"⚡ Performance Cache initialized: {max_size} items, {ttl_hours}h TTL")
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments"""
        key_data = f"{func_name}_{str(args)}_{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_expired(self, timestamp: datetime) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() - timestamp > timedelta(hours=self.ttl_hours)
    
    def _cleanup_expired(self):
        """Remove expired cache entries"""
        with self.lock:
            expired_keys = [
                key for key, timestamp in self.access_times.items()
                if self._is_expired(timestamp)
            ]
            
            for key in expired_keys:
                self.cache.pop(key, None)
                self.access_times.pop(key, None)
                
                # Remove disk cache file
                cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _evict_lru(self):
        """Evict least recently used items if cache is full"""
        with self.lock:
            if len(self.cache) >= self.max_size:
                # Find least recently used item
                lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
                
                self.cache.pop(lru_key, None)
                self.access_times.pop(lru_key, None)
                
                # Remove disk cache file
                cache_file = os.path.join(self.cache_dir, f"{lru_key}.pkl")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                
                logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self.lock:
            self._cleanup_expired()
            
            if key in self.cache:
                # Update access time
                self.access_times[key] = datetime.now()
                return self.cache[key]
            
            # Try to load from disk
            cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                    
                    # Check if disk cache is expired
                    file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
                    if not self._is_expired(file_time):
                        self.cache[key] = data
                        self.access_times[key] = datetime.now()
                        return data
                    else:
                        os.remove(cache_file)
                        
                except Exception as e:
                    logger.warning(f"Failed to load disk cache {key}: {e}")
            
            return None
    
    def set(self, key: str, value: Any, persist: bool = True):
        """Set item in cache"""
        with self.lock:
            self._evict_lru()
            
            self.cache[key] = value
            self.access_times[key] = datetime.now()
            
            # Persist to disk for large computations
            if persist:
                try:
                    cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
                    with open(cache_file, 'wb') as f:
                        pickle.dump(value, f)
                except Exception as e:
                    logger.warning(f"Failed to persist cache {key}: {e}")
    
    def cached_call(self, func: Callable, *args, persist: bool = True, **kwargs) -> Any:
        """Execute function with caching"""
        key = self._generate_key(func.__name__, args, kwargs)
        
        # Try to get from cache
        result = self.get(key)
        if result is not None:
            logger.debug(f"Cache hit for {func.__name__}")
            return result
        
        # Execute function and cache result
        logger.debug(f"Cache miss for {func.__name__}, executing...")
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        self.set(key, result, persist)
        logger.debug(f"Cached {func.__name__} result (executed in {execution_time:.2f}s)")
        
        return result

class ParallelProcessor:
    """Parallel processing manager for CPU-intensive tasks"""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.cpu_count = psutil.cpu_count()
        self.max_workers = max_workers if max_workers is not None else min(self.cpu_count or 4, 8)  # Cap at 8 to avoid resource exhaustion
        
        # Thread pool for I/O bound tasks
        self.thread_executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Process pool for CPU bound tasks (created on demand)
        self._process_executor = None
        
        logger.info(f"⚡ Parallel Processor initialized: {self.max_workers} workers")
    
    @property
    def process_executor(self):
        """Lazy-load process executor to avoid resource usage when not needed"""
        if self._process_executor is None:
            self._process_executor = ProcessPoolExecutor(max_workers=self.max_workers)
        return self._process_executor
    
    def parallel_map(self, func: Callable, items: List[Any], cpu_bound: bool = True) -> List[Any]:
        """Execute function in parallel across items"""
        if len(items) <= 1:
            return [func(item) for item in items]
        
        executor = self.process_executor if cpu_bound else self.thread_executor
        
        try:
            start_time = time.time()
            results = list(executor.map(func, items))
            execution_time = time.time() - start_time
            
            logger.info(f"Parallel execution completed: {len(items)} items in {execution_time:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Parallel execution failed: {e}")
            # Fallback to sequential processing
            return [func(item) for item in items]
    
    def cleanup(self):
        """Clean up executors"""
        if self.thread_executor:
            self.thread_executor.shutdown(wait=True)
        if self._process_executor:
            self._process_executor.shutdown(wait=True)

class MemoryManager:
    """Optimized memory management for large video processing"""
    
    def __init__(self):
        self.memory_threshold = 0.85  # Use up to 85% of available memory
        self.chunk_sizes = self._calculate_optimal_chunks()
        
        logger.info(f"⚡ Memory Manager initialized")
        logger.info(f"   Memory threshold: {self.memory_threshold*100}%")
        logger.info(f"   Chunk sizes: {self.chunk_sizes}")
    
    def _calculate_optimal_chunks(self) -> Dict[str, int]:
        """Calculate optimal chunk sizes based on available memory"""
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        
        # Calculate chunk sizes for different operations
        base_chunk = int(available_gb * 60)  # 60 seconds per GB of RAM
        
        return {
            "audio_analysis": max(30, min(base_chunk, 300)),     # 30s-5min chunks
            "video_processing": max(10, min(base_chunk//2, 120)), # 10s-2min chunks
            "feature_extraction": max(60, min(base_chunk*2, 600)) # 1min-10min chunks
        }
    
    def get_chunk_size(self, operation: str, duration: float) -> int:
        """Get optimal chunk size for operation"""
        base_size = self.chunk_sizes.get(operation, 60)
        
        # Adjust based on total duration
        if duration > 3600:  # > 1 hour
            return max(base_size, 120)  # Larger chunks for long videos
        elif duration < 300:  # < 5 minutes
            return min(base_size, 30)   # Smaller chunks for short videos
        
        return base_size
    
    def monitor_memory_usage(self) -> Dict[str, float]:
        """Monitor current memory usage"""
        memory = psutil.virtual_memory()
        
        return {
            "used_percent": memory.percent,
            "available_gb": memory.available / (1024**3),
            "used_gb": memory.used / (1024**3),
            "total_gb": memory.total / (1024**3),
            "threshold_exceeded": memory.percent > (self.memory_threshold * 100)
        }
    
    def optimize_numpy_arrays(self, arrays: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Optimize numpy arrays for memory efficiency"""
        optimized = {}
        
        for name, array in arrays.items():
            if array.dtype == np.float64:
                # Convert to float32 for memory savings (50% reduction)
                optimized[name] = array.astype(np.float32)
            elif array.dtype == np.int64:
                # Convert to int32 if values fit
                if np.all(array <= np.iinfo(np.int32).max) and np.all(array >= np.iinfo(np.int32).min):
                    optimized[name] = array.astype(np.int32)
                else:
                    optimized[name] = array
            else:
                optimized[name] = array
        
        return optimized

class PerformanceMonitor:
    """Real-time performance monitoring and metrics"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            "function_calls": {},
            "execution_times": {},
            "memory_peaks": [],
            "cache_stats": {"hits": 0, "misses": 0},
            "parallel_jobs": 0
        }
        self.lock = threading.Lock()
        
        logger.info("⚡ Performance Monitor initialized")
    
    def time_function(self, func: Callable) -> Callable:
        """Decorator to time function execution"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                self.record_execution(func.__name__, execution_time)
        
        return wrapper
    
    def record_execution(self, func_name: str, execution_time: float):
        """Record function execution time"""
        with self.lock:
            if func_name not in self.metrics["function_calls"]:
                self.metrics["function_calls"][func_name] = 0
                self.metrics["execution_times"][func_name] = []
            
            self.metrics["function_calls"][func_name] += 1
            self.metrics["execution_times"][func_name].append(execution_time)
            
            # Keep only last 100 execution times per function
            if len(self.metrics["execution_times"][func_name]) > 100:
                self.metrics["execution_times"][func_name] = self.metrics["execution_times"][func_name][-100:]
    
    def record_memory_peak(self):
        """Record current memory usage peak"""
        memory = psutil.virtual_memory()
        with self.lock:
            self.metrics["memory_peaks"].append({
                "timestamp": time.time(),
                "used_percent": memory.percent,
                "used_gb": memory.used / (1024**3)
            })
            
            # Keep only last 1000 memory measurements
            if len(self.metrics["memory_peaks"]) > 1000:
                self.metrics["memory_peaks"] = self.metrics["memory_peaks"][-1000:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        with self.lock:
            uptime = time.time() - self.start_time
            
            # Calculate averages and totals
            function_stats = {}
            for func_name, times in self.metrics["execution_times"].items():
                if times:
                    function_stats[func_name] = {
                        "calls": self.metrics["function_calls"][func_name],
                        "avg_time": np.mean(times),
                        "total_time": np.sum(times),
                        "min_time": np.min(times),
                        "max_time": np.max(times)
                    }
            
            # Memory statistics
            memory_stats = {}
            if self.metrics["memory_peaks"]:
                memory_usage = [m["used_percent"] for m in self.metrics["memory_peaks"]]
                memory_stats = {
                    "avg_usage_percent": np.mean(memory_usage),
                    "peak_usage_percent": np.max(memory_usage),
                    "current_usage": psutil.virtual_memory().percent
                }
            
            return {
                "uptime_seconds": uptime,
                "function_stats": function_stats,
                "memory_stats": memory_stats,
                "cache_stats": self.metrics["cache_stats"].copy(),
                "parallel_jobs": self.metrics["parallel_jobs"]
            }

# Global performance optimization instances
performance_cache = PerformanceCache()
parallel_processor = ParallelProcessor()
memory_manager = MemoryManager()
performance_monitor = PerformanceMonitor()

def cached(persist: bool = True):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return performance_cache.cached_call(func, *args, persist=persist, **kwargs)
        return wrapper
    return decorator

def timed(func: Callable) -> Callable:
    """Decorator for timing function execution"""
    return performance_monitor.time_function(func)

def parallel_chunks(chunk_operation: str):
    """Decorator for parallel chunk processing"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(data, *args, **kwargs):
            # Determine if we should use chunking
            if hasattr(data, '__len__') and len(data) > 1000:  # Large datasets
                chunk_size = memory_manager.get_chunk_size(chunk_operation, len(data))
                
                # Split data into chunks
                chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
                
                # Process chunks in parallel
                def process_chunk(chunk):
                    return func(chunk, *args, **kwargs)
                
                results = parallel_processor.parallel_map(process_chunk, chunks)
                
                # Combine results (assumes concatenatable results)
                if results and hasattr(results[0], '__iter__'):
                    return np.concatenate(results)
                else:
                    return results
            else:
                # Process normally for small datasets
                return func(data, *args, **kwargs)
        
        return wrapper
    return decorator

def cleanup_performance_resources():
    """Clean up all performance optimization resources"""
    try:
        parallel_processor.cleanup()
        logger.info("⚡ Performance optimization resources cleaned up")
    except Exception as e:
        logger.warning(f"Error cleaning up performance resources: {e}")

# Performance optimization utilities
def optimize_video_processing_pipeline():
    """Optimize the entire video processing pipeline"""
    logger.info("⚡ Optimizing video processing pipeline...")
    
    # Set optimal numpy threading
    try:
        import os
        # Use all available cores for numpy operations
        os.environ["OMP_NUM_THREADS"] = str(psutil.cpu_count())
        os.environ["MKL_NUM_THREADS"] = str(psutil.cpu_count())
        logger.info(f"Set numpy threading to {psutil.cpu_count()} cores")
    except Exception as e:
        logger.warning(f"Could not optimize numpy threading: {e}")
    
    # Record initial memory state
    performance_monitor.record_memory_peak()
    
    logger.info("⚡ Video processing pipeline optimization complete") 