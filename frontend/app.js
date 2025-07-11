let currentJobId = null;
let statusInterval = null;

async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a video file');
        return;
    }
    
    // For now, just show a placeholder message
    showStatus('Day 1 Setup Complete! Backend integration coming in Day 3...', 'info');
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
}

// Test function to verify JavaScript is working
function testJS() {
    console.log('StreamClip AI frontend loaded successfully!');
    showStatus('Frontend loaded successfully!', 'success');
}

// Call test function when page loads
window.addEventListener('load', testJS); 