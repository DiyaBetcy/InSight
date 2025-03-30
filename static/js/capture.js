/**
 * Camera capture functionality for attendance tracking
 */

function initCapture(postUrl) {
    const videoElement = document.getElementById('video');
    const captureBtn = document.getElementById('capture-btn');
    const processingIndicator = document.getElementById('processing-indicator');
    const resultContainer = document.getElementById('result-container');
    const attendanceList = document.getElementById('attendance-list');
    const newCaptureBtn = document.getElementById('new-capture-btn');
    const captureControls = document.getElementById('capture-controls');
    const successMessage = document.getElementById('success-message');
    
    let stream = null;
    
    // Start video stream
    async function startVideo() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'user' }, 
                audio: false 
            });
            videoElement.srcObject = stream;
        } catch (err) {
            console.error('Error accessing camera:', err);
            alert('Could not access camera. Please allow camera access and try again.');
        }
    }
    
    // Stop video stream
    function stopVideo() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            videoElement.srcObject = null;
        }
    }
    
    // Handle capture button click
    captureBtn.addEventListener('click', function() {
        captureControls.classList.add('d-none');
        processingIndicator.classList.remove('d-none');
        
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        // Set canvas dimensions to match video
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        
        // Draw the current video frame on the canvas
        context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        
        // Get the image data as base64 string
        const imageData = canvas.toDataURL('image/jpeg');
        
        // Send the image to the server
        fetch(postUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ imageData: imageData }),
        })
        .then(response => response.json())
        .then(data => {
            processingIndicator.classList.add('d-none');
            
            if (data.success) {
                // Show the attendance results
                resultContainer.classList.remove('d-none');
                
                // Update success message
                successMessage.textContent = `Attendance has been recorded successfully! Session ID: ${data.session_id}`;
                
                // Populate the attendance list
                attendanceList.innerHTML = '';
                
                if (data.detected_students) {
                    // Sort students by name
                    const students = Object.keys(data.detected_students).sort();
                    
                    // Count present and absent
                    let presentCount = 0;
                    let absentCount = 0;
                    
                    students.forEach(student => {
                        const isPresent = data.detected_students[student];
                        
                        if (isPresent) {
                            presentCount++;
                        } else {
                            absentCount++;
                        }
                        
                        const listItem = document.createElement('li');
                        listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                        
                        listItem.innerHTML = `
                            ${student}
                            <span class="badge ${isPresent ? 'bg-success' : 'bg-danger'}">
                                ${isPresent ? 'Present' : 'Absent'}
                            </span>
                        `;
                        
                        attendanceList.appendChild(listItem);
                    });
                    
                    // Add summary at the top
                    const summaryItem = document.createElement('li');
                    summaryItem.className = 'list-group-item d-flex justify-content-between align-items-center active';
                    
                    summaryItem.innerHTML = `
                        <span>Total: ${students.length} students</span>
                        <div>
                            <span class="badge bg-light text-dark me-2">Present: ${presentCount}</span>
                            <span class="badge bg-light text-dark">Absent: ${absentCount}</span>
                        </div>
                    `;
                    
                    attendanceList.insertBefore(summaryItem, attendanceList.firstChild);
                }
                
                // Stop the video
                stopVideo();
            } else {
                alert(`Error: ${data.message}`);
                captureControls.classList.remove('d-none');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            processingIndicator.classList.add('d-none');
            captureControls.classList.remove('d-none');
            alert('A network error occurred. Please try again.');
        });
    });
    
    // New capture button
    newCaptureBtn.addEventListener('click', function() {
        resultContainer.classList.add('d-none');
        captureControls.classList.remove('d-none');
        startVideo();
    });
    
    // Start the video when the page loads
    startVideo();
}
