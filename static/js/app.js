// NexaFiles Client-Side Application JavaScript

document.addEventListener('DOMContentLoaded', function () {
    initDropzone();
    initUploadForm();
});

// -------------------------------------------------------------
// Drag & Drop File Upload Handler
// -------------------------------------------------------------
function initDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const infoBox = document.getElementById('fileSelectionInfo');
    const nameSpan = document.getElementById('selectedFileName');
    const sizeSpan = document.getElementById('selectedFileSize');
    const categorySelect = document.getElementById('categorySelect');

    if (!dropzone || !fileInput) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('drag-active');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('drag-active');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateSelectedFileInfo(files[0]);
        }
    }, false);

    fileInput.addEventListener('change', function () {
        if (this.files.length > 0) {
            updateSelectedFileInfo(this.files[0]);
        }
    });

    function updateSelectedFileInfo(file) {
        if (!file) return;
        nameSpan.textContent = file.name;
        sizeSpan.textContent = formatBytes(file.size);
        infoBox.classList.remove('d-none');

        // Heuristic category auto-selection based on extension
        const ext = file.name.split('.').pop().toLowerCase();
        if (['py', 'js', 'html', 'css', 'json', 'cpp', 'java'].includes(ext)) {
            categorySelect.value = 'Code';
        } else if (['pdf', 'docx', 'doc', 'txt'].includes(ext)) {
            if (file.name.toLowerCase().includes('paper') || file.name.toLowerCase().includes('research')) {
                categorySelect.value = 'Research';
            } else {
                categorySelect.value = 'Notes';
            }
        } else if (['pptx', 'ppt'].includes(ext)) {
            categorySelect.value = 'Presentation';
        } else if (['png', 'jpg', 'jpeg', 'mp4', 'mp3'].includes(ext)) {
            categorySelect.value = 'Media';
        } else if (['zip', 'tar', 'gz', 'rar'].includes(ext)) {
            categorySelect.value = 'Archive';
        }
    }
}

function initUploadForm() {
    const uploadForm = document.getElementById('uploadForm');
    const progressBar = document.getElementById('uploadProgressBar');
    const submitBtn = document.getElementById('submitUploadBtn');

    if (!uploadForm) return;

    uploadForm.addEventListener('submit', function () {
        if (progressBar) progressBar.classList.remove('d-none');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Encrypting & Streaming...';
        }
    });
}

// -------------------------------------------------------------
// Interactive Star Toggle via AJAX
// -------------------------------------------------------------
function toggleFileStar(fileId, btnElement) {
    fetch(`/toggle-star/${fileId}`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const icon = btnElement.querySelector('i');
            if (data.is_starred) {
                icon.className = 'bi bi-star-fill text-warning fs-5';
            } else {
                icon.className = 'bi bi-star text-muted fs-5';
            }
        } else {
            alert('Failed to update favorite status.');
        }
    })
    .catch(err => {
        console.error('Star toggle error:', err);
    });
}

// -------------------------------------------------------------
// Confirm and Delete File
// -------------------------------------------------------------
function confirmDeleteFile(fileId, fileName) {
    if (!confirm(`Are you sure you want to permanently delete '${fileName}' from your cloud vault?`)) {
        return;
    }

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/delete/${fileId}`;
    document.body.appendChild(form);
    form.submit();
}

// -------------------------------------------------------------
// Metadata Inspector Modal Populate
// -------------------------------------------------------------
function showFileMetadata(file) {
    if (!file) return;

    document.getElementById('metaOriginalName').textContent = file.original_filename || file.filename;
    document.getElementById('metaS3Key').textContent = file.s3_key || '—';
    document.getElementById('metaChecksum').textContent = file.checksum || '—';
    document.getElementById('metaMime').textContent = file.mime_type || '—';
    document.getElementById('metaSize').textContent = formatBytes(file.file_size);
    document.getElementById('metaCategory').textContent = file.category || 'Other';
    document.getElementById('metaTags').textContent = file.tags || 'None';
    document.getElementById('metaDate').textContent = file.upload_date || '—';

    const downloadBtn = document.getElementById('metaDownloadBtn');
    if (downloadBtn) {
        downloadBtn.href = `/download/${file.id}`;
    }

    const modal = new bootstrap.Modal(document.getElementById('metadataModal'));
    modal.show();
}

// -------------------------------------------------------------
// Helper: Format Bytes to Human Readable
// -------------------------------------------------------------
function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// -------------------------------------------------------------
// Helper: Copy Pre-Signed Download Link to Clipboard
// -------------------------------------------------------------
function copyDownloadUrl(relativeUrl) {
    const fullUrl = window.location.origin + relativeUrl;
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(fullUrl).then(() => {
            showToast('Ephemeral Pre-Signed download URL copied!');
        }).catch(() => {
            prompt('Copy download URL:', fullUrl);
        });
    } else {
        prompt('Copy download URL:', fullUrl);
    }
}

function showToast(message) {
    const existing = document.querySelector('.toast-feedback');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast-feedback';
    toast.innerHTML = `<i class="bi bi-shield-check text-info fs-5"></i> <span>${message}</span>`;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(15px)';
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}
