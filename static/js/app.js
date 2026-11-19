// NexaFiles Client-Side Application JavaScript
// Enterprise Edition: Previews, AI Summaries, Ephemeral Sharing & Version Control

document.addEventListener('DOMContentLoaded', function () {
    initDropzone();
    initUploadForm();
});

// Current active IDs for modals
let activeFileId = null;
let currentPreviewRawCode = '';

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
        if (['py', 'js', 'html', 'css', 'json', 'cpp', 'java', 'sql', 'sh'].includes(ext)) {
            categorySelect.value = 'Code';
        } else if (['pdf', 'docx', 'doc', 'txt'].includes(ext)) {
            if (file.name.toLowerCase().includes('paper') || file.name.toLowerCase().includes('research')) {
                categorySelect.value = 'Research';
            } else {
                categorySelect.value = 'Notes';
            }
        } else if (['pptx', 'ppt'].includes(ext)) {
            categorySelect.value = 'Presentation';
        } else if (['png', 'jpg', 'jpeg', 'mp4', 'mp3', 'gif'].includes(ext)) {
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
// In-Browser Document & Code Preview Engine
// -------------------------------------------------------------
function openPreviewModal(fileId) {
    activeFileId = fileId;
    const modalEl = document.getElementById('previewModal');
    if (!modalEl) return;

    const modal = new bootstrap.Modal(modalEl);
    const body = document.getElementById('previewBody');
    const filenameEl = document.getElementById('previewFilename');
    const langBadge = document.getElementById('previewLanguage');
    const copyBtn = document.getElementById('copyCodeBtn');
    const downloadBtn = document.getElementById('previewDownloadBtn');

    body.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="text-muted small mt-2">Loading document stream from cloud vault...</p>
        </div>
    `;
    copyBtn.style.display = 'none';
    downloadBtn.href = `/download/${fileId}`;
    langBadge.textContent = '';

    modal.show();

    fetch(`/api/preview/${fileId}`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                body.innerHTML = `<div class="alert alert-danger">${data.error || 'Unable to preview file.'}</div>`;
                return;
            }

            filenameEl.textContent = data.filename;

            if (data.preview_type === 'code') {
                currentPreviewRawCode = data.content;
                langBadge.textContent = data.language.toUpperCase();
                copyBtn.style.display = 'inline-block';
                body.innerHTML = `
                    <div class="p-3 bg-dark text-light rounded-4 overflow-auto" style="max-height: 550px;">
                        <pre class="mb-0"><code style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.88rem; line-height: 1.6;">${escapeHtml(data.content)}</code></pre>
                    </div>
                `;
            } else if (data.preview_type === 'image') {
                body.innerHTML = `
                    <div class="text-center py-2">
                        <img src="${data.url}" class="img-fluid rounded-4 shadow-sm" style="max-height: 550px;" alt="${data.filename}">
                    </div>
                `;
            } else if (data.preview_type === 'pdf') {
                body.innerHTML = `
                    <div class="ratio ratio-16x9" style="height: 600px;">
                        <iframe src="${data.url}" class="rounded-4 border-0 w-100 h-100" title="PDF Preview"></iframe>
                    </div>
                `;
            } else {
                body.innerHTML = `
                    <div class="text-center py-5">
                        <i class="bi bi-file-earmark-lock display-4 text-muted mb-3 d-block"></i>
                        <h6 class="fw-bold text-dark">Native In-Browser Preview Unavailable</h6>
                        <p class="text-muted small mb-3">${data.message || 'Please download the file to inspect its full payload.'}</p>
                        <a href="/download/${fileId}" class="btn btn-brand-primary btn-sm rounded-pill px-4">
                            <i class="bi bi-download me-1"></i> Download File (${data.size || ''})
                        </a>
                    </div>
                `;
            }
        })
        .catch(err => {
            body.innerHTML = `<div class="alert alert-danger">Error loading document preview: ${err.message}</div>`;
        });
}

function copyPreviewContent() {
    if (!currentPreviewRawCode) return;
    navigator.clipboard.writeText(currentPreviewRawCode).then(() => {
        showToast('Source code copied to clipboard!');
    }).catch(() => {
        alert('Code copied!');
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}

// -------------------------------------------------------------
// AI Document Summarizer & Smart Tagging
// -------------------------------------------------------------
function openAIModal(fileId, filename) {
    activeFileId = fileId;
    const modalEl = document.getElementById('aiSummaryModal');
    if (!modalEl) return;

    const modal = new bootstrap.Modal(modalEl);
    document.getElementById('aiDocName').textContent = filename;
    document.getElementById('aiLoading').classList.remove('d-none');
    document.getElementById('aiResult').classList.add('d-none');

    modal.show();

    fetch(`/api/ai/summarize/${fileId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            document.getElementById('aiLoading').classList.add('d-none');
            if (!data.success) {
                alert(data.error || 'AI analysis failed.');
                return;
            }

            document.getElementById('aiResult').classList.remove('d-none');
            
            // Populate 3 bullets
            const bulletsList = document.getElementById('aiBulletsList');
            bulletsList.innerHTML = '';
            data.bullets.forEach(b => {
                const li = document.createElement('li');
                li.className = 'mb-1';
                li.textContent = b;
                bulletsList.appendChild(li);
            });

            // Populate Suggested Tags
            const tagContainer = document.getElementById('aiSuggestedTags');
            tagContainer.innerHTML = '';
            data.suggested_tags.forEach(tag => {
                const badge = document.createElement('span');
                badge.className = 'badge bg-light text-primary border rounded-pill px-3 py-1 cursor-pointer';
                badge.style.cursor = 'pointer';
                badge.innerHTML = `<i class="bi bi-plus"></i> ${tag}`;
                badge.onclick = () => addSuggestedTag(tag);
                tagContainer.appendChild(badge);
            });

            document.getElementById('aiCurrentTags').value = data.current_tags || '';
        })
        .catch(err => {
            document.getElementById('aiLoading').classList.add('d-none');
            alert('AI analysis error: ' + err.message);
        });
}

