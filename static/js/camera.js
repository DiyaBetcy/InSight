// This file contains common camera handling functions
// that can be reused across different pages

/**
 * Initializes the camera stream
 * @param {HTMLVideoElement} videoElement - Video element to display the stream
 * @param {Function} onSuccess - Callback function on successful camera initialization
 * @param {Function} onError - Callback function on camera initialization error
 * @param {Object} constraints - Media constraints (optional)
 */
function initCamera(videoElement, onSuccess, onError, constraints = null) {
    // Default constraints
    const defaultConstraints = { 
        video: { 
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user" 
        } 
    };
    
    // Use provided constraints or default
    const mediaConstraints = constraints || defaultConstraints;
    
    // Request camera access
    navigator.mediaDevices.getUserMedia(mediaConstraints)
        .then(stream => {
            videoElement.srcObject = stream;
            if (onSuccess) onSuccess(stream);
        })
        .catch(err => {
            console.error('Error accessing camera:', err);
            if (onError) onError(err);
        });
}

/**
 * Captures a photo from the video stream
 * @param {HTMLVideoElement} videoElement - Video element with the stream
 * @param {Boolean} asDataURL - Whether to return the image as dataURL (default true)
 * @returns {String|ImageData} - Image as dataURL string or ImageData object
 */
function capturePhoto(videoElement, asDataURL = true) {
    // Create a canvas element
    const canvas = document.createElement('canvas');
    canvas.width = videoElement.videoWidth;
    canvas.height = videoElement.videoHeight;
    
    // Draw the current video frame to canvas
    const context = canvas.getContext('2d');
    context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
    
    // Return as dataURL or image data
    if (asDataURL) {
        return canvas.toDataURL('image/jpeg');
    } else {
        return context.getImageData(0, 0, canvas.width, canvas.height);
    }
}

/**
 * Stops all tracks in a media stream
 * @param {MediaStream} stream - The media stream to stop
 */
function stopCameraStream(stream) {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
}
