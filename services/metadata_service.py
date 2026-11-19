# -*- coding: utf-8 -*-
"""
NexaFiles: Metadata Management and Database Modeling Service
Implements SQLite relational persistence, indexing, and multi-attribute search queries.
"""

import sqlite3
from datetime import datetime
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
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Create Performance Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_user ON files(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_category ON files(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_checksum ON files(checksum)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_upload_date ON files(upload_date)')
    
    conn.commit()
    conn.close()

def create_file_record(user_id, filename, original_filename, s3_key, file_size, file_type, mime_type, category, tags, checksum):
    """Insert a new file metadata record into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO files (
            user_id, filename, original_filename, s3_key, file_size,
            file_type, mime_type, category, tags, checksum
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, filename, original_filename, s3_key, file_size,
        file_type, mime_type, category, tags, checksum
    ))
    
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id

def get_file_by_id(file_id, user_id):
    """Retrieve metadata for a specific file owned by the user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM files
        WHERE id = ? AND user_id = ? AND is_deleted = 0
    ''', (file_id, user_id))
    
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_file_record(file_id, user_id):
    """Soft-delete a file record from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Retrieve s3_key first so caller can delete physical binary
    cursor.execute('SELECT s3_key FROM files WHERE id = ? AND user_id = ? AND is_deleted = 0', (file_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    s3_key = row['s3_key']
    cursor.execute('UPDATE files SET is_deleted = 1 WHERE id = ? AND user_id = ?', (file_id, user_id))
    conn.commit()
    conn.close()
    return s3_key

def toggle_star(file_id, user_id):
    """Toggle the starred/favorite status of a file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT is_starred FROM files WHERE id = ? AND user_id = ? AND is_deleted = 0', (file_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    new_status = 0 if row['is_starred'] == 1 else 1
    cursor.execute('UPDATE files SET is_starred = ? WHERE id = ? AND user_id = ?', (new_status, file_id, user_id))
    conn.commit()
    conn.close()
    return bool(new_status)

def search_files(user_id, keyword=None, category=None, file_type=None, is_starred=None, date_from=None, date_to=None, sort_by='upload_date', sort_order='DESC'):
    """
    Execute dynamic multi-attribute search across file metadata.
    Enforces parameterized queries to prevent SQL injection.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM files WHERE user_id = ? AND is_deleted = 0"
    params = [user_id]
    
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query += " AND (filename LIKE ? OR original_filename LIKE ? OR tags LIKE ?)"
        params.extend([kw, kw, kw])
        
    if category and category.strip() and category != 'All':
        query += " AND category = ?"
        params.append(category.strip())
        
    if file_type and file_type.strip() and file_type != 'All':
        query += " AND file_type = ?"
        params.append(file_type.strip().lower())
        
    if is_starred is not None and is_starred != '':
        query += " AND is_starred = ?"
        params.append(1 if is_starred else 0)
        
    if date_from and date_from.strip():
        query += " AND date(upload_date) >= date(?)"
        params.append(date_from.strip())
        
    if date_to and date_to.strip():
        query += " AND date(upload_date) <= date(?)"
        params.append(date_to.strip())
        
    allowed_sort_cols = {'upload_date', 'filename', 'file_size', 'category'}
    sort_col = sort_by if sort_by in allowed_sort_cols else 'upload_date'
    sort_dir = 'ASC' if str(sort_order).upper() == 'ASC' else 'DESC'
    
    query += f" ORDER BY {sort_col} {sort_dir} LIMIT 200"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

def get_user_metrics(user_id):
    """Aggregate storage consumption and document statistics for user dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total Files & Total Storage Size
    cursor.execute('''
        SELECT COUNT(*) as total_files, COALESCE(SUM(file_size), 0) as total_bytes,
               SUM(CASE WHEN is_starred = 1 THEN 1 ELSE 0 END) as total_starred
        FROM files
        WHERE user_id = ? AND is_deleted = 0
    ''', (user_id,))
    summary = cursor.fetchone()
    
    # 2. Count by Category
    cursor.execute('''
        SELECT category, COUNT(*) as count, COALESCE(SUM(file_size), 0) as bytes
        FROM files
        WHERE user_id = ? AND is_deleted = 0
        GROUP BY category
    ''', (user_id,))
    cat_rows = cursor.fetchall()
    category_metrics = {r['category']: {'count': r['count'], 'bytes': r['bytes']} for r in cat_rows}
    
    # 3. Recent 5 Files
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
