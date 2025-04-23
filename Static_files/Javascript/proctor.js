/**
 * proctor.js - Handles exam proctoring with tab switching detection and webcam monitoring
 */

let examId = null;
let tabSwitchCount = 0;
let lastActiveTime = Date.now();
const INACTIVITY_THRESHOLD = 10000; // 10 seconds
let inactivityTimer = null;
let isSubmitting = false;

// Webcam monitoring variables
let webcamStream = null;
let webcamVideo = null;
let webcamCanvas = null;
let captureInterval = null;
const CAPTURE_INTERVAL = 15000; // Capture every 15 seconds
let isWebcamEnabled = false;

// Initialize proctoring
function initProctoring(examIdValue) {
    examId = examIdValue;
    
    // Set up event listeners for tab visibility and focus
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleWindowBlur);
    window.addEventListener('focus', handleWindowFocus);
    
    // Set up periodic activity check
    document.addEventListener('mousemove', resetInactivityTimer);
    document.addEventListener('keypress', resetInactivityTimer);
    document.addEventListener('click', resetInactivityTimer);
    
    // Start inactivity monitoring
    startInactivityMonitoring();
    
    console.log('Proctoring initialized for exam ID:', examId);
    
    // Initialize webcam monitoring if user grants permission
    initWebcamMonitoring();
    
    // Warn user about proctoring before exam starts
    alert('Warning: This exam is being proctored. Switching tabs or windows and your webcam feed will be monitored during the exam. This information may affect your grade.');
    
    // When form is submitted, prevent further tab switch warnings
    const examForm = document.getElementById('exam-form');
    if (examForm) {
        examForm.addEventListener('submit', function() {
            isSubmitting = true;
            stopWebcamMonitoring();
        });
    }
}

// Initialize webcam monitoring
function initWebcamMonitoring() {
    // Create video element for webcam feed
    webcamVideo = document.createElement('video');
    webcamVideo.setAttribute('autoplay', '');
    webcamVideo.setAttribute('playsinline', '');
    webcamVideo.style.display = 'none';
    document.body.appendChild(webcamVideo);
    
    // Create canvas for capturing frames
    webcamCanvas = document.createElement('canvas');
    webcamCanvas.style.display = 'none';
    document.body.appendChild(webcamCanvas);
    
    // Create webcam preview container
    const webcamContainer = document.createElement('div');
    webcamContainer.id = 'webcam-container';
    webcamContainer.style.position = 'fixed';
    webcamContainer.style.right = '20px';
    webcamContainer.style.top = '20px';
    webcamContainer.style.width = '160px';
    webcamContainer.style.height = '120px';
    webcamContainer.style.border = '2px solid #007bff';
    webcamContainer.style.borderRadius = '5px';
    webcamContainer.style.overflow = 'hidden';
    webcamContainer.style.zIndex = '1000';
    
    // Create webcam preview
    const webcamPreview = document.createElement('video');
    webcamPreview.id = 'webcam-preview';
    webcamPreview.setAttribute('autoplay', '');
    webcamPreview.setAttribute('playsinline', '');
    webcamPreview.style.width = '100%';
    webcamPreview.style.height = '100%';
    webcamPreview.style.objectFit = 'cover';
    
    webcamContainer.appendChild(webcamPreview);
    document.body.appendChild(webcamContainer);
    
    // Start webcam
    startWebcam();
}

// Start webcam monitoring
function startWebcam() {
    // Request webcam access
    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(function(stream) {
            webcamStream = stream;
            
            // Set video sources
            webcamVideo.srcObject = stream;
            document.getElementById('webcam-preview').srcObject = stream;
            
            isWebcamEnabled = true;
            
            // Start periodic capture
            startPeriodicCapture();
            
            console.log('Webcam monitoring started');
        })
        .catch(function(error) {
            console.error('Error accessing webcam:', error);
            alert('Webcam access is required for this exam. Please allow camera access and reload the page.');
            
            // Notify server about webcam access failure
            reportWebcamStatus(false, 'Webcam access denied: ' + error.message);
        });
}

// Start periodic webcam capture
function startPeriodicCapture() {
    captureInterval = setInterval(captureWebcamFrame, CAPTURE_INTERVAL);
    
    // Take initial capture
    setTimeout(captureWebcamFrame, 1000);
}

// Capture webcam frame and send to server
function captureWebcamFrame() {
    if (!isWebcamEnabled || isSubmitting) return;
    
    try {
        // Set canvas dimensions
        webcamCanvas.width = webcamVideo.videoWidth;
        webcamCanvas.height = webcamVideo.videoHeight;
        
        // Draw video frame to canvas
        const context = webcamCanvas.getContext('2d');
        context.drawImage(webcamVideo, 0, 0, webcamCanvas.width, webcamCanvas.height);
        
        // Get frame as base64 encoded image
        const imageData = webcamCanvas.toDataURL('image/jpeg', 0.7);
        
        // Send to server
        sendWebcamFrameToServer(imageData);
    } catch (error) {
        console.error('Error capturing webcam frame:', error);
    }
}

// Send webcam frame to server
function sendWebcamFrameToServer(imageData) {
    if (!examId) return;
    
    fetch(`/exam/${examId}/webcam-frame`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ 
            imageData: imageData,
            timestamp: Date.now()
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Webcam frame sent:', data);
        
        // Handle potential flags or alerts from server
        if (data.alert) {
            alert(data.alert);
        }
    })
    .catch(error => {
        console.error('Error sending webcam frame:', error);
    });
}

// Report webcam status to server
function reportWebcamStatus(isEnabled, message) {
    if (!examId) return;
    
    fetch(`/exam/${examId}/webcam-status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ 
            isEnabled: isEnabled,
            message: message
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Webcam status reported:', data);
    })
    .catch(error => {
        console.error('Error reporting webcam status:', error);
    });
}

// Stop webcam monitoring
function stopWebcamMonitoring() {
    if (captureInterval) {
        clearInterval(captureInterval);
        captureInterval = null;
    }
    
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }
    
    isWebcamEnabled = false;
    console.log('Webcam monitoring stopped');
}

// Handle visibility change (tab switching)
function handleVisibilityChange() {
    if (document.visibilityState === 'hidden' && !isSubmitting) {
        tabSwitchDetected();
    }
}

// Handle window losing focus
function handleWindowBlur() {
    if (!isSubmitting) {
        tabSwitchDetected();
    }
}

// Handle window gaining focus
function handleWindowFocus() {
    resetInactivityTimer();
}

// Record tab switch event
function tabSwitchDetected() {
    tabSwitchCount++;
    console.warn('Tab switch detected:', tabSwitchCount);
    
    // Report tab switch to server
    if (examId) {
        fetch(`/exam/${examId}/tab-switch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ switchCount: tabSwitchCount })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Tab switch recorded:', data);
            
            // Alert user (can be controlled via server response)
            if (data.message) {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error('Error recording tab switch:', error);
        });
    }
}

// Start monitoring for inactivity
function startInactivityMonitoring() {
    inactivityTimer = setInterval(checkActivity, 1000);
}

// Reset inactivity timer
function resetInactivityTimer() {
    lastActiveTime = Date.now();
}

// Check for user activity
function checkActivity() {
    const currentTime = Date.now();
    const inactiveTime = currentTime - lastActiveTime;
    
    if (inactiveTime > INACTIVITY_THRESHOLD) {
        console.warn('User inactive for extended period:', inactiveTime);
        // Could implement additional monitoring here
    }
}

// Get CSRF token from meta tag
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

// Confirm before leaving page during exam
window.addEventListener('beforeunload', function(e) {
    if (!isSubmitting) {
        const confirmationMessage = 'Are you sure you want to leave the exam? This will be recorded.';
        e.returnValue = confirmationMessage;
        return confirmationMessage;
    }
});
