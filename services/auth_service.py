# -*- coding: utf-8 -*-
"""
NexaFiles: Authentication and Session Security Service
Implements password hashing, user registration, authentication, and session control.
"""

from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from services.metadata_service import get_db_connection

def register_user(username, email, password):
    """
    Register a new user account with hashed password.
    Returns (success: bool, message: str, user_id: int | None).
    """
    username = username.strip() if username else ''
    email = email.strip().lower() if email else ''
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long.", None
    if '@' not in email or '.' not in email:
        return False, "Please enter a valid email address.", None
    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", None
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if username or email already exists
    cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return False, "A user with this username or email already exists.", None
        
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    try:
        cursor.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        user_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        return False, f"Database error during registration: {str(e)}", None
        
    conn.close()
    return True, "Account created successfully! Please log in.", user_id

def authenticate_user(username_or_email, password):
    """
    Authenticate user credentials against stored hash.
    Returns (user_dict | None, error_message: str | None).
    """
    identifier = username_or_email.strip() if username_or_email else ''
    if not identifier or not password:
        return None, "Please provide both username/email and password."
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT * FROM users WHERE username = ? OR email = ?',
        (identifier, identifier.lower())
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return None, "Invalid username or password."
        
    if not check_password_hash(user['password_hash'], password):
        return None, "Invalid username or password."
        
    return dict(user), None

def login_user_session(user_dict):
    """Store authenticated user session context."""
    session.clear()
    session['user_id'] = user_dict['id']
    session['username'] = user_dict['username']
    session['email'] = user_dict['email']

def logout_user_session():
    """Clear user session context."""
    session.clear()

def get_current_user():
    """Retrieve the currently authenticated user dictionary from session."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return {
        'id': user_id,
        'username': session.get('username'),
        'email': session.get('email')
    }

def login_required(f):
    """Decorator to enforce authentication on protected endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
