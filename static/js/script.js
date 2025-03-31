document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const uploadForm = document.getElementById('uploadForm');
    const transcribeForm = document.getElementById('transcribeForm');
    const downloadForm = document.getElementById('downloadForm');
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseBtn');
    const dropArea = document.getElementById('dropArea');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = uploadProgress.querySelector('.progress-bar');
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');
    const stepIndicator1 = document.getElementById('stepIndicator1');
    const stepIndicator2 = document.getElementById('stepIndicator2');
    const stepIndicator3 = document.getElementById('stepIndicator3');
    const backToUploadBtn = document.getElementById('backToUploadBtn');
    const processingStatus = document.getElementById('processingStatus');
    const transcriptPreview = document.getElementById('transcriptPreview');
    const togglePreviewBtn = document.getElementById('togglePreviewBtn');
    const newFileBtn = document.getElementById('newFileBtn');
    const alertToast = document.getElementById('alertToast');
    const alertTitle = document.getElementById('alertTitle');
    const alertMessage = document.getElementById('alertMessage');

    // Bootstrap toast component
    const toast = new bootstrap.Toast(alertToast);

    // Show alert message with toast
    function showAlert(title, message, type = 'danger') {
        alertTitle.textContent = title;
        alertMessage.textContent = message;
        alertToast.className = `toast hide bg-${type} text-white`;
        toast.show();
    }

    // Update step indicators
    function updateStepIndicators(currentStep) {
        // Reset all indicators
        [stepIndicator1, stepIndicator2, stepIndicator3].forEach(indicator => {
            indicator.classList.remove('active', 'completed');
        });
        
        // Set active and completed states
        if (currentStep === 1) {
            stepIndicator1.classList.add('active');
        } else if (currentStep === 2) {
            stepIndicator1.classList.add('completed');
            stepIndicator2.classList.add('active');
        } else if (currentStep === 3) {
            stepIndicator1.classList.add('completed');
            stepIndicator2.classList.add('completed');
            stepIndicator3.classList.add('active');
        }
    }

    // Setup file drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropArea.classList.add('dragover');
    }

    function unhighlight() {
        dropArea.classList.remove('dragover');
    }

    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        fileInput.files = files;
        handleFileSelect();
    }

    // File selection handler
    fileInput.addEventListener('change', handleFileSelect);
    browseBtn.addEventListener('click', () => fileInput.click());

    function handleFileSelect() {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            fileName.textContent = file.name;
            fileInfo.classList.remove('d-none');
            uploadBtn.disabled = false;
            
            // Add animation to fileInfo
            fileInfo.classList.add('animate__animated', 'animate__fadeIn');
            setTimeout(() => {
                fileInfo.classList.remove('animate__animated', 'animate__fadeIn');
            }, 1000);
        } else {
            fileInfo.classList.add('d-none');
            uploadBtn.disabled = true;
        }
    }

    // File upload handler
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            showAlert('Error', 'Please select a file first.');
            return;
        }
        
        // Check file size (max 200MB)
        const maxSize = 200 * 1024 * 1024; // 200MB in bytes
        if (file.size > maxSize) {
            showAlert('Error', 'File is too large. Maximum size is 200MB.');
            return;
        }
        
        // Show progress bar with animation
        uploadProgress.classList.remove('d-none');
        uploadProgress.classList.add('animate__animated', 'animate__fadeIn');
        uploadBtn.disabled = true;
        
        // Create FormData
        const formData = new FormData();
        formData.append('file', file);
        
        // Send request
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = percentComplete + '%';
                progressBar.setAttribute('aria-valuenow', percentComplete);
            }
        });
        
        xhr.addEventListener('load', function(e) {
            uploadProgress.classList.add('d-none');
            
            try {
                const response = JSON.parse(xhr.responseText);
                
                if (xhr.status === 200) {
                    // Show success message
                    showAlert('Success', 'File uploaded successfully!', 'success');
                    
                    // Move to step 2 with animation
                    step1.classList.add('d-none');
                    step2.classList.remove('d-none');
                    step2.classList.add('animate__animated', 'animate__fadeIn');
                    setTimeout(() => {
                        step2.classList.remove('animate__animated', 'animate__fadeIn');
                    }, 1000);
                    
                    // Update step indicators
                    updateStepIndicators(2);
                } else {
                    showAlert('Error', response.error || 'Upload failed.');
                    uploadBtn.disabled = false;
                }
            } catch (err) {
                showAlert('Error', 'Something went wrong during upload.');
                uploadBtn.disabled = false;
            }
        });
        
        xhr.addEventListener('error', function() {
            uploadProgress.classList.add('d-none');
            showAlert('Error', 'A network error occurred.');
            uploadBtn.disabled = false;
        });
        
        xhr.open('POST', '/upload', true);
        xhr.send(formData);
    });

    // Transcribe handler
    transcribeForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Show processing status with animation
        processingStatus.classList.remove('d-none');
        processingStatus.classList.add('animate__animated', 'animate__fadeIn');
        document.getElementById('transcribeBtn').disabled = true;
        
        // Get form data
        const formData = new FormData(transcribeForm);
        
        // Send request
        fetch('/transcribe', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            processingStatus.classList.add('d-none');
            
            if (data.error) {
                showAlert('Error', data.error);
                document.getElementById('transcribeBtn').disabled = false;
                return;
            }
            
            // Show preview
            transcriptPreview.textContent = data.preview;
            
            // Move to step 3 with animation
            step2.classList.add('d-none');
            step3.classList.remove('d-none');
            step3.classList.add('animate__animated', 'animate__fadeIn');
            setTimeout(() => {
                step3.classList.remove('animate__animated', 'animate__fadeIn');
            }, 1000);
            
            // Update step indicators
            updateStepIndicators(3);
            
            showAlert('Success', 'Transcription completed!', 'success');
        })
        .catch(error => {
            processingStatus.classList.add('d-none');
            showAlert('Error', 'Something went wrong during transcription.');
            document.getElementById('transcribeBtn').disabled = false;
        });
    });

    // Add format option selection styling
    const formatOptions = document.querySelectorAll('.format-option');
    formatOptions.forEach(option => {
        const radioInput = option.previousElementSibling;
        
        option.addEventListener('click', function() {
            radioInput.checked = true;
            
            // Visual feedback
            formatOptions.forEach(opt => {
                opt.classList.remove('selected');
            });
            option.classList.add('selected');
        });
    });

    // Add task option selection styling
    const taskOptions = document.querySelectorAll('.task-option');
    taskOptions.forEach(option => {
        const radioInput = option.previousElementSibling;
        
        option.addEventListener('click', function() {
            radioInput.checked = true;
            
            // Visual feedback
            taskOptions.forEach(opt => {
                opt.classList.remove('selected');
            });
            option.classList.add('selected');
        });
    });

    // Download handler
    downloadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get selected format
        const format = document.querySelector('input[name="format"]:checked').value;
        
        // Create form data
        const formData = new FormData();
        formData.append('format', format);
        
        // Add loading indicator to button
        const downloadBtn = document.getElementById('downloadBtn');
        const originalBtnText = downloadBtn.innerHTML;
        downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Preparing download...';
        downloadBtn.disabled = true;
        
        // Start download
        const downloadWindow = window.open('', '_blank');
        
        fetch('/download', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.blob();
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            // Set the filename based on content type
            const contentDisposition = response.headers.get('content-disposition');
            let filename = 'subtitles.' + format;
            
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]*)"?/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1];
                }
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            if (downloadWindow) {
                downloadWindow.close();
            }
            
            // Reset download button
            downloadBtn.innerHTML = originalBtnText;
            downloadBtn.disabled = false;
            
            showAlert('Success', `Subtitles downloaded in ${format.toUpperCase()} format.`, 'success');
            
            // Delete the file from Gofile storage after download
            setTimeout(() => {
                fetch('/download-complete', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        console.log('File deleted from cloud storage after download');
                    }
                })
                .catch(error => {
                    console.error('Error deleting file from cloud storage:', error);
                });
            }, 1000);
        })
        .catch(error => {
            if (downloadWindow) {
                downloadWindow.close();
            }
            
            // Reset download button
            downloadBtn.innerHTML = originalBtnText;
            downloadBtn.disabled = false;
            
            showAlert('Error', 'Download failed. Please try again.');
            console.error('Download error:', error);
        });
    });

    // Navigation buttons
    backToUploadBtn.addEventListener('click', function() {
        step2.classList.add('d-none');
        step1.classList.remove('d-none');
        
        // Update step indicators
        updateStepIndicators(1);
    });

    newFileBtn.addEventListener('click', function() {
        // Clear the session on the server
        fetch('/clear', {
            method: 'POST'
        })
        .then(() => {
            // Reset the UI
            fileInput.value = '';
            fileInfo.classList.add('d-none');
            uploadBtn.disabled = true;
            document.getElementById('transcribeBtn').disabled = false;
            
            // Reset the progress
            progressBar.style.width = '0%';
            progressBar.setAttribute('aria-valuenow', 0);
            
            // Go back to step 1
            step3.classList.add('d-none');
            step1.classList.remove('d-none');
            
            // Update step indicators
            updateStepIndicators(1);
        });
    });

    // Toggle transcript preview expansion
    togglePreviewBtn.addEventListener('click', function() {
        transcriptPreview.classList.toggle('expanded');
        
        const icon = togglePreviewBtn.querySelector('i');
        if (transcriptPreview.classList.contains('expanded')) {
            icon.classList.remove('fa-expand-alt');
            icon.classList.add('fa-compress-alt');
            togglePreviewBtn.setAttribute('title', 'Collapse preview');
        } else {
            icon.classList.remove('fa-compress-alt');
            icon.classList.add('fa-expand-alt');
            togglePreviewBtn.setAttribute('title', 'Expand preview');
        }
    });

    // Add additional styling to step badges
    document.querySelectorAll('.badge').forEach(badge => {
        badge.style.background = 'var(--primary-gradient)';
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
