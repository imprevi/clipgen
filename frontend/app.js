// StreamClip AI Frontend - Day 4 Complete Integration
// Connects to the FastAPI backend for real video processing

// Configuration
const API_BASE_URL = '/api';
const POLL_INTERVAL = 2000; // Poll every 2 seconds for progress

// Global state
let currentJobId = null;
let statusInterval = null;
let isProcessing = false;

// DOM elements
const fileInput = document.getElementById('fileInput');
const uploadButton = document.querySelector('.upload-btn');
const statusDiv = document.getElementById('status');
const resultsDiv = document.getElementById('results');

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('StreamClip AI frontend loaded successfully!');
    testConnection();
    setupEventListeners();
});

// Test backend connection
async function testConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            const data = await response.json();
            showStatus('✅ Connected to StreamClip AI backend!', 'success');
            console.log('Backend health:', data);
        } else {
            showStatus('⚠️ Backend not responding. Make sure the server is running.', 'error');
        }
    } catch (error) {
        showStatus('❌ Cannot connect to backend. Please start the server with: python backend/main.py', 'error');
        console.error('Connection error:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Upload button click
    uploadButton.addEventListener('click', startProcessing);
    
    // Source selection radio buttons
    const sourceRadios = document.querySelectorAll('input[name="source"]');
    sourceRadios.forEach(radio => {
        radio.addEventListener('change', handleSourceChange);
    });
    
    // Drag and drop support
    const uploadArea = document.getElementById('uploadArea');
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('drop', handleDrop);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('click', () => fileInput.click());
}

// Handle file selection
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        validateFile(file);
    }
}

// Validate selected file
function validateFile(file) {
    const allowedTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/mkv', 'video/webm', 'video/x-flv'];
    const maxSize = 5 * 1024 * 1024 * 1024; // 5GB
    
    if (!allowedTypes.includes(file.type)) {
        showStatus('❌ Invalid file type. Please select MP4, AVI, MOV, MKV, WebM, or FLV files.', 'error');
        return false;
    }
    
    if (file.size > maxSize) {
        showStatus('❌ File too large. Maximum size is 5GB.', 'error');
        return false;
    }
    
    const fileSizeMB = (file.size / 1024 / 1024).toFixed(2);
    showStatus(`✅ File selected: ${file.name} (${fileSizeMB} MB)`, 'success');
    return true;
}

// Handle drag over
function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
}

// Handle drag leave
function handleDragLeave(event) {
    event.currentTarget.classList.remove('drag-over');
}

// Handle file drop
function handleDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files;
        validateFile(files[0]);
    }
}

// Handle source selection change
function handleSourceChange(event) {
    const selectedSource = event.target.value;
    const uploadArea = document.getElementById('uploadArea');
    const twitchArea = document.getElementById('twitchArea');
    
    if (selectedSource === 'upload') {
        uploadArea.style.display = 'block';
        twitchArea.style.display = 'none';
    } else {
        uploadArea.style.display = 'none';
        twitchArea.style.display = 'block';
    }
}

// Validate Twitch URL
function validateTwitchUrl(url) {
    if (!url || url.trim() === '') {
        showStatus('❌ Please enter a Twitch VOD URL.', 'error');
        return false;
    }
    
    if (!url.includes('twitch.tv') || !url.includes('videos/')) {
        showStatus('❌ Invalid Twitch URL format. Please use a URL like: https://www.twitch.tv/videos/123456789', 'error');
        return false;
    }
    
    showStatus('✅ Valid Twitch URL detected.', 'success');
    return true;
}

// Start processing (either file upload or Twitch VOD)
async function startProcessing() {
    const selectedSource = document.querySelector('input[name="source"]:checked').value;
    
    if (selectedSource === 'upload') {
        await uploadFile();
    } else {
        await processTwitchVod();
    }
}

// Process Twitch VOD
async function processTwitchVod() {
    const twitchUrl = document.getElementById('twitchUrlInput').value.trim();
    
    if (!validateTwitchUrl(twitchUrl)) {
        return;
    }
    
    if (isProcessing) {
        showStatus('⏳ Processing already in progress...', 'info');
        return;
    }
    
    isProcessing = true;
    updateUploadUI(true);
    
    try {
        showStatus('🎮 Starting Twitch VOD processing...', 'info');
        showProgress(0);
        
        // Get processing options from form
        const sensitivity = document.getElementById('sensitivity').value;
        const duration = document.getElementById('duration').value;
        const maxClips = document.getElementById('maxClips').value;
        
        const requestData = {
            twitch_url: twitchUrl,
            audio_threshold: parseFloat(sensitivity),
            clip_duration: parseInt(duration),
            max_clips: parseInt(maxClips)
        };
        
        const response = await fetch(`${API_BASE_URL}/process-twitch-vod`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (response.ok) {
            const data = await response.json();
            currentJobId = data.job_id;
            
            showStatus('✅ Twitch VOD processing started!', 'success');
            console.log('Twitch VOD processing started:', data);
            
            // Start monitoring progress
            startProgressMonitoring();
            
        } else {
            const errorData = await response.json();
            showStatus(`❌ Processing failed: ${errorData.detail || 'Unknown error'}`, 'error');
            console.error('Twitch VOD processing error:', errorData);
        }
        
    } catch (error) {
        showStatus('❌ Processing error: ' + error.message, 'error');
        console.error('Twitch VOD processing error:', error);
    } finally {
        if (!currentJobId) {
            isProcessing = false;
            updateUploadUI(false);
        }
    }
}

// Upload file and start processing
async function uploadFile() {
    const file = fileInput.files[0];
    
    if (!file) {
        showStatus('❌ Please select a video file first.', 'error');
        return;
    }
    
    if (!validateFile(file)) {
        return;
    }
    
    if (isProcessing) {
        showStatus('⏳ Upload already in progress...', 'info');
        return;
    }
    
    isProcessing = true;
    updateUploadUI(true);
    
    try {
        showStatus('📤 Uploading video file...', 'info');
        showProgress(0);
        
        // Get processing options from form
        const sensitivity = document.getElementById('sensitivity').value;
        const duration = document.getElementById('duration').value;
        const maxClips = document.getElementById('maxClips').value;
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('audio_threshold', sensitivity);
        formData.append('clip_duration', duration);
        formData.append('max_clips', maxClips);
        
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            currentJobId = data.job_id;
            
            showStatus('✅ Upload successful! Processing started...', 'success');
            console.log('Upload successful:', data);
            
            // Start monitoring progress
            startProgressMonitoring();
            
        } else {
            const errorData = await response.json();
            showStatus(`❌ Upload failed: ${errorData.detail || 'Unknown error'}`, 'error');
            console.error('Upload error:', errorData);
        }
        
    } catch (error) {
        showStatus('❌ Upload error: ' + error.message, 'error');
        console.error('Upload error:', error);
    } finally {
        if (!currentJobId) {
            isProcessing = false;
            updateUploadUI(false);
        }
    }
}

// Start monitoring job progress
function startProgressMonitoring() {
    if (statusInterval) {
        clearInterval(statusInterval);
    }
    
    statusInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/jobs/${currentJobId}`);
            
            if (response.ok) {
                const jobData = await response.json();
                updateProgress(jobData);
                
                if (jobData.status === 'completed') {
                    handleJobComplete(jobData);
                } else if (jobData.status === 'failed') {
                    handleJobFailed(jobData);
                }
            } else {
                console.error('Failed to fetch job status');
            }
            
        } catch (error) {
            console.error('Progress monitoring error:', error);
        }
    }, POLL_INTERVAL);
}

// Update progress display
function updateProgress(jobData) {
    const { status, progress, filename, current_phase, source_type } = jobData;
    
    let statusText = '';
    let statusClass = 'info';
    const sourceIcon = source_type === 'twitch_vod' ? '🎮' : '📤';
    
    switch (status) {
        case 'queued':
            statusText = `⏳ Queued for processing: ${filename}`;
            showProgress(5);
            break;
        case 'downloading':
            statusText = `📥 Downloading: ${filename} (${progress}%)`;
            showProgress(progress);
            break;
        case 'processing':
            statusText = `🔄 Processing: ${filename} (${progress}%)`;
            showProgress(progress);
            break;
        case 'completed':
            statusText = `✅ Processing complete: ${filename}`;
            statusClass = 'success';
            showProgress(100);
            break;
        case 'failed':
            statusText = `❌ Processing failed: ${filename}`;
            statusClass = 'error';
            hideProgress();
            break;
        default:
            statusText = `${sourceIcon} Status: ${status}`;
    }
    
    showStatus(statusText, statusClass);
    
    // Update progress phase if available
    const progressPhaseElement = document.getElementById('progressPhase');
    if (progressPhaseElement && current_phase) {
        progressPhaseElement.textContent = current_phase;
        progressPhaseElement.style.display = 'block';
    } else if (progressPhaseElement) {
        progressPhaseElement.style.display = 'none';
    }
}

// Handle job completion
function handleJobComplete(jobData) {
    clearInterval(statusInterval);
    statusInterval = null;
    
    isProcessing = false;
    updateUploadUI(false);
    
    showStatus('🎉 Video processing completed successfully!', 'success');
    displayResults(jobData);
    
    // Hide progress bar after a brief delay
    setTimeout(() => {
        hideProgress();
    }, 2000);
    
    // Reset for next upload
    currentJobId = null;
    fileInput.value = '';
    document.getElementById('twitchUrlInput').value = '';
}

// Handle job failure
function handleJobFailed(jobData) {
    clearInterval(statusInterval);
    statusInterval = null;
    
    isProcessing = false;
    updateUploadUI(false);
    
    const errorMessage = jobData.error || 'Unknown error occurred';
    showStatus(`❌ Processing failed: ${errorMessage}`, 'error');
    hideProgress();
    
    // Reset for next upload
    currentJobId = null;
    fileInput.value = '';
    document.getElementById('twitchUrlInput').value = '';
}

// Display processing results
function displayResults(jobData) {
    const { clips, timestamps, analysis, stats } = jobData;
    
    if (!clips || clips.length === 0) {
        resultsDiv.innerHTML = '<p>No clips were generated. The video might not have enough audio activity.</p>';
        return;
    }
    
    let html = '<h3>🎬 Generated Clips</h3>';
    
    // Video analysis info
    if (analysis) {
        html += `<div class="analysis-info">
            <strong>📊 Video Analysis:</strong>
            Duration: ${analysis.duration?.toFixed(1)}s | 
            Resolution: ${analysis.resolution || 'N/A'} | 
            Audio: ${analysis.has_audio ? '✅' : '❌'}
        </div>`;
    }
    
    // Statistics
    if (stats) {
        html += `<div class="stats-info">
            <strong>🔍 Processing Stats:</strong>
            Audio peaks found: ${stats.total_peaks_found || 0} | 
            Clips generated: ${clips.length}
        </div>`;
    }
    
    // Clips list
    html += '<div class="clips-container">';
    clips.forEach((clipFilename, index) => {
        const timestamp = timestamps && timestamps[index] ? timestamps[index] : 'N/A';
        const timeFormatted = formatTime(timestamp);
        
        html += `
            <div class="clip-item">
                <h4>🎯 Clip ${index + 1}</h4>
                <p><strong>Timestamp:</strong> ${timeFormatted}</p>
                <p><strong>File:</strong> ${clipFilename}</p>
                <div class="clip-actions">
                    <button onclick="downloadClip('${clipFilename}')" class="download-btn">
                        📥 Download
                    </button>
                    <button onclick="previewClip('${clipFilename}')" class="preview-btn">
                        👁️ Preview
                    </button>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    // Bulk actions
    html += `
        <div class="bulk-actions">
            <button onclick="downloadAllClips()" class="bulk-download-btn">
                📦 Download All Clips
            </button>
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

// Format timestamp in seconds to readable format
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return 'N/A';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Download individual clip
async function downloadClip(filename) {
    try {
        const response = await fetch(`${API_BASE_URL}/download/${filename}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            window.URL.revokeObjectURL(url);
            
            showStatus(`📥 Downloaded: ${filename}`, 'success');
        } else {
            showStatus(`❌ Download failed: ${filename}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Download error: ${error.message}`, 'error');
        console.error('Download error:', error);
    }
}

// Preview clip (open in new tab)
function previewClip(filename) {
    const url = `${API_BASE_URL}/download/${filename}`;
    window.open(url, '_blank');
}

// Download all clips
async function downloadAllClips() {
    const clipItems = document.querySelectorAll('.clip-item');
    
    for (const item of clipItems) {
        const filename = item.querySelector('p:nth-child(3)').textContent.replace('File: ', '');
        await downloadClip(filename);
        await new Promise(resolve => setTimeout(resolve, 500)); // Small delay between downloads
    }
}

// Update upload UI state
function updateUploadUI(processing) {
    uploadButton.disabled = processing;
    fileInput.disabled = processing;
    
    if (processing) {
        uploadButton.textContent = '⏳ Processing...';
    } else {
        uploadButton.textContent = 'Upload & Process';
    }
}

// Show status message
function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
    statusDiv.style.display = 'block';
    console.log(`Status: ${message}`);
}

// Progress bar functions
function showProgress(percentage) {
    const progressSection = document.getElementById('progressSection');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    progressSection.style.display = 'block';
    progressFill.style.width = `${percentage}%`;
    progressText.textContent = `${percentage}%`;
}

function hideProgress() {
    const progressSection = document.getElementById('progressSection');
    progressSection.style.display = 'none';
}

// Export functions for global access
window.uploadFile = uploadFile;
window.downloadClip = downloadClip;
window.previewClip = previewClip;
window.downloadAllClips = downloadAllClips; 