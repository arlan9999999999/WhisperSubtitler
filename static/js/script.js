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

    // Show error message
    function showAlert(title, message, type = 'danger') {
        alertTitle.textContent = title;
        alertMessage.textContent = message;
        alertToast.className = `toast hide bg-${type} text-white`;
        toast.show();
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
        
        // Show progress bar
        uploadProgress.classList.remove('d-none');
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
                    
                    // Move to step 2
                    step1.classList.add('d-none');
                    step2.classList.remove('d-none');
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
        
        // Show processing status
        processingStatus.classList.remove('d-none');
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
            
            // Move to step 3
            step2.classList.add('d-none');
            step3.classList.remove('d-none');
            
            showAlert('Success', 'Transcription completed!', 'success');
        })
        .catch(error => {
            processingStatus.classList.add('d-none');
            showAlert('Error', 'Something went wrong during transcription.');
            document.getElementById('transcribeBtn').disabled = false;
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
            
            showAlert('Success', `Subtitles downloaded in ${format.toUpperCase()} format.`, 'success');
        })
        .catch(error => {
            if (downloadWindow) {
                downloadWindow.close();
            }
            showAlert('Error', 'Download failed. Please try again.');
            console.error('Download error:', error);
        });
    });

    // Navigation buttons
    backToUploadBtn.addEventListener('click', function() {
        step2.classList.add('d-none');
        step1.classList.remove('d-none');
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
        });
    });

    // Toggle transcript preview expansion
    togglePreviewBtn.addEventListener('click', function() {
        transcriptPreview.classList.toggle('expanded');
        
        const icon = togglePreviewBtn.querySelector('i');
        if (transcriptPreview.classList.contains('expanded')) {
            icon.classList.remove('fa-expand-alt');
            icon.classList.add('fa-compress-alt');
        } else {
            icon.classList.remove('fa-compress-alt');
            icon.classList.add('fa-expand-alt');
        }
    });
});
