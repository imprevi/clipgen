#!/usr/bin/env python3
"""
Day 3 Integration Test Script
Tests the complete StreamClip AI API workflow: upload -> process -> download

Run this script to verify Day 3 implementation is working correctly.
Make sure the FastAPI server is running on localhost:8000
"""

import requests
import time
import os
import sys
from pathlib import Path

# API configuration
BASE_URL = "http://localhost:8000"
TEST_VIDEO_PATH = None  # Will be set by user input

def print_header(title):
    """Print a styled header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_step(step, description):
    """Print a test step"""
    print(f"\n{step}️⃣ {description}")
    print("-" * 40)

def test_health_check():
    """Test the health check endpoint"""
    print_step("1", "Testing Health Check Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed!")
            print(f"   Status: {data.get('status')}")
            print(f"   Processor: {data.get('processor')}")
            print(f"   Storage: {data.get('storage')}")
            print(f"   Active jobs: {data.get('active_jobs')}")
            print(f"   Total jobs: {data.get('total_jobs')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server!")
        print("   Make sure FastAPI server is running on localhost:8000")
        print("   Run: python main.py")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_api_docs():
    """Test that API documentation is accessible"""
    print_step("2", "Testing API Documentation")
    
    try:
        response = requests.get(f"{BASE_URL}/docs")
        
        if response.status_code == 200:
            print("✅ API documentation accessible at /docs")
            print("   Visit http://localhost:8000/docs to see interactive docs")
            return True
        else:
            print(f"❌ API docs failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API docs error: {e}")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    print_step("3", "Testing Root Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Root endpoint working!")
            print(f"   Message: {data.get('message')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Status: {data.get('status')}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False

def test_upload_video(video_path):
    """Test video upload endpoint"""
    print_step("4", f"Testing Video Upload: {os.path.basename(video_path)}")
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return None
    
    file_size = os.path.getsize(video_path) / 1024 / 1024
    print(f"📁 File: {os.path.basename(video_path)} ({file_size:.2f} MB)")
    
    try:
        with open(video_path, 'rb') as f:
            files = {'file': (os.path.basename(video_path), f, 'video/mp4')}
            data = {
                'audio_threshold': 0.1,  # Default sensitivity
                'clip_duration': 30,     # 30-second clips
                'max_clips': 3          # Generate up to 3 clips for testing
            }
            
            print("🚀 Uploading video...")
            response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print("✅ Upload successful!")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {result.get('status')}")
            return job_id
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def test_job_status(job_id):
    """Test job status monitoring"""
    print_step("5", f"Monitoring Job Progress: {job_id}")
    
    max_wait_time = 300  # 5 minutes max
    start_time = time.time()
    
    while True:
        try:
            response = requests.get(f"{BASE_URL}/jobs/{job_id}")
            
            if response.status_code == 200:
                job = response.json()
                status = job.get('status')
                progress = job.get('progress', 0)
                
                print(f"📊 Status: {status} | Progress: {progress}%")
                
                if status == 'completed':
                    print("✅ Processing completed!")
                    clips = job.get('clips', [])
                    timestamps = job.get('timestamps', [])
                    
                    print(f"   📈 Results:")
                    print(f"   - Clips generated: {len(clips)}")
                    print(f"   - Timestamps: {timestamps}")
                    
                    analysis = job.get('analysis', {})
                    if analysis:
                        print(f"   - Video duration: {analysis.get('duration', 'N/A'):.1f}s")
                        print(f"   - Resolution: {analysis.get('resolution', 'N/A')}")
                        print(f"   - Has audio: {analysis.get('has_audio', 'N/A')}")
                    
                    stats = job.get('stats', {})
                    if stats:
                        print(f"   - Audio peaks found: {stats.get('total_peaks_found', 'N/A')}")
                    
                    return clips
                    
                elif status == 'failed':
                    print("❌ Processing failed!")
                    error = job.get('error')
                    print(f"   Error: {error}")
                    return None
                    
                elif status in ['queued', 'processing']:
                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed > max_wait_time:
                        print(f"⏰ Timeout after {max_wait_time}s")
                        return None
                    
                    # Wait before next check
                    time.sleep(5)
                    continue
                    
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return None

def test_download_clips(clips):
    """Test downloading generated clips"""
    print_step("6", f"Testing Clip Downloads ({len(clips)} clips)")
    
    downloaded_clips = []
    
    for i, clip_filename in enumerate(clips):
        try:
            print(f"📥 Downloading clip {i+1}: {clip_filename}")
            
            response = requests.get(f"{BASE_URL}/download/{clip_filename}")
            
            if response.status_code == 200:
                # Save to local file for verification
                local_filename = f"downloaded_{clip_filename}"
                with open(local_filename, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content) / 1024 / 1024
                print(f"✅ Downloaded: {local_filename} ({file_size:.2f} MB)")
                downloaded_clips.append(local_filename)
                
            else:
                print(f"❌ Download failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Download error: {e}")
    
    return downloaded_clips

def test_list_jobs():
    """Test job listing endpoint"""
    print_step("7", "Testing Job Listing")
    
    try:
        response = requests.get(f"{BASE_URL}/jobs?limit=10")
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('jobs', [])
            total = data.get('total', 0)
            
            print(f"✅ Job listing successful!")
            print(f"   Total jobs: {total}")
            
            for job in jobs[:3]:  # Show first 3 jobs
                print(f"   📋 {job.get('filename')} - {job.get('status')} ({job.get('clips_count', 0)} clips)")
                
            return True
        else:
            print(f"❌ Job listing failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Job listing error: {e}")
        return False

def test_stats():
    """Test system stats endpoint"""
    print_step("8", "Testing System Statistics")
    
    try:
        response = requests.get(f"{BASE_URL}/stats")
        
        if response.status_code == 200:
            stats = response.json()
            print("✅ Stats retrieved successfully!")
            print(f"   Total jobs: {stats.get('total_jobs')}")
            print(f"   Total clips generated: {stats.get('total_clips_generated')}")
            print(f"   Average clips per job: {stats.get('average_clips_per_job', 0):.1f}")
            print(f"   System status: {stats.get('system_status')}")
            
            status_breakdown = stats.get('status_breakdown', {})
            if status_breakdown:
                print(f"   Status breakdown: {status_breakdown}")
                
            return True
        else:
            print(f"❌ Stats failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return False

def cleanup_test_files(downloaded_clips):
    """Clean up downloaded test files"""
    print_step("9", "Cleaning Up Test Files")
    
    for clip_file in downloaded_clips:
        try:
            if os.path.exists(clip_file):
                os.remove(clip_file)
                print(f"🗑️ Removed: {clip_file}")
        except Exception as e:
            print(f"⚠️ Could not remove {clip_file}: {e}")

def main():
    """Main test function"""
    global TEST_VIDEO_PATH
    
    print_header("StreamClip AI Day 3 Integration Test")
    print("🎯 Testing complete upload-to-download workflow")
    
    # Get video file path from user
    if len(sys.argv) > 1:
        TEST_VIDEO_PATH = sys.argv[1]
    else:
        print("\n📁 Please provide a test video file:")
        print("   Usage: python test_day3_api.py path/to/video.mp4")
        print("   Or place a video in uploads/ folder and enter the filename:")
        
        filename = input("   Video filename (or full path): ").strip()
        
        if filename:
            # Try uploads folder first
            uploads_path = os.path.join("uploads", filename)
            if os.path.exists(uploads_path):
                TEST_VIDEO_PATH = uploads_path
            elif os.path.exists(filename):
                TEST_VIDEO_PATH = filename
            else:
                print(f"❌ Video file not found: {filename}")
                return
    
    if not TEST_VIDEO_PATH or not os.path.exists(TEST_VIDEO_PATH):
        print("❌ No valid video file provided")
        return
    
    print(f"🎬 Using video: {TEST_VIDEO_PATH}")
    
    # Run tests
    test_results = []
    
    # Basic API tests
    test_results.append(test_health_check())
    test_results.append(test_api_docs())
    test_results.append(test_root_endpoint())
    
    # Core workflow tests
    job_id = test_upload_video(TEST_VIDEO_PATH)
    if job_id:
        clips = test_job_status(job_id)
        if clips:
            downloaded_clips = test_download_clips(clips)
            test_results.append(len(downloaded_clips) > 0)
            
            # Cleanup
            cleanup_test_files(downloaded_clips)
        else:
            test_results.append(False)
    else:
        test_results.append(False)
        test_results.append(False)
    
    # Additional API tests
    test_results.append(test_list_jobs())
    test_results.append(test_stats())
    
    # Summary
    print_header("Test Results Summary")
    
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Day 3 Integration Complete!")
        print("✅ Your StreamClip AI API is fully functional:")
        print("   • File upload working")
        print("   • Background processing working") 
        print("   • Progress tracking working")
        print("   • Clip download working")
        print("   • All API endpoints working")
        print("\n🚀 Ready for Day 4: Frontend Integration!")
        
    else:
        print(f"⚠️ {passed}/{total} tests passed")
        print("   Some features may need attention before proceeding")
    
    print(f"\n📊 Test Score: {passed}/{total}")

if __name__ == "__main__":
    main() 