"""
Test script for the VideoProcessor class
Run this to verify the video processing functionality is working correctly
"""

import sys
import os
from video_processor import VideoProcessor
import time

def test_video_processor():
    """Test the video processor with various scenarios"""
    
    print("🧪 Testing StreamClip AI Video Processor")
    print("=" * 50)
    
    # Initialize the processor
    processor = VideoProcessor()
    
    # Test 1: Check if directories are created
    print("\n1️⃣ Testing directory creation...")
    if os.path.exists(processor.temp_dir) and os.path.exists(processor.clips_dir):
        print("✅ Directories created successfully")
    else:
        print("❌ Failed to create directories")
        return False
    
    # Test 2: Test with non-existent file
    print("\n2️⃣ Testing error handling...")
    result = processor.process_video("nonexistent_video.mp4")
    if "error" in result:
        print("✅ Error handling works correctly")
        print(f"   Error message: {result['error']}")
    else:
        print("❌ Error handling failed")
        return False
    
    # Test 3: Test cleanup function
    print("\n3️⃣ Testing cleanup function...")
    try:
        processor.cleanup_temp_files()
        print("✅ Cleanup function works")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False
    
    print("\n🎉 All basic tests passed!")
    
    # Test 4: Instructions for testing with real video
    print("\n4️⃣ Testing with real video (manual step):")
    print("   To test with a real video file:")
    print("   1. Download a sample video (MP4 format)")
    print("   2. Place it in the 'uploads' folder")
    print("   3. Run: python test_processor.py path/to/your/video.mp4")
    print("   4. The processor will generate clips in the 'clips' folder")
    
    return True

def test_with_video_file(video_path):
    """Test the processor with an actual video file"""
    
    print(f"\n🎬 Testing with video file: {video_path}")
    print("=" * 50)
    
    processor = VideoProcessor()
    
    # Record start time
    start_time = time.time()
    
    # Process the video
    result = processor.process_video(video_path)
    
    # Record end time
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"\n⏱️  Processing time: {processing_time:.2f} seconds")
    
    # Check results
    if result.get("success"):
        print("✅ Video processing successful!")
        print(f"📊 Analysis:")
        analysis = result.get("analysis", {})
        print(f"   - Duration: {analysis.get('duration', 'N/A'):.2f} seconds")
        print(f"   - Resolution: {analysis.get('resolution', 'N/A')}")
        print(f"   - FPS: {analysis.get('fps', 'N/A')}")
        print(f"   - Has audio: {analysis.get('has_audio', 'N/A')}")
        print(f"   - File size: {analysis.get('file_size', 0) / 1024 / 1024:.2f} MB")
        
        stats = result.get("stats", {})
        print(f"\n📈 Processing stats:")
        print(f"   - Audio peaks found: {stats.get('total_peaks_found', 0)}")
        print(f"   - Clips generated: {stats.get('clips_generated', 0)}")
        
        clips = result.get("clips", [])
        if clips:
            print(f"\n🎥 Generated clips:")
            for i, clip_path in enumerate(clips):
                filename = os.path.basename(clip_path)
                if os.path.exists(clip_path):
                    size = os.path.getsize(clip_path) / 1024 / 1024
                    print(f"   {i+1}. {filename} ({size:.2f} MB)")
                else:
                    print(f"   {i+1}. {filename} (file not found)")
        
        warnings = analysis.get("warnings", [])
        if warnings:
            print(f"\n⚠️  Warnings:")
            for warning in warnings:
                print(f"   - {warning}")
        
        return True
    else:
        print("❌ Video processing failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        
        if "suggestion" in result:
            print(f"   Suggestion: {result['suggestion']}")
        
        return False

def main():
    """Main function to run tests"""
    
    # Check if a video file path was provided
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        
        if not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            return
        
        # Test with the provided video file
        success = test_with_video_file(video_path)
        
        if success:
            print("\n🎉 Video processing test completed successfully!")
        else:
            print("\n💥 Video processing test failed!")
    else:
        # Run basic tests
        success = test_video_processor()
        
        if success:
            print("\n🎉 All tests passed! Video processor is ready!")
        else:
            print("\n💥 Some tests failed!")

if __name__ == "__main__":
    main() 