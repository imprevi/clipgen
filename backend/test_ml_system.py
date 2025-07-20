"""
🧪 ML System Test Suite
====================

Comprehensive testing for the ML-enhanced video processing system.
Tests functionality, performance, and provides processing time estimates.

Usage:
    python test_ml_system.py [video_path]

Author: StreamClip AI Team
"""

import sys
import os
import time
import logging
from typing import Dict, List
import traceback

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_dependencies():
    """Test if all required dependencies are available"""
    missing_deps = []
    
    try:
        import numpy
        logger.info("✅ numpy available")
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import librosa
        logger.info("✅ librosa available")
    except ImportError:
        missing_deps.append("librosa")
    
    try:
        import scipy
        logger.info("✅ scipy available")
    except ImportError:
        missing_deps.append("scipy")
    
    try:
        import sklearn
        logger.info("✅ scikit-learn available")
    except ImportError:
        missing_deps.append("scikit-learn")
    
    try:
        import psutil
        logger.info("✅ psutil available")
    except ImportError:
        missing_deps.append("psutil")
    
    try:
        from moviepy.editor import VideoFileClip
        logger.info("✅ moviepy available")
    except ImportError:
        missing_deps.append("moviepy")
    
    if missing_deps:
        logger.error(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        logger.info("📦 Install with: pip install " + " ".join(missing_deps))
        return False
    
    logger.info("🎉 All dependencies available!")
    return True

def test_ml_analyzer():
    """Test the ML Audio Analyzer"""
    try:
        logger.info("🤖 Testing ML Audio Analyzer...")
        
        # This will test without loading audio
        from ml_audio_analyzer import MLAudioAnalyzer
        analyzer = MLAudioAnalyzer()
        
        logger.info(f"   RAM Strategy: {analyzer.processing_strategy}")
        logger.info(f"   Available RAM: {analyzer.available_ram_gb:.1f}GB")
        logger.info(f"   Rolling window: {analyzer.rolling_window_minutes} minutes")
        
        # Test feature names
        expected_excitement_types = ['laughter', 'shock', 'hype', 'speech']
        detected_types = list(analyzer.excitement_types.keys())
        
        for exc_type in expected_excitement_types:
            if exc_type in detected_types:
                logger.info(f"   ✅ {exc_type} detection available")
            else:
                logger.warning(f"   ⚠️ {exc_type} detection missing")
        
        logger.info("✅ ML Audio Analyzer test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ ML Audio Analyzer test failed: {e}")
        return False

def test_enhanced_processor():
    """Test the Enhanced Video Processor"""
    try:
        logger.info("🚀 Testing Enhanced Video Processor...")
        
        from enhanced_video_processor import EnhancedVideoProcessor
        processor = EnhancedVideoProcessor()
        
        logger.info(f"   Temp dir: {processor.temp_dir}")
        logger.info(f"   Clips dir: {processor.clips_dir}")
        logger.info(f"   Max segments: {processor.max_segments_to_process}")
        
        # Test directory creation
        if os.path.exists(processor.temp_dir):
            logger.info("   ✅ Temp directory exists")
        else:
            logger.warning("   ⚠️ Temp directory not created")
        
        if os.path.exists(processor.clips_dir):
            logger.info("   ✅ Clips directory exists")
        else:
            logger.warning("   ⚠️ Clips directory not created")
        
        logger.info("✅ Enhanced Video Processor test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced Video Processor test failed: {e}")
        return False

def estimate_processing_time(video_path: str) -> Dict:
    """Estimate processing times for a given video"""
    try:
        logger.info(f"⏱️ Estimating processing time for: {video_path}")
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return {}
        
        # Get video info quickly
        from moviepy.editor import VideoFileClip
        video = VideoFileClip(video_path)
        duration_minutes = video.duration / 60
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        has_audio = video.audio is not None
        video.close()
        
        # Estimate based on video characteristics
        estimates = {
            "video_duration_minutes": duration_minutes,
            "file_size_mb": file_size_mb,
            "has_audio": has_audio
        }
        
        if has_audio:
            # Base processing time: ~1 minute per 10 minutes of video for ML analysis
            base_time = duration_minutes * 0.1
            
            # RAM-based multipliers
            from ml_audio_analyzer import MLAudioAnalyzer
            analyzer = MLAudioAnalyzer()
            
            if analyzer.processing_strategy == "high_memory":
                time_multiplier = 0.8  # 20% faster with more RAM
            elif analyzer.processing_strategy == "balanced":
                time_multiplier = 1.0  # Normal speed
            else:
                time_multiplier = 1.3  # 30% slower with limited RAM
            
            # File size impact (larger files take longer to process)
            if file_size_mb > 1000:  # > 1GB
                size_multiplier = 1.2
            elif file_size_mb > 500:  # > 500MB
                size_multiplier = 1.1
            else:
                size_multiplier = 1.0
            
            ml_analysis_time = base_time * time_multiplier * size_multiplier
            clip_generation_time = len(range(min(10, int(duration_minutes / 2)))) * 0.5  # ~30s per clip
            
            estimates.update({
                "estimated_ml_analysis_minutes": ml_analysis_time,
                "estimated_clip_generation_minutes": clip_generation_time,
                "estimated_total_minutes": ml_analysis_time + clip_generation_time,
                "processing_strategy": analyzer.processing_strategy,
                "ram_available_gb": analyzer.available_ram_gb
            })
            
            logger.info(f"📊 Processing estimates:")
            logger.info(f"   Video: {duration_minutes:.1f} min, {file_size_mb:.1f}MB")
            logger.info(f"   ML Analysis: ~{ml_analysis_time:.1f} minutes")
            logger.info(f"   Clip Generation: ~{clip_generation_time:.1f} minutes")
            logger.info(f"   Total Time: ~{ml_analysis_time + clip_generation_time:.1f} minutes")
            logger.info(f"   Strategy: {analyzer.processing_strategy} ({analyzer.available_ram_gb:.1f}GB RAM)")
            
        else:
            estimates.update({
                "error": "No audio track - ML analysis not possible",
                "estimated_total_minutes": 0
            })
            logger.warning("⚠️ No audio track detected - ML features unavailable")
        
        return estimates
        
    except Exception as e:
        logger.error(f"Error estimating processing time: {e}")
        return {"error": str(e)}

def test_with_video(video_path: str) -> bool:
    """Test the ML system with an actual video file"""
    try:
        logger.info(f"🎬 Testing with video: {video_path}")
        
        # First, get processing time estimates
        estimates = estimate_processing_time(video_path)
        if "error" in estimates:
            logger.error(f"Cannot test video: {estimates['error']}")
            return False
        
        # Warn user about processing time
        total_time = estimates.get("estimated_total_minutes", 0)
        if total_time > 5:
            logger.warning(f"⚠️ Processing will take approximately {total_time:.1f} minutes")
            logger.warning("⚠️ You can cancel this test if it's taking too long")
        
        # Initialize enhanced processor
        from enhanced_video_processor import EnhancedVideoProcessor
        processor = EnhancedVideoProcessor()
        
        # Test video quality analysis (fast)
        logger.info("📊 Analyzing video quality...")
        quality_analysis = processor.analyze_video_quality(video_path)
        
        if not quality_analysis["suitable_for_processing"]:
            logger.error(f"Video not suitable: {quality_analysis}")
            return False
        
        logger.info("✅ Video quality analysis passed")
        
        # Test ML analysis (time-consuming)
        logger.info("🤖 Running ML analysis (this may take several minutes)...")
        start_time = time.time()
        
        # Run just the ML analysis part
        ml_results = processor.ml_analyzer.analyze_audio_advanced(video_path)
        
        analysis_time = time.time() - start_time
        
        if ml_results["success"]:
            segments_detected = ml_results["segments_detected"]
            logger.info(f"✅ ML analysis completed in {analysis_time:.1f} seconds")
            logger.info(f"   Segments detected: {segments_detected}")
            logger.info(f"   Processing strategy: {ml_results['processing_strategy']}")
            
            # Show top segments
            if ml_results["segments"]:
                logger.info("🎯 Top segments detected:")
                for i, segment in enumerate(ml_results["segments"][:3]):
                    logger.info(f"   #{i+1}: {segment['excitement_type']} | "
                              f"{segment['duration']:.1f}s | "
                              f"Score: {segment['total_excitement_score']:.2f} | "
                              f"Social: {segment['social_media_potential']:.2f}")
            
            return True
        else:
            logger.error(f"ML analysis failed: {ml_results.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        logger.error(f"Video test failed: {e}")
        traceback.print_exc()
        return False

def run_comprehensive_test(video_path: str = None):
    """Run all tests"""
    logger.info("🧪 Starting ML System Comprehensive Test")
    logger.info("=" * 50)
    
    # Test 1: Dependencies
    logger.info("📦 Test 1: Checking dependencies...")
    if not test_dependencies():
        logger.error("❌ Dependency test failed - cannot continue")
        return False
    
    # Test 2: ML Analyzer
    logger.info("\n🤖 Test 2: ML Audio Analyzer...")
    if not test_ml_analyzer():
        logger.error("❌ ML Analyzer test failed")
        return False
    
    # Test 3: Enhanced Processor
    logger.info("\n🚀 Test 3: Enhanced Video Processor...")
    if not test_enhanced_processor():
        logger.error("❌ Enhanced Processor test failed")
        return False
    
    # Test 4: Video Processing (if video provided)
    if video_path:
        logger.info(f"\n🎬 Test 4: Video Processing with {video_path}...")
        if not test_with_video(video_path):
            logger.error("❌ Video processing test failed")
            return False
    else:
        logger.info("\n⏭️ Test 4: Skipped (no video provided)")
        logger.info("   To test with video: python test_ml_system.py your_video.mp4")
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("🎉 All tests passed! ML system is ready for use.")
    
    if video_path:
        logger.info("\n📈 Performance Summary:")
        estimates = estimate_processing_time(video_path)
        if estimates and "estimated_total_minutes" in estimates:
            logger.info(f"   Processing time estimate: ~{estimates['estimated_total_minutes']:.1f} minutes")
            logger.info(f"   RAM strategy: {estimates.get('processing_strategy', 'unknown')}")
    
    logger.info("\n🔄 Next steps:")
    logger.info("   1. Rebuild Docker containers to install new dependencies")
    logger.info("   2. Test through the web interface")
    logger.info("   3. Compare results with legacy processing")
    
    return True

if __name__ == "__main__":
    # Get video path from command line
    video_path = None
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        if not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            sys.exit(1)
    
    # Run tests
    success = run_comprehensive_test(video_path)
    
    if success:
        print("\n✅ Test suite completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Test suite failed!")
        sys.exit(1) 