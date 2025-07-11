"""
Fine-tuning script for StreamClip AI Video Processor
Test different parameters to optimize for your content type
"""

import sys
import os
from video_processor import VideoProcessor
import time

def test_different_thresholds(video_path):
    """Test the same video with different audio thresholds"""
    
    print(f"🎛️ Fine-tuning Audio Sensitivity for: {os.path.basename(video_path)}")
    print("=" * 60)
    
    # Different sensitivity levels to test
    thresholds = [
        (0.05, "Very Sensitive - Catches quiet moments"),
        (0.1, "Default - Balanced detection"),
        (0.15, "Moderate - Only clear peaks"),
        (0.2, "Conservative - Only loud moments"),
        (0.3, "Very Conservative - Only very loud moments")
    ]
    
    processor = VideoProcessor()
    
    for threshold, description in thresholds:
        print(f"\n🎯 Testing threshold {threshold} - {description}")
        print("-" * 50)
        
        start_time = time.time()
        result = processor.process_video(
            video_path, 
            audio_threshold=threshold,
            max_clips=3  # Limit to 3 clips for testing
        )
        end_time = time.time()
        
        if result.get("success"):
            stats = result.get("stats", {})
            print(f"✅ Success - Processing time: {end_time - start_time:.1f}s")
            print(f"   📊 Audio peaks found: {stats.get('total_peaks_found', 0)}")
            print(f"   🎬 Clips generated: {stats.get('clips_generated', 0)}")
            
            # Show first few timestamps
            timestamps = result.get("timestamps", [])
            if timestamps:
                print(f"   ⏰ First few peaks at: {[f'{t}s' for t in timestamps[:3]]}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    
    print(f"\n🎉 Fine-tuning complete! Check the clips folder to see results.")

def test_clip_durations(video_path):
    """Test different clip lengths"""
    
    print(f"\n🎬 Testing Different Clip Durations")
    print("=" * 40)
    
    durations = [15, 30, 45, 60]  # seconds
    processor = VideoProcessor()
    
    for duration in durations:
        print(f"\n⏱️ Testing {duration}-second clips...")
        result = processor.process_video(
            video_path,
            clip_duration=duration,
            max_clips=2  # Just 2 clips per test
        )
        
        if result.get("success"):
            clips = result.get("clips", [])
            print(f"✅ Generated {len(clips)} clips of {duration} seconds each")
        else:
            print(f"❌ Failed: {result.get('error')}")

def analyze_video_content(video_path):
    """Analyze video to recommend optimal settings"""
    
    print(f"\n🔍 Analyzing Video Content for Optimal Settings")
    print("=" * 50)
    
    processor = VideoProcessor()
    analysis = processor.analyze_video_quality(video_path)
    
    if analysis.get("suitable_for_processing"):
        duration = analysis.get("duration", 0)
        has_audio = analysis.get("has_audio", False)
        
        print(f"📊 Video Analysis:")
        print(f"   Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"   Resolution: {analysis.get('resolution')}")
        print(f"   FPS: {analysis.get('fps')}")
        print(f"   Has Audio: {has_audio}")
        print(f"   File Size: {analysis.get('file_size', 0) / 1024 / 1024:.1f} MB")
        
        # Recommendations based on analysis
        print(f"\n💡 Recommended Settings:")
        
        if duration < 300:  # Less than 5 minutes
            print("   📏 Short video detected")
            print("   🎯 Recommended threshold: 0.05 (very sensitive)")
            print("   ⏰ Recommended clip length: 15-30 seconds")
        elif duration < 1800:  # Less than 30 minutes
            print("   📏 Medium length video detected")
            print("   🎯 Recommended threshold: 0.1 (default)")
            print("   ⏰ Recommended clip length: 30 seconds")
        else:  # Long video
            print("   📏 Long video detected")
            print("   🎯 Recommended threshold: 0.15 (moderate)")
            print("   ⏰ Recommended clip length: 30-45 seconds")
        
        # Content type recommendations
        print(f"\n🎮 Content Type Recommendations:")
        print("   🎵 Music/Gaming: Use threshold 0.1-0.15")
        print("   🎙️ Podcast/Talk: Use threshold 0.05-0.1")
        print("   📺 General Stream: Use threshold 0.1 (default)")
        
        warnings = analysis.get("warnings", [])
        if warnings:
            print(f"\n⚠️ Warnings:")
            for warning in warnings:
                print(f"   - {warning}")
    else:
        print(f"❌ Video analysis failed: {analysis.get('error')}")

def interactive_tuning(video_path):
    """Interactive tuning session"""
    
    print(f"\n🎮 Interactive Fine-Tuning Session")
    print("=" * 40)
    
    processor = VideoProcessor()
    
    while True:
        print(f"\nChoose tuning option:")
        print("1. Test custom audio threshold")
        print("2. Test custom clip duration")
        print("3. Test max clips setting")
        print("4. Run with custom settings")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            try:
                threshold = float(input("Enter audio threshold (0.01-0.5): "))
                if 0.01 <= threshold <= 0.5:
                    result = processor.process_video(video_path, audio_threshold=threshold, max_clips=2)
                    if result.get("success"):
                        stats = result.get("stats", {})
                        print(f"✅ Found {stats.get('total_peaks_found', 0)} peaks, generated {stats.get('clips_generated', 0)} clips")
                    else:
                        print(f"❌ Failed: {result.get('error')}")
                else:
                    print("❌ Threshold must be between 0.01 and 0.5")
            except ValueError:
                print("❌ Please enter a valid number")
        
        elif choice == "2":
            try:
                duration = int(input("Enter clip duration in seconds (10-120): "))
                if 10 <= duration <= 120:
                    result = processor.process_video(video_path, clip_duration=duration, max_clips=2)
                    if result.get("success"):
                        print(f"✅ Generated clips of {duration} seconds each")
                    else:
                        print(f"❌ Failed: {result.get('error')}")
                else:
                    print("❌ Duration must be between 10 and 120 seconds")
            except ValueError:
                print("❌ Please enter a valid number")
        
        elif choice == "3":
            try:
                max_clips = int(input("Enter max clips to generate (1-10): "))
                if 1 <= max_clips <= 10:
                    result = processor.process_video(video_path, max_clips=max_clips)
                    if result.get("success"):
                        print(f"✅ Generated {len(result.get('clips', []))} clips")
                    else:
                        print(f"❌ Failed: {result.get('error')}")
                else:
                    print("❌ Max clips must be between 1 and 10")
            except ValueError:
                print("❌ Please enter a valid number")
        
        elif choice == "4":
            try:
                threshold = float(input("Audio threshold (0.01-0.5): "))
                duration = int(input("Clip duration (10-120): "))
                max_clips = int(input("Max clips (1-10): "))
                
                print(f"\n🚀 Running with custom settings...")
                result = processor.process_video(
                    video_path,
                    audio_threshold=threshold,
                    clip_duration=duration,
                    max_clips=max_clips
                )
                
                if result.get("success"):
                    stats = result.get("stats", {})
                    print(f"✅ Success!")
                    print(f"   📊 Audio peaks found: {stats.get('total_peaks_found', 0)}")
                    print(f"   🎬 Clips generated: {stats.get('clips_generated', 0)}")
                    print(f"   📁 Check the clips folder for results!")
                else:
                    print(f"❌ Failed: {result.get('error')}")
            except ValueError:
                print("❌ Please enter valid numbers")
        
        elif choice == "5":
            print("👋 Exiting fine-tuning session")
            break
        
        else:
            print("❌ Invalid choice, please try again")

def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("❌ Usage: python fine_tune_test.py <video_path> [mode]")
        print("   Modes: thresholds, durations, analyze, interactive")
        print("   Example: python fine_tune_test.py uploads/video.mp4 thresholds")
        return
    
    video_path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "analyze"
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return
    
    print(f"🎯 StreamClip AI Fine-Tuning Tool")
    print(f"📁 Video: {os.path.basename(video_path)}")
    print(f"🔧 Mode: {mode}")
    
    if mode == "thresholds":
        test_different_thresholds(video_path)
    elif mode == "durations":
        test_clip_durations(video_path)
    elif mode == "analyze":
        analyze_video_content(video_path)
    elif mode == "interactive":
        interactive_tuning(video_path)
    elif mode == "all":
        analyze_video_content(video_path)
        test_different_thresholds(video_path)
        test_clip_durations(video_path)
    else:
        print(f"❌ Unknown mode: {mode}")
        print("   Available modes: thresholds, durations, analyze, interactive, all")

if __name__ == "__main__":
    main() 