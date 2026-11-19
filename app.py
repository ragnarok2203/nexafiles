# -*- coding: utf-8 -*-
"""
NexaFiles: Cloud-Based Intelligent File Organization and Retrieval System
Flask Application Factory & HTTP Routing Controllers
"""

import os
import mimetypes
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, send_file, abort
)
from werkzeug.utils import secure_filename
from config import Config
from services.metadata_service import (
    init_db, create_file_record, get_file_by_id,
    delete_file_record, toggle_star, search_files,
    get_user_metrics, format_bytes
)
from services.auth_service import (
    register_user, authenticate_user, login_user_session,
    logout_user_session, get_current_user, login_required
)
from services.storage_service import storage_service

def create_app(test_config=None):
    """Flask Application Factory Pattern."""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Apply configuration
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
        
    # Ensure database tables exist
    with app.app_context():
        init_db()
    
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
        """User registration endpoint."""
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
                flash(msg, "success")
                return redirect(url_for('login'))
            else:
                flash(msg, "danger")
                return render_template('register.html', username=username, email=email)
                
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login authentication endpoint."""
        if get_current_user():
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            identifier = request.form.get('username_or_email')
            password = request.form.get('password')
            
            user, error = authenticate_user(identifier, password)
            if user:
                login_user_session(user)
                flash(f"Welcome back, {user['username']}!", "success")
                next_url = request.args.get('next')
                return redirect(next_url or url_for('dashboard'))
            else:
                flash(error or "Authentication failed.", "danger")
                return render_template('login.html', identifier=identifier)
                
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        """User logout endpoint."""
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
    # File Ingestion & Cloud Upload
    # -------------------------------------------------------------
    @app.route('/upload', methods=['POST'])
    @login_required
    def upload_file():
        """
        File Ingestion Endpoint.
        Validates size, extension, MIME type, generates S3 key,
        computes SHA-256 fingerprint, and persists metadata.
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
            
        # Persist metadata record in SQLite
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
        
        success_msg = f"'{raw_filename}' successfully uploaded and categorized under {category}!"
        if request.is_json:
            return jsonify({
                'success': True,
                'message': success_msg,
                'file_id': file_id,
                'filename': clean_fn,
                'file_size': file_size,
                'formatted_size': format_bytes(file_size),
                'checksum': checksum,
                'category': category
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
            keyword=keyword,
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
    def api_search():
        """JSON endpoint for dynamic client-side live search."""
        user = get_current_user()
        keyword = request.args.get('q', '')
        category = request.args.get('category', '')
        file_type = request.args.get('type', '')
        is_starred = request.args.get('starred', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        results = search_files(
            user_id=user['id'],
            keyword=keyword,
            category=category,
            file_type=file_type,
            is_starred=True if is_starred == '1' else None,
            date_from=date_from,
            date_to=date_to
        )
        
        # Attach human-readable formatted sizes
        for r in results:
            r['formatted_size'] = format_bytes(r['file_size'])
            
        return jsonify({'success': True, 'count': len(results), 'results': results})

    # -------------------------------------------------------------
    # Ephemeral Pre-Signed Download URL & Streaming
    # -------------------------------------------------------------
    @app.route('/download/<int:file_id>')
    @login_required
    def download_file(file_id):
        """Generate time-limited signed URL and redirect user to stream."""
        user = get_current_user()
        file_record = get_file_by_id(file_id, user['id'])
        if not file_record:
            abort(404, description="File not found or access denied.")
            
        url, mode = storage_service.generate_presigned_download_url(
            s3_key=file_record['s3_key'],
            original_filename=file_record['original_filename']
        )
        
        # Redirect client directly to the signed URL (S3 bucket or local streaming route)
        return redirect(url)

    @app.route('/storage/stream/<path:s3_key>')
    def stream_local_file(s3_key):
        """
        Serves local files securely when emulating S3 Pre-Signed URLs.
        Enforces cryptographic signature and expiration time check.
        """
        expires = request.args.get('expires')
        sig = request.args.get('sig')
        download_name = request.args.get('filename', 'download.bin')
        
        if not expires or not sig:
            abort(403, description="Missing pre-signed URL security tokens.")
            
        valid, err = storage_service.verify_local_download_signature(s3_key, expires, sig)
        if not valid:
            abort(403, description=f"Security verification failed: {err}")
            
        local_path = storage_service._get_base_path() / s3_key
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
        """Toggle favorite status of a file."""
        user = get_current_user()
        status = toggle_star(file_id, user['id'])
        if status is None:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        return jsonify({'success': True, 'is_starred': status})

    @app.route('/delete/<int:file_id>', methods=['POST'])
    @login_required
    def delete_file(file_id):
        """Delete file record and physical storage object."""
        user = get_current_user()
        s3_key = delete_file_record(file_id, user['id'])
        if not s3_key:
            if request.is_json:
                return jsonify({'success': False, 'error': 'File not found'}), 404
            flash("File not found or access denied.", "danger")
            return redirect(url_for('dashboard'))
            
        # Clean physical storage object
        storage_service.delete_object(s3_key)
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'File deleted successfully.'})
            
        flash("File deleted successfully.", "info")
        return redirect(url_for('dashboard'))

    # -------------------------------------------------------------
    # API & Health Check
    # -------------------------------------------------------------
    @app.route('/api/metrics')
    @login_required
    def api_metrics():
        """Retrieve aggregated user dashboard metrics."""
        user = get_current_user()
        metrics = get_user_metrics(user['id'])
        return jsonify({'success': True, 'metrics': metrics})

    @app.route('/health')
    def health():
        """System health and infrastructure diagnostics endpoint."""
        return jsonify({
            'status': 'healthy',
            'version': '1.0.0',
            'project': 'NexaFiles: Cloud-Based Intelligent File Organization and Retrieval System',
            'storage': storage_service.get_status()
        })

    # -------------------------------------------------------------
    # Custom Error Handlers
    # -------------------------------------------------------------
    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json:
            return jsonify({'success': False, 'error': 'Resource not found'}), 404
        return render_template('error.html', code=404, title="Page Not Found",
                               message="The requested file or resource could not be located."), 404

    @app.errorhandler(413)
    def payload_too_large_error(error):
        msg = f"File exceeds the maximum allowable upload limit of {Config.MAX_CONTENT_LENGTH_MB} MB."
        if request.is_json:
            return jsonify({'success': False, 'error': msg}), 413
        flash(msg, 'danger')
        return redirect(url_for('dashboard'))

    @app.errorhandler(500)
    def internal_server_error(error):
        if request.is_json:
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
        return render_template('error.html', code=500, title="Server Error",
                               message="An unexpected server error occurred. Please try again later."), 500

    return app

if __name__ == '__main__':
    app = create_app()
    print(f"[*] NexaFiles running on http://127.0.0.1:{Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