function addSuggestedTag(tag) {
    const tagInput = document.getElementById('aiCurrentTags');
    const current = tagInput.value.split(',').map(t => t.trim()).filter(Boolean);
    if (!current.includes(tag)) {
        current.push(tag);
        tagInput.value = current.join(', ');
        showToast(`Added tag '${tag}'`);
    }
}

function saveAITags() {
    if (!activeFileId) return;
    const tags = document.getElementById('aiCurrentTags').value;
    
    // Gather bullets for summary
    const lis = document.querySelectorAll('#aiBulletsList li');
    const summary = Array.from(lis).map(li => li.textContent).join(' \u2022 ');

    fetch(`/api/ai/apply-tags/${activeFileId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags: tags, summary: summary })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast('AI Summary & Metadata tags saved!');
            const modal = bootstrap.Modal.getInstance(document.getElementById('aiSummaryModal'));
            if (modal) modal.hide();
        } else {
            alert(data.error || 'Failed to update tags.');
        }
    });
}

// -------------------------------------------------------------
// Ephemeral Secure Sharing Modal
// -------------------------------------------------------------
function openShareModal(fileId) {
    activeFileId = fileId;
    const modalEl = document.getElementById('shareModal');
    if (!modalEl) return;

    document.getElementById('shareLinkContainer').classList.add('d-none');
    document.getElementById('sharePassword').value = '';
    document.getElementById('shareMaxDownloads').value = '0';
    document.getElementById('generateShareBtn').disabled = false;

    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}

function submitShareCreation() {
    if (!activeFileId) return;

    const expiry = document.getElementById('shareExpiry').value;
    const password = document.getElementById('sharePassword').value;
    const maxDl = document.getElementById('shareMaxDownloads').value;
    const btn = document.getElementById('generateShareBtn');

    btn.disabled = true;

    fetch(`/api/share/${activeFileId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            expires_hours: parseInt(expiry),
            password: password,
            max_downloads: parseInt(maxDl)
        })
    })
    .then(res => res.json())
    .then(data => {
        btn.disabled = false;
        if (data.success) {
            document.getElementById('shareLinkContainer').classList.remove('d-none');
            document.getElementById('generatedShareUrl').value = data.share_url;
            showToast('Share link created successfully!');
        } else {
            alert(data.error || 'Failed to generate share link.');
        }
    })
    .catch(err => {
        btn.disabled = false;
        alert('Share creation error: ' + err.message);
    });
}

function copyGeneratedShareUrl() {
    const input = document.getElementById('generatedShareUrl');
    input.select();
    navigator.clipboard.writeText(input.value).then(() => {
        showToast('Public share link copied to clipboard!');
    });
}

// -------------------------------------------------------------
// Smart Revision Control & Version Rollback
// -------------------------------------------------------------
function openVersionModal(fileId, filename) {
    activeFileId = fileId;
    const modalEl = document.getElementById('versionModal');
    if (!modalEl) return;

    document.getElementById('versionDocName').textContent = filename;
    const listEl = document.getElementById('versionList');
    listEl.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary" role="status"></div></div>';

    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    fetch(`/api/versions/${fileId}`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                listEl.innerHTML = `<div class="alert alert-danger">${data.error || 'Failed to load versions.'}</div>`;
                return;
            }

            if (!data.versions || data.versions.length === 0) {
                listEl.innerHTML = '<p class="text-muted small">No revisions recorded yet.</p>';
                return;
            }

            let html = '<div class="list-group list-group-flush">';
            data.versions.forEach(v => {
                const isCurrent = v.version_number === data.current_version;
                html += `
                    <div class="list-group-item d-flex justify-content-between align-items-center px-0 py-3">
                        <div>
                            <div class="d-flex align-items-center gap-2">
                                <span class="badge ${isCurrent ? 'bg-primary' : 'bg-secondary'} rounded-pill">v${v.version_number}</span>
                                <strong class="small text-dark">${isCurrent ? 'Current Active Version' : 'Historical Revision'}</strong>
                            </div>
                            <div class="text-muted small mt-1 font-monospace">
                                Size: ${v.formatted_size} &bull; Uploaded: ${v.created_at || '—'}
                            </div>
                            <div class="text-muted small font-monospace text-truncate" style="max-width: 320px;">
                                Hash: ${v.checksum.substring(0, 16)}...
                            </div>
                        </div>
                        <div>
                            ${isCurrent ? 
                                '<span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25 rounded-pill px-3 py-1">Active</span>' :
                                `<form method="POST" action="/restore-version/${fileId}/${v.id}" class="d-inline">
                                    <button type="submit" class="btn btn-outline-primary btn-sm rounded-pill px-3" onclick="return confirm('Restore this version as active?')">
                                        <i class="bi bi-arrow-counterclockwise me-1"></i> Restore
                                    </button>
                                 </form>`
                            }
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            listEl.innerHTML = html;
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
    const verEl = document.getElementById('metaVersion');
    if (verEl) {
        verEl.innerHTML = `<span class="badge bg-primary rounded-pill px-2">v${file.version || 1}</span>`;
    }
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
