# -*- coding: utf-8 -*-
"""
NexaFiles: Metadata Management and Database Modeling Service
Implements SQLite relational persistence, indexing, multi-attribute search queries,
revision version control, ephemeral share links, and security audit logging.
"""

import sqlite3
import uuid
from datetime import datetime, timedelta
from flask import current_app, has_app_context
from config import Config

def get_db_connection(db_path=None):
    """Establish connection to SQLite database with Row mapping enabled."""
    if db_path is None:
        if has_app_context() and current_app.config.get('DATABASE'):
            db_path = current_app.config['DATABASE']
        else:
            db_path = Config.DATABASE
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(db_path=None):
    """Initialize database tables, foreign keys, and indexes if they do not exist."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Table 1: Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table 2: Files Metadata
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            s3_key TEXT UNIQUE NOT NULL,
            file_size INTEGER NOT NULL,
            file_type TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            category TEXT NOT NULL,
            tags TEXT DEFAULT '',
            checksum TEXT NOT NULL,
            is_starred INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            summary TEXT DEFAULT '',
            version INTEGER DEFAULT 1,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Ensure columns exist on legacy instances of files table
    cursor.execute("PRAGMA table_info(files)")
    cols = [r['name'] for r in cursor.fetchall()]
    if 'summary' not in cols:
        cursor.execute("ALTER TABLE files ADD COLUMN summary TEXT DEFAULT ''")
    if 'version' not in cols:
        cursor.execute("ALTER TABLE files ADD COLUMN version INTEGER DEFAULT 1")

    # Table 3: File Versions (Smart Revision Control)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            s3_key TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            checksum TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
        )
    ''')

    # Table 4: Shared Ephemeral Links (Password-Protected & Time-Limited)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shared_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            share_token TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            expires_at TIMESTAMP,
            max_downloads INTEGER DEFAULT 0,
            download_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
        )
    ''')

    # Table 5: Security Activity & Audit Logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            ip_address TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Performance & Foreign Key Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_user ON files(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_category ON files(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_checksum ON files(checksum)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_upload_date ON files(upload_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_file ON file_versions(file_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shared_token ON shared_links(share_token)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_logs(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_action ON activity_logs(action)')
    
    conn.commit()
    conn.close()

def create_file_record(user_id, filename, original_filename, s3_key, file_size, file_type, mime_type, category, tags, checksum, summary=''):
    """Insert a new file metadata record into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO files (
            user_id, filename, original_filename, s3_key,
            file_size, file_type, mime_type, category, tags, checksum, summary, version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    ''', (user_id, filename, original_filename, s3_key, file_size, file_type, mime_type, category, tags, checksum, summary))
    
    file_id = cursor.lastrowid
    
    # Record initial v1 in file_versions
    cursor.execute('''
        INSERT INTO file_versions (file_id, version_number, s3_key, file_size, checksum)
        VALUES (?, 1, ?, ?, ?)
    ''', (file_id, s3_key, file_size, checksum))
    
    conn.commit()
    conn.close()
    return file_id

def find_file_by_checksum(checksum):
    """Find any existing un-deleted file matching the checksum (for deduplication)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM files WHERE checksum = ? AND is_deleted = 0 LIMIT 1', (checksum,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def find_user_file_by_name(user_id, filename):
    """Find user's existing file with the same name (for versioning)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM files WHERE user_id = ? AND original_filename = ? AND is_deleted = 0 LIMIT 1', (user_id, filename))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_file_version(file_id, s3_key, file_size, checksum):
    """Upload a new revision version to an existing file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT version FROM files WHERE id = ?', (file_id,))
    row = cursor.fetchone()
    current_version = row['version'] if row else 1
    new_version = current_version + 1
    
    cursor.execute('''
        UPDATE files 
        SET s3_key = ?, file_size = ?, checksum = ?, version = ?, upload_date = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (s3_key, file_size, checksum, new_version, file_id))
    
    cursor.execute('''
        INSERT INTO file_versions (file_id, version_number, s3_key, file_size, checksum)
        VALUES (?, ?, ?, ?, ?)
    ''', (file_id, new_version, s3_key, file_size, checksum))
    
    conn.commit()
    conn.close()
    return new_version

def get_file_versions(file_id):
    """Retrieve all recorded revisions for a file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM file_versions WHERE file_id = ? ORDER BY version_number DESC
    ''', (file_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def restore_file_version(file_id, version_id):
    """Roll back file to a specific older revision."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM file_versions WHERE id = ? AND file_id = ?', (version_id, file_id))
    ver = cursor.fetchone()
    if not ver:
        conn.close()
        return False, "Version not found."
        
    cursor.execute('''
        UPDATE files
        SET s3_key = ?, file_size = ?, checksum = ?, version = ?
        WHERE id = ?
    ''', (ver['s3_key'], ver['file_size'], ver['checksum'], ver['version_number'], file_id))
    
    conn.commit()
    conn.close()
    return True, f"Successfully restored to version v{ver['version_number']}"

def create_shared_link(file_id, expires_hours=24, password_hash=None, max_downloads=0):
    """Generate ephemeral share link record."""
    share_token = uuid.uuid4().hex
    expires_at = (datetime.now() + timedelta(hours=expires_hours)).strftime('%Y-%m-%d %H:%M:%S') if expires_hours > 0 else None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO shared_links (file_id, share_token, password_hash, expires_at, max_downloads)
        VALUES (?, ?, ?, ?, ?)
    ''', (file_id, share_token, password_hash, expires_at, max_downloads))
    conn.commit()
    conn.close()
    return share_token

def get_shared_link(share_token):
    """Retrieve shared link joined with file info."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, f.original_filename, f.file_size, f.file_type, f.s3_key, f.checksum, f.category
        FROM shared_links s
        JOIN files f ON s.file_id = f.id
        WHERE s.share_token = ? AND f.is_deleted = 0
    ''', (share_token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def record_shared_download(share_token):
    """Increment download counter on shared link."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE shared_links SET download_count = download_count + 1 WHERE share_token = ?', (share_token,))
    conn.commit()
    conn.close()

def update_file_summary_and_tags(file_id, summary, tags):
    """Update AI summary and tags for a file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE files SET summary = ?, tags = ? WHERE id = ?', (summary, tags, file_id))
    conn.commit()
    conn.close()

def log_activity(user_id, action, details, ip_address=''):
    """Record audit log event."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_logs (user_id, action, details, ip_address)
        VALUES (?, ?, ?, ?)
    ''', (user_id, action, details, ip_address))
    conn.commit()
    conn.close()

def get_user_activity(user_id, limit=50, action_filter=None):
    """Retrieve audit history for user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if action_filter:
        cursor.execute('''
            SELECT * FROM activity_logs 
            WHERE (user_id = ? OR user_id IS NULL) AND action = ?
            ORDER BY timestamp DESC LIMIT ?
        ''', (user_id, action_filter, limit))
    else:
        cursor.execute('''
            SELECT * FROM activity_logs 
            WHERE (user_id = ? OR user_id IS NULL)
            ORDER BY timestamp DESC LIMIT ?
        ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_file_by_id(file_id, user_id=None):
    """Retrieve a single active file record by ID, ensuring user boundary."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute('SELECT * FROM files WHERE id = ? AND user_id = ? AND is_deleted = 0', (file_id, user_id))
    else:
        cursor.execute('SELECT * FROM files WHERE id = ? AND is_deleted = 0', (file_id,))
        
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_file_record(file_id, user_id):
    """Mark file as soft-deleted in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE files SET is_deleted = 1 WHERE id = ? AND user_id = ?', (file_id, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def toggle_star(file_id, user_id):
    """Toggle the starred/favorite status of a file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT is_starred FROM files WHERE id = ? AND user_id = ?', (file_id, user_id))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return None
        
    new_status = 0 if row['is_starred'] == 1 else 1
    cursor.execute('UPDATE files SET is_starred = ? WHERE id = ? AND user_id = ?', (new_status, file_id, user_id))
    conn.commit()
    conn.close()
    return new_status

def search_files(user_id, query=None, category=None, file_type=None, is_starred=None):
    """
    Multi-Attribute Search Engine:
    Executes parameterized dynamic SQL queries across filename, category, tags, and type.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = ['SELECT * FROM files WHERE user_id = ? AND is_deleted = 0']
    params = [user_id]
    
    if query and query.strip():
        q = f"%{query.strip().lower()}%"
        sql.append('AND (LOWER(original_filename) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(category) LIKE ? OR LOWER(summary) LIKE ?)')
        params.extend([q, q, q, q])
        
    if category and category.strip():
        sql.append('AND category = ?')
        params.append(category.strip())
        
    if file_type and file_type.strip():
        sql.append('AND LOWER(file_type) = ?')
        params.append(file_type.strip().lower())
        
    if is_starred in ('1', 1, True):
        sql.append('AND is_starred = 1')
        
    sql.append('ORDER BY upload_date DESC')
    
    cursor.execute(' '.join(sql), params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_metrics(user_id):
    """Compute aggregate storage telemetry for dashboard presentation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(*) as total_files,
            COALESCE(SUM(file_size), 0) as total_bytes,
            SUM(CASE WHEN is_starred = 1 THEN 1 ELSE 0 END) as total_starred
        FROM files
        WHERE user_id = ? AND is_deleted = 0
    ''', (user_id,))
    summary = cursor.fetchone()
    
    cursor.execute('''
        SELECT category, COUNT(*) as count, COALESCE(SUM(file_size), 0) as bytes
        FROM files
        WHERE user_id = ? AND is_deleted = 0
        GROUP BY category
    ''', (user_id,))
    cat_rows = cursor.fetchall()
    category_metrics = {r['category']: {'count': r['count'], 'bytes': r['bytes']} for r in cat_rows}
    
    cursor.execute('''
        SELECT * FROM files
        WHERE user_id = ? AND is_deleted = 0
        ORDER BY upload_date DESC LIMIT 5
    ''', (user_id,))
    recent_rows = cursor.fetchall()
    
    conn.close()
    
    total_bytes = summary['total_bytes'] or 0
    formatted_size = format_bytes(total_bytes)
    
    return {
        'total_files': summary['total_files'] or 0,
        'total_bytes': total_bytes,
        'formatted_size': formatted_size,
        'total_starred': summary['total_starred'] or 0,
        'categories': category_metrics,
        'recent_files': [dict(r) for r in recent_rows]
    }

def format_bytes(byte_count):
    """Format numeric byte count into human-readable string (KB, MB, GB)."""
    if byte_count < 1024:
        return f"{byte_count} B"
    elif byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KB"
    elif byte_count < 1024 * 1024 * 1024:
        return f"{byte_count / (1024 * 1024):.2f} MB"
    else:
        return f"{byte_count / (1024 * 1024 * 1024):.2f} GB"
