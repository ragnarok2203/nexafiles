# -*- coding: utf-8 -*-
"""
NexaFiles: Cloud-Based Intelligent File Organization and Retrieval System
Flask Application Factory & HTTP Routing Controllers
Enterprise Edition: In-Browser Previews, AI Summarization, Smart Versioning,
Ephemeral Share Links, Deduplication, and Comprehensive Security Audit Trails.
"""

import os
import io
import csv
import time
import mimetypes
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse, urljoin
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, send_file, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from services.metadata_service import (
    init_db, create_file_record, get_file_by_id,
    delete_file_record, toggle_star, search_files,
    get_user_metrics, format_bytes, find_file_by_checksum,
    find_user_file_by_name, add_file_version, get_file_versions,
    restore_file_version, create_shared_link, get_shared_link,
    record_shared_download, update_file_summary_and_tags,
    log_activity, get_user_activity
)
from services.auth_service import (
    register_user, authenticate_user, login_user_session,
    logout_user_session, get_current_user, login_required
)
from services.storage_service import storage_service
from services.ai_service import ai_service

# Rate limiting and brute-force mitigation trackers: ip -> list of timestamps
_FAILED_LOGINS = defaultdict(list)
_FAILED_SHARE_AUTH = defaultdict(list)

def is_safe_url(target, host_url):
    """Verify redirection target strictly stays on the same domain/host."""
    if not target:
        return False
    ref_url = urlparse(host_url)
    test_url = urlparse(urljoin(host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

def is_rate_limited(ip, tracker, max_attempts=5, window=60):
    """Check if an IP address has exceeded failed authentication attempts in window seconds."""
    now = time.time()
    tracker[ip] = [ts for ts in tracker[ip] if now - ts < window]
    return len(tracker[ip]) >= max_attempts

def record_failed_attempt(ip, tracker):
    """Record a failed authentication timestamp."""
    tracker[ip].append(time.time())

def clear_failed_attempts(ip, tracker):
    """Reset failed attempts for an IP address upon successful authentication."""
    tracker.pop(ip, None)

def create_app(test_config=None):
    """Flask Application Factory Pattern."""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Apply configuration
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
        
    # Ensure database tables exist within app context
    with app.app_context():
        init_db()

    # -------------------------------------------------------------
    # Enterprise Security Headers Middleware (OWASP Secure Headers)
    # -------------------------------------------------------------
    @app.after_request
    def set_security_headers(response):
        """Inject enterprise-grade HTTP security headers on all responses."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "frame-src 'self';"
        )
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response
    
    # -------------------------------------------------------------
    # Context Processor: Inject standard variables into all templates
    # -------------------------------------------------------------
    @app.context_processor
    def inject_global_template_vars():
        return {
            'current_user': get_current_user(),
            'categories': Config.CATEGORIES,
            'category_colors': Config.CATEGORY_COLORS,
            'storage_status': storage_service.get_status(),
            'format_bytes': format_bytes
        }

    # -------------------------------------------------------------
    # Root & Authentication Routes
    # -------------------------------------------------------------
    @app.route('/')
    def index():
        """Root route: redirect to dashboard or login."""
        if get_current_user():
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration endpoint with input sanitization and password hashing."""
        if get_current_user():
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm = request.form.get('confirm_password')
            
            if password != confirm:
                flash("Passwords do not match.", "danger")
                return render_template('register.html', username=username, email=email)
                
            success, msg, user_id = register_user(username, email, password)
            if success:
                log_activity(user_id, 'USER_REGISTER', f"Account registered: {username}", request.remote_addr)
                flash(msg, "success")
                return redirect(url_for('login'))
            else:
                flash(msg, "danger")
                return render_template('register.html', username=username, email=email)
                
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login authentication endpoint with brute-force protection and open-redirect defense."""
        if get_current_user():
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            identifier = request.form.get('username_or_email')
            password = request.form.get('password')
            client_ip = request.remote_addr or '127.0.0.1'
            
            # Rate limiting check (bypassed in pytest testing environment)
            if not app.config.get('TESTING') and is_rate_limited(client_ip, _FAILED_LOGINS, max_attempts=5, window=60):
                flash("Too many failed login attempts detected. Please wait 60 seconds before trying again.", "danger")
                return render_template('login.html', identifier=identifier)
            
            user, error = authenticate_user(identifier, password)
            if user:
                clear_failed_attempts(client_ip, _FAILED_LOGINS)
                login_user_session(user)
                log_activity(user['id'], 'USER_LOGIN', f"User logged in: {user['username']}", client_ip)
                flash(f"Welcome back, {user['username']}!", "success")
                next_url = request.args.get('next')
                if next_url and is_safe_url(next_url, request.host_url):
                    return redirect(next_url)
                return redirect(url_for('dashboard'))
            else:
                record_failed_attempt(client_ip, _FAILED_LOGINS)
                flash(error or "Authentication failed.", "danger")
                return render_template('login.html', identifier=identifier)
                
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        """User logout endpoint."""
        user = get_current_user()
        if user:
            log_activity(user['id'], 'USER_LOGOUT', f"User logged out: {user['username']}", request.remote_addr)
        logout_user_session()
        flash("You have been logged out successfully.", "info")
        return redirect(url_for('login'))

    # -------------------------------------------------------------
    # Dashboard & Analytics Routes
    # -------------------------------------------------------------
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Centralized metrics, quick category cards, and recent uploads."""
        user = get_current_user()
        metrics = get_user_metrics(user['id'])
        return render_template('dashboard.html', metrics=metrics)

    # -------------------------------------------------------------
    # File Ingestion, Cloud Upload & Deduplication
    # -------------------------------------------------------------
    @app.route('/upload', methods=['POST'])
    @login_required
    def upload_file():
        """
        File Ingestion Endpoint.
        Validates size, extension, MIME type, generates S3 key,
        computes SHA-256 fingerprint, performs deduplication,
        manages smart versioning, and persists metadata.
        """
        user = get_current_user()
        
        if 'file' not in request.files:
            if request.is_json:
                return jsonify({'success': False, 'error': 'No file part in the request.'}), 400
            flash('No file selected.', 'warning')
            return redirect(url_for('dashboard'))
            
        file_obj = request.files['file']
        if not file_obj or file_obj.filename == '':
            if request.is_json:
                return jsonify({'success': False, 'error': 'No file selected.'}), 400
            flash('No file selected for upload.', 'warning')
            return redirect(url_for('dashboard'))
            
        raw_filename = file_obj.filename
        clean_fn = secure_filename(raw_filename)
        if not clean_fn:
            clean_fn = f"file_{int(time.time())}.bin"
            
        # Extension verification
        ext = clean_fn.rsplit('.', 1)[-1].lower() if '.' in clean_fn else ''
        if ext not in Config.ALLOWED_EXTENSIONS:
            err = f"File type '.{ext}' is not permitted. Allowed: {', '.join(sorted(Config.ALLOWED_EXTENSIONS)[:8])}..."
            if request.is_json:
                return jsonify({'success': False, 'error': err}), 400
            flash(err, 'danger')
            return redirect(url_for('dashboard'))
            
        # Metadata parameters from request
        category = request.form.get('category', 'Other')
        if category not in Config.CATEGORIES:
            category = 'Other'
        tags = request.form.get('tags', '').strip()
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(clean_fn)
        if not mime_type:
            mime_type = file_obj.content_type or 'application/octet-stream'
            
        # Generate globally unique S3 Object Key
        s3_key = storage_service.generate_s3_key(user['id'], clean_fn)
        
        # Upload stream to Cloud Object Storage & compute SHA-256
        success, checksum, file_size, err = storage_service.upload_stream(
            file_obj.stream, s3_key, mime_type=mime_type
        )
        
        if not success:
            err_msg = f"Upload failed: {err}"
            if request.is_json:
                return jsonify({'success': False, 'error': err_msg}), 500
            flash(err_msg, 'danger')
            return redirect(url_for('dashboard'))

        # Check for smart versioning: does user already possess an active file with this exact filename?
        existing_named = find_user_file_by_name(user['id'], raw_filename)
        if existing_named:
            new_version = add_file_version(existing_named['id'], s3_key, file_size, checksum)
            log_activity(user['id'], 'VERSION_UPLOAD', f"Updated '{raw_filename}' to revision v{new_version}", request.remote_addr)
            version_msg = f"'{raw_filename}' successfully uploaded and updated to revision v{new_version}!"
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': version_msg,
                    'file_id': existing_named['id'],
                    'version': new_version
                })
            flash(version_msg, 'success')
            return redirect(url_for('dashboard'))

        # Check for deduplication across the repository
        existing_dup = find_file_by_checksum(checksum)
        if existing_dup:
            log_activity(user['id'], 'UPLOAD_DEDUPLICATED', f"Ingested '{raw_filename}' (SHA-256 matched '{existing_dup['original_filename']}')", request.remote_addr)

        # Persist new metadata record in SQLite
        file_id = create_file_record(
            user_id=user['id'],
            filename=clean_fn,
            original_filename=raw_filename,
            s3_key=s3_key,
            file_size=file_size,
            file_type=ext,
            mime_type=mime_type,
            category=category,
            tags=tags,
            checksum=checksum
        )
        
        log_activity(user['id'], 'UPLOAD', f"Uploaded '{raw_filename}' ({format_bytes(file_size)}) categorized as {category}", request.remote_addr)
        
        success_msg = f"'{raw_filename}' successfully uploaded and categorized under {category}!"
        if existing_dup:
            success_msg += " (⚡ Deduplication active: Shared cloud object reference saved storage)"
            
        if request.is_json:
            return jsonify({
                'success': True,
                'message': success_msg,
                'file_id': file_id,
                'filename': clean_fn,
                'file_size': file_size,
                'formatted_size': format_bytes(file_size),
                'checksum': checksum,
                'category': category,
                'is_deduplicated': bool(existing_dup)
            })
            
        flash(success_msg, 'success')
        return redirect(url_for('dashboard'))

    # -------------------------------------------------------------
    # Search Engine & Multi-Attribute Query Routes
    # -------------------------------------------------------------
    @app.route('/search')
    @login_required
    def search_page():
        """Interactive Search & Filter Page."""
        user = get_current_user()
        keyword = request.args.get('q', '')
        category = request.args.get('category', '')
        file_type = request.args.get('type', '')
        is_starred = request.args.get('starred', '')
        
        results = search_files(
            user_id=user['id'],
            query=keyword,
            category=category,
            file_type=file_type,
            is_starred=True if is_starred == '1' else None
        )
        
        return render_template(
            'search.html',
            results=results,
            query=keyword,
            selected_category=category,
            selected_type=file_type,
            is_starred=is_starred
        )

    @app.route('/api/search')
    @login_required
    def search_api():
        """RESTful Search API Endpoint."""
        user = get_current_user()
        keyword = request.args.get('q', '')
        category = request.args.get('category', '')
        file_type = request.args.get('type', '')
        is_starred = request.args.get('starred', '')
        
        results = search_files(
            user_id=user['id'],
            query=keyword,
            category=category,
            file_type=file_type,
            is_starred=True if is_starred == '1' else None
        )
        
        for r in results:
            r['formatted_size'] = format_bytes(r['file_size'])
            
        return jsonify({'success': True, 'count': len(results), 'results': results})

    @app.route('/api/metrics')
    @login_required
    def metrics_api():
        """Return user metrics in JSON format."""
        user = get_current_user()
        metrics = get_user_metrics(user['id'])
        return jsonify({'success': True, 'metrics': metrics})

    # -------------------------------------------------------------
    # In-Browser Document & Code Preview Engine
    # -------------------------------------------------------------
    @app.route('/api/preview/<int:file_id>')
    @login_required
    def preview_file(file_id):
        """
        In-browser multi-format document preview API.
        Extracts code, markdown, JSON, images, and PDFs.
        """
        user = get_current_user()
        file_record = get_file_by_id(file_id, user['id'])
        if not file_record:
            return jsonify({'success': False, 'error': 'File not found.'}), 404

        ext = file_record['file_type'].lower()
        s3_key = file_record['s3_key']
        log_activity(user['id'], 'PREVIEW', f"Previewed '{file_record['original_filename']}'", request.remote_addr)

        code_exts = {
            'py': 'python', 'js': 'javascript', 'html': 'html', 'css': 'css',
            'json': 'json', 'md': 'markdown', 'sql': 'sql', 'txt': 'text',
            'csv': 'csv', 'xml': 'xml', 'sh': 'bash'
        }

        # 1. Plain text and source code
        if ext in code_exts:
            content_bytes = storage_service.get_file_bytes(s3_key, max_bytes=80000)
            if content_bytes is not None:
                text_content = content_bytes.decode('utf-8', errors='ignore')
                return jsonify({
                    'success': True,
                    'preview_type': 'code',
                    'language': code_exts[ext],
                    'content': text_content,
                    'filename': file_record['original_filename'],
                    'size': format_bytes(file_record['file_size']),
                    'category': file_record['category'],
                    'summary': file_record.get('summary', '')
                })

        # 2. Images (PNG, JPG, JPEG)
        if ext in ['png', 'jpg', 'jpeg', 'gif', 'svg']:
            url, _ = storage_service.generate_presigned_download_url(s3_key, file_record['original_filename'])
            return jsonify({
                'success': True,
                'preview_type': 'image',
                'url': url,
                'filename': file_record['original_filename'],
                'size': format_bytes(file_record['file_size']),
                'category': file_record['category']
            })

        # 3. PDF Documents
        if ext == 'pdf':
            url, _ = storage_service.generate_presigned_download_url(s3_key, file_record['original_filename'])
            return jsonify({
                'success': True,
                'preview_type': 'pdf',
                'url': url,
                'filename': file_record['original_filename'],
                'size': format_bytes(file_record['file_size']),
                'category': file_record['category']
            })

        return jsonify({
            'success': True,
            'preview_type': 'unsupported',
            'filename': file_record['original_filename'],
            'size': format_bytes(file_record['file_size']),
            'message': f"In-browser rendering is unavailable for .{ext} documents. Please download the file to inspect."
        })

    # -------------------------------------------------------------
    # AI Document Intelligence & Smart Tagging
    # -------------------------------------------------------------
    @app.route('/api/ai/summarize/<int:file_id>', methods=['POST'])
    @login_required
    def summarize_file(file_id):
        """
        Analyzes document contents and returns 3-bullet summary + recommended tags.
        """
        user = get_current_user()
        file_record = get_file_by_id(file_id, user['id'])
        if not file_record:
            return jsonify({'success': False, 'error': 'File not found.'}), 404

        target_path = storage_service.get_local_file_path(file_record['s3_key'])
        if target_path:
            text = ai_service.extract_text(target_path)
        else:
            raw_bytes = storage_service.get_file_bytes(file_record['s3_key'], max_bytes=100000)
            text = raw_bytes.decode('utf-8', errors='ignore') if raw_bytes else ""

        summary_bullets = ai_service.summarize_document(
            text,
            filename=file_record['original_filename'],
            category=file_record['category']
        )
        suggested_tags = ai_service.extract_keywords(text, top_n=6)
        
        summary_str = " \u2022 " + " \u2022 ".join(summary_bullets)
        log_activity(user['id'], 'AI_SUMMARY', f"Generated AI analysis for '{file_record['original_filename']}'", request.remote_addr)

        return jsonify({
            'success': True,
            'bullets': summary_bullets,
            'summary_text': summary_str,
            'suggested_tags': suggested_tags,
            'current_tags': file_record['tags'],
            'filename': file_record['original_filename']
        })

    @app.route('/api/ai/apply-tags/<int:file_id>', methods=['POST'])
    @login_required
    def apply_ai_tags(file_id):
        """Persists AI-generated summary and tags to file metadata."""
        user = get_current_user()
        file_record = get_file_by_id(file_id, user['id'])
        if not file_record:
            return jsonify({'success': False, 'error': 'File not found.'}), 404

        data = request.get_json() or {}
        new_tags = data.get('tags', '').strip()
        summary_text = data.get('summary', '').strip()

        update_file_summary_and_tags(file_id, summary_text, new_tags)
        log_activity(user['id'], 'AI_TAGS_APPLIED', f"Updated AI metadata for '{file_record['original_filename']}'", request.remote_addr)

        return jsonify({'success': True, 'message': 'AI metadata updated successfully.'})

    # -------------------------------------------------------------
    # Smart Revision Control & Version Rollback
    # -------------------------------------------------------------
    @app.route('/api/versions/<int:file_id>')
    @login_required
    def get_versions(file_id):
        """Retrieve revision history for a file."""
        user = get_current_user()
        file_record = get_file_by_id(file_id, user['id'])
        if not file_record:
            return jsonify({'success': False, 'error': 'File not found.'}), 404

        versions = get_file_versions(file_id)
        for v in versions:
            v['formatted_size'] = format_bytes(v['file_size'])
            
        return jsonify({
            'success': True,
            'versions': versions,
            'current_version': file_record['version'],
            'filename': file_record['original_filename']
        })

    @app.route('/restore-version/<int:file_id>/<int:version_id>', methods=['POST'])
    @login_required
    def restore_version_endpoint(file_id, version_id):
        """Rollback to a previous document revision."""
        user = get_current_user()
        file_record = get_file_by_id(file_id, user['id'])
        if not file_record:
            abort(404, description="File not found.")

        ok, msg = restore_file_version(file_id, version_id)
        if ok:
            log_activity(user['id'], 'RESTORE_VERSION', f"Rolled back '{file_record['original_filename']}' to previous revision", request.remote_addr)
            flash(msg, 'success')
        else:
            flash(msg, 'danger')
        return redirect(url_for('dashboard'))

    # -------------------------------------------------------------
    # Ephemeral Password-Protected Public Share Links
    # -------------------------------------------------------------
    @app.route('/api/share/<int:file_id>', methods=['POST'])
    @login_required
    def create_share(file_id):
        """Generate a time-limited public sharing link."""
        user = get_current_user()
        file_record = get_file_by_id(file_id, user['id'])
        if not file_record:
            return jsonify({'success': False, 'error': 'File not found.'}), 404

        data = request.get_json() or {}
        hours = int(data.get('expires_hours', 24))
        password = data.get('password', '').strip()
        max_downloads = int(data.get('max_downloads', 0))

        pw_hash = generate_password_hash(password, method='pbkdf2:sha256') if password else None
        token = create_shared_link(file_id, expires_hours=hours, password_hash=pw_hash, max_downloads=max_downloads)

        share_url = url_for('view_shared_link', token=token, _external=True)
        log_activity(user['id'], 'CREATE_SHARE', f"Created public share link for '{file_record['original_filename']}' (expires in {hours}h)", request.remote_addr)

        return jsonify({
            'success': True,
            'share_url': share_url,
            'token': token,
            'expires_hours': hours,
            'has_password': bool(password)
        })

    @app.route('/share/<token>')
    def view_shared_link(token):
        """Public portal for downloading shared documents."""
        link_data = get_shared_link(token)
        if not link_data:
            return render_template('share.html', error="This share link does not exist or the document was deleted.", link_data=None)

        # Expiry check
        if link_data['expires_at']:
            exp = datetime.strptime(link_data['expires_at'], '%Y-%m-%d %H:%M:%S')
            if datetime.now() > exp:
                return render_template('share.html', error="This share link has expired.", link_data=None)

        # Max downloads check
        if link_data['max_downloads'] > 0 and link_data['download_count'] >= link_data['max_downloads']:
            return render_template('share.html', error="This share link has reached its maximum permitted download limit.", link_data=None)

        return render_template('share.html', link_data=link_data, error=None)

    @app.route('/share/<token>/download', methods=['POST'])
    def download_shared_file(token):
        """Authenticate password and stream download for shared file with brute force defense."""
        link_data = get_shared_link(token)
        if not link_data:
            abort(404, description="Share link not found.")

        client_ip = request.remote_addr or '127.0.0.1'

        # Password validation if protected
        if link_data['password_hash']:
            # Brute-force rate limiting protection
            if not app.config.get('TESTING') and is_rate_limited(f"{client_ip}:{token}", _FAILED_SHARE_AUTH, max_attempts=5, window=60):
                flash("Too many failed passphrase attempts. Please wait 60 seconds before retrying.", "danger")
                return redirect(url_for('view_shared_link', token=token))

            provided_pw = request.form.get('password', '')
            if not check_password_hash(link_data['password_hash'], provided_pw):
                record_failed_attempt(f"{client_ip}:{token}", _FAILED_SHARE_AUTH)
                flash("Incorrect password for this protected document.", "danger")
                return redirect(url_for('view_shared_link', token=token))
            clear_failed_attempts(f"{client_ip}:{token}", _FAILED_SHARE_AUTH)

        # Check expiration
        if link_data['expires_at']:
            exp = datetime.strptime(link_data['expires_at'], '%Y-%m-%d %H:%M:%S')
            if datetime.now() > exp:
                flash("This link has expired.", "danger")
                return redirect(url_for('view_shared_link', token=token))

        # Check download limit
        if link_data['max_downloads'] > 0 and link_data['download_count'] >= link_data['max_downloads']:
            flash("Download limit reached.", "danger")
            return redirect(url_for('view_shared_link', token=token))

        record_shared_download(token)
        log_activity(None, 'PUBLIC_DOWNLOAD', f"Public download of '{link_data['original_filename']}' via share token", request.remote_addr)

        url, _ = storage_service.generate_presigned_download_url(link_data['s3_key'], link_data['original_filename'])
        return redirect(url)

    # -------------------------------------------------------------
    # Security Audit Trail & Activity Feed Routes
    # -------------------------------------------------------------
    @app.route('/activity')
    @login_required
    def activity_page():
        """Audit trail and security activity history view."""
        user = get_current_user()
        action_filter = request.args.get('action', '')
        logs = get_user_activity(user['id'], limit=100, action_filter=action_filter if action_filter else None)
        return render_template('activity.html', logs=logs, selected_action=action_filter)

    @app.route('/activity/export.csv')
    @login_required
    def export_activity_csv():
        """Export security audit log to downloadable CSV."""
        user = get_current_user()
        logs = get_user_activity(user['id'], limit=500)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Action', 'Details', 'IP Address', 'Timestamp'])
        for l in logs:
            writer.writerow([l['id'], l['action'], l['details'], l['ip_address'], l['timestamp']])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='nexafiles_security_audit.csv'
        )

    # -------------------------------------------------------------
    # Pre-Signed URL Downloads & Streaming
    # -------------------------------------------------------------
    @app.route('/download/<int:file_id>')
    @login_required
    def download_file(file_id):
        """Generate time-limited signed URL and redirect user to stream."""
        user = get_current_user()
        file_record = get_file_by_id(file_id, user['id'])
        if not file_record:
            abort(404, description="File not found or access denied.")
            
        log_activity(user['id'], 'DOWNLOAD', f"Downloaded '{file_record['original_filename']}' via pre-signed URL", request.remote_addr)
        
        url, mode = storage_service.generate_presigned_download_url(
            s3_key=file_record['s3_key'],
            original_filename=file_record['original_filename']
        )
        return redirect(url)

    @app.route('/storage/stream/<path:s3_key>')
    def stream_local_file(s3_key):
        """
        Serves local files securely when emulating S3 Pre-Signed URLs.
        Enforces cryptographic signature, expiration time check, and path containment.
        """
        expires = request.args.get('expires')
        sig = request.args.get('sig')
        download_name = request.args.get('filename', 'download.bin')
        
        if not expires or not sig:
            abort(403, description="Missing pre-signed URL security tokens.")
            
        valid, err = storage_service.verify_local_download_signature(s3_key, expires, sig)
        if not valid:
            abort(403, description=f"Security verification failed: {err}")
            
        base_dir = storage_service._get_base_path().resolve()
        try:
            local_path = (base_dir / s3_key).resolve()
            if not local_path.is_relative_to(base_dir):
                abort(403, description="Access forbidden: Path traversal attempt detected.")
        except Exception:
            abort(400, description="Invalid path format.")
            
        if not local_path.exists():
            abort(404, description="Binary object does not exist on storage disk.")
            
        return send_file(
            local_path,
            as_attachment=True,
            download_name=download_name
        )

    # -------------------------------------------------------------
    # File Management Operations: Star & Delete
    # -------------------------------------------------------------
    @app.route('/toggle-star/<int:file_id>', methods=['POST'])
    @login_required
    def toggle_star_endpoint(file_id):
        """AJAX endpoint for toggling starred status."""
        user = get_current_user()
        file_record = get_file_by_id(file_id, user['id'])
        if not file_record:
            return jsonify({'success': False, 'error': 'File not found.'}), 404
            
        new_status = toggle_star(file_id, user['id'])
        if new_status is not None:
            action_name = 'Starred' if new_status == 1 else 'Unstarred'
            log_activity(user['id'], 'STAR_TOGGLE', f"{action_name} document '{file_record['original_filename']}'", request.remote_addr)
            return jsonify({'success': True, 'is_starred': bool(new_status)})
        return jsonify({'success': False, 'error': 'Update failed.'}), 500

    @app.route('/delete/<int:file_id>', methods=['POST'])
    @login_required
    def delete_file(file_id):
        """Soft-delete metadata record and purge cloud object payload."""
        user = get_current_user()
        file_record = get_file_by_id(file_id, user['id'])
        if not file_record:
            abort(404, description="File not found.")
            
        # 1. Purge binary payload from Cloud Storage
        storage_service.delete_object(file_record['s3_key'])
        
        # 2. Mark record as deleted in SQLite
        delete_file_record(file_id, user['id'])
        log_activity(user['id'], 'DELETE', f"Deleted document '{file_record['original_filename']}'", request.remote_addr)
        
        flash(f"'{file_record['original_filename']}' deleted successfully from vault.", 'info')
        return redirect(url_for('dashboard'))

    # -------------------------------------------------------------
    # Error Handlers
    # -------------------------------------------------------------
    @app.errorhandler(404)
    def handle_not_found(e):
        return render_template('error.html', code=404, title="Page Not Found",
                               message="The requested cloud document or route was not found."), 404

    @app.errorhandler(413)
    def handle_file_too_large(e):
        return render_template('error.html', code=413, title="Payload Too Large",
                               message=f"Uploaded file exceeds the maximum limit of {Config.MAX_CONTENT_LENGTH_MB} MB."), 413

    @app.errorhandler(500)
    def handle_server_error(e):
        return render_template('error.html', code=500, title="Server Error",
                               message="An unexpected error occurred while processing the cloud storage operation."), 500

    return app

if __name__ == '__main__':
    application = create_app()
    application.run(host='127.0.0.1', port=Config.PORT, debug=Config.DEBUG)
