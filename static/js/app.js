// NexaFiles Client-Side Application JavaScript
// Enterprise Edition: Previews, AI Summaries, Ephemeral Sharing & Version Control

document.addEventListener('DOMContentLoaded', function () {
    initMoodThemes();
    init3DTilt();
    initDropzone();
    initUploadForm();
});

// Current active IDs for modals
let activeFileId = null;
let currentPreviewRawCode = '';

function showSafeAlert(container, message, type = 'danger') {
    if (!container) return;
    container.innerHTML = '';
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    container.appendChild(alertDiv);
}

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
                showSafeAlert(body, data.error || 'Unable to preview file.');
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
            showSafeAlert(body, 'Error loading document preview: ' + err.message);
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

            // Populate Suggested Tags (Sanitized against DOM XSS)
            const tagContainer = document.getElementById('aiSuggestedTags');
            tagContainer.innerHTML = '';
            data.suggested_tags.forEach(tag => {
                const badge = document.createElement('span');
                badge.className = 'badge bg-light text-primary border rounded-pill px-3 py-1 cursor-pointer';
                badge.style.cursor = 'pointer';
                const icon = document.createElement('i');
                icon.className = 'bi bi-plus me-1';
                badge.appendChild(icon);
                badge.appendChild(document.createTextNode(tag));
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
                showSafeAlert(listEl, data.error || 'Failed to load versions.');
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
function showFileMetadata(elOrFile) {
    let file = elOrFile;
    if (elOrFile && elOrFile.dataset && elOrFile.dataset.file) {
        try {
            file = JSON.parse(elOrFile.dataset.file);
        } catch (e) {
            console.error("Failed to parse file metadata", e);
            return;
        }
    }
    if (!file) return;

    document.getElementById('metaOriginalName').textContent = file.original_filename || file.filename;
    const verEl = document.getElementById('metaVersion');
    if (verEl) {
        verEl.innerHTML = '';
        const badge = document.createElement('span');
        badge.className = 'badge bg-primary rounded-pill px-2';
        badge.textContent = `v${file.version || 1}`;
        verEl.appendChild(badge);
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
    const icon = document.createElement('i');
    icon.className = 'bi bi-shield-check text-info fs-5 me-2';
    const msgSpan = document.createElement('span');
    msgSpan.textContent = message;
    toast.appendChild(icon);
    toast.appendChild(msgSpan);
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(15px)';
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}

// =============================================================
// DYNAMIC MOOD THEME & 3D DASHBOARD ENGINE
// =============================================================

const MOOD_METADATA = {
    obsidian: {
        name: 'Deep Focus',
        icon: 'bi-stars',
        emoji: '🌌',
        color: '#6366f1',
        vibe: 'Deep space cyber aurora & locked-in focus'
    },
    cyberpunk: {
        name: 'Neon Rush',
        icon: 'bi-lightning-charge-fill',
        emoji: '⚡',
        color: '#ec4899',
        vibe: 'Synthwave hyperdrive & vibrant neon pulse'
    },
    emerald: {
        name: 'Zen Flow',
        icon: 'bi-tree-fill',
        emoji: '🌿',
        color: '#10b981',
        vibe: 'Tranquil calm, clarity & balanced mindset'
    },
    sunset: {
        name: 'Creative Fire',
        icon: 'bi-fire',
        emoji: '🔥',
        color: '#f59e0b',
        vibe: 'Warm radiant energy, passion & creative flow'
    },
    arctic: {
        name: 'Frost Chill',
        icon: 'bi-snow',
        emoji: '❄️',
        color: '#0284c7',
        vibe: 'Glacial clarity, diamond ice & crisp thoughts'
    },
    midnight: {
        name: 'Royalty',
        icon: 'bi-gem',
        emoji: '💎',
        color: '#3b82f6',
        vibe: 'Executive sapphire, sovereign power & prestige'
    }
};

function initMoodThemes() {
    const savedMood = localStorage.getItem('nexafiles-mood-theme') || 'obsidian';
    setMoodTheme(savedMood, false);
}

function setMoodTheme(moodKey, triggerFeedback = true) {
    if (!MOOD_METADATA[moodKey]) moodKey = 'obsidian';
    
    document.documentElement.setAttribute('data-mood', moodKey);
    localStorage.setItem('nexafiles-mood-theme', moodKey);

    const meta = MOOD_METADATA[moodKey];

    // Update active state on mood chips in dock
    document.querySelectorAll('.mood-chip-btn').forEach(btn => {
        const isMatch = btn.getAttribute('data-mood-target') === moodKey;
        btn.classList.toggle('active', isMatch);
        if (isMatch) {
            btn.setAttribute('aria-pressed', 'true');
        } else {
            btn.removeAttribute('aria-pressed');
        }
    });

    // Update navbar mood badge & dropdown
    const navBadge = document.getElementById('navbarMoodBadge');
    if (navBadge) {
        navBadge.innerHTML = `<span class="mood-swatch-dot me-1" style="color: ${meta.color}; background-color: ${meta.color};"></span> ${meta.emoji} ${meta.name}`;
    }

    // Update dropdown active checkmarks
    document.querySelectorAll('.dropdown-item-mood').forEach(item => {
        const isMatch = item.getAttribute('data-mood-target') === moodKey;
        item.classList.toggle('active', isMatch);
        const check = item.querySelector('.mood-check-icon');
        if (check) check.style.display = isMatch ? 'inline-block' : 'none';
    });

    // Update vibe description text on dashboard dock
    const vibeText = document.getElementById('moodVibeText');
    if (vibeText) {
        vibeText.textContent = `${meta.emoji} ${meta.vibe}`;
    }

    if (triggerFeedback) {
        showToast(`Mood theme switched to ${meta.emoji} ${meta.name}!`);
    }
}

// -------------------------------------------------------------
// Interactive 3D Card Tilt Engine
// -------------------------------------------------------------
function init3DTilt() {
    // Check 3D mode setting
    const saved3D = localStorage.getItem('nexafiles-3d-mode') || 'on';
    document.documentElement.setAttribute('data-3d-mode', saved3D);
    update3DModeButton(saved3D);

    const cards = document.querySelectorAll('.tilt-card-3d');
    cards.forEach(card => {
        // Ensure glare element exists
        if (!card.querySelector('.glare-sheen')) {
            const glare = document.createElement('div');
            glare.className = 'glare-sheen';
            card.appendChild(glare);
        }

        let isHovered = false;
        let animationFrameId = null;

        card.addEventListener('mouseenter', () => {
            if (document.documentElement.getAttribute('data-3d-mode') === 'off') return;
            isHovered = true;
            card.style.transition = 'transform 0.1s ease-out, box-shadow 0.25s ease';
        });

        card.addEventListener('mousemove', (e) => {
            if (document.documentElement.getAttribute('data-3d-mode') === 'off') return;
            if (!isHovered) isHovered = true;

            if (animationFrameId) cancelAnimationFrame(animationFrameId);

            animationFrameId = requestAnimationFrame(() => {
                const rect = card.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;

                const percentX = mouseX / rect.width;
                const percentY = mouseY / rect.height;

                const normX = (percentX - 0.5) * 2; // -1 to 1
                const normY = (percentY - 0.5) * 2; // -1 to 1

                const maxTilt = card.dataset.tiltMax ? parseFloat(card.dataset.tiltMax) : 12;
                const rotX = -normY * maxTilt;
                const rotY = normX * maxTilt;

                card.style.transform = `perspective(1000px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) translateZ(10px) scale3d(1.02, 1.02, 1.02)`;
                card.style.setProperty('--glare-x', `${(percentX * 100).toFixed(1)}%`);
                card.style.setProperty('--glare-y', `${(percentY * 100).toFixed(1)}%`);
            });
        });

        card.addEventListener('mouseleave', () => {
            isHovered = false;
            if (animationFrameId) cancelAnimationFrame(animationFrameId);
            card.style.transition = 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease';
            card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px) scale3d(1, 1, 1)';
        });
    });
}

function toggle3DMode() {
    const current = document.documentElement.getAttribute('data-3d-mode') || 'on';
    const next = current === 'on' ? 'off' : 'on';
    document.documentElement.setAttribute('data-3d-mode', next);
    localStorage.setItem('nexafiles-3d-mode', next);
    update3DModeButton(next);
    showToast(`3D Dashboard Depth FX: ${next.toUpperCase()}`);
}

function update3DModeButton(mode) {
    ['toggle3DModeBtn', 'toggle3DModeBtnGuest'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
            if (mode === 'on') {
                btn.className = 'btn btn-outline-info btn-sm rounded-pill px-3 d-flex align-items-center gap-1 active';
                btn.innerHTML = '<i class="bi bi-badge-3d-fill"></i> <span class="d-none d-md-inline">3D Active</span>';
                btn.title = '3D Tilt & Parallax is ON (Click to disable)';
            } else {
                btn.className = 'btn btn-outline-secondary btn-sm rounded-pill px-3 d-flex align-items-center gap-1';
                btn.innerHTML = '<i class="bi bi-badge-3d"></i> <span class="d-none d-md-inline">3D Off</span>';
                btn.title = '3D Tilt & Parallax is OFF (Click to enable)';
            }
        }
    });
}
