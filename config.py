# -*- coding: utf-8 -*-
"""
NexaFiles: Cloud-Based Intelligent File Organization and Retrieval System
Configuration Module
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent

# Check for Vercel Serverless environment
IS_VERCEL = bool(os.getenv('VERCEL') or os.getenv('VERCEL_ENV'))
if IS_VERCEL:
    DATA_DIR = Path('/tmp') / 'data'
    STORAGE_DIR = DATA_DIR / 'storage'
    DATABASE_PATH = DATA_DIR / 'nexafiles.db'
else:
    DATA_DIR = BASE_DIR / 'data'
    STORAGE_DIR = DATA_DIR / 'storage'
    DATABASE_PATH = DATA_DIR / 'nexafiles.db'

# Ensure required runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Load optional .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

class Config:
    """Application configuration parameters."""
    # Cryptographic Session & Token Signing Key
    # Automatically generates a secure random token in production/cloud if not explicitly set
    _env_secret = os.getenv('SECRET_KEY')
    if _env_secret:
        SECRET_KEY = _env_secret
    elif os.getenv('VERCEL') or os.getenv('VERCEL_ENV') or os.getenv('FLASK_ENV') == 'production':
        import secrets
        SECRET_KEY = secrets.token_hex(32)
    else:
        SECRET_KEY = 'nexafiles-dev-secret-key-2026'

    DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
    PORT = int(os.getenv('PORT', 5000))
    
    # Database
    DATABASE = str(DATABASE_PATH)
    
    # Storage settings
    # 's3' uses Amazon Web Services S3 Object Storage via Boto3
    # 'local' emulates cloud object storage locally (no AWS account required)
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'local').lower()
    
    # AWS S3 Cloud Storage Credentials
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'nexafiles-cloud-vault')
    
    # Local Storage Fallback Path
    LOCAL_STORAGE_PATH = str(STORAGE_DIR)
    
    # Security & Upload Limits
    MAX_CONTENT_LENGTH_MB = int(os.getenv('MAX_CONTENT_LENGTH_MB', 50))
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH_MB * 1024 * 1024  # bytes
    PRESIGNED_URL_EXPIRATION = int(os.getenv('PRESIGNED_URL_EXPIRATION', 900))  # seconds (15 min)
    
    # Session Cookie Security Flags
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Automatically enforce HTTPS Secure cookies in production or Vercel
    SESSION_COOKIE_SECURE = (
        IS_VERCEL or 
        os.getenv('FLASK_ENV') == 'production' or 
        os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')
    )
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    # Allowed File Extensions
    ALLOWED_EXTENSIONS = {
        'pdf', 'docx', 'doc', 'txt', 'csv', 'xlsx', 'xls',
        'pptx', 'ppt', 'zip', 'tar', 'gz', 'png', 'jpg', 'jpeg',
        'py', 'js', 'html', 'css', 'json', 'md', 'xml'
    }
    
    # Standard Academic & Professional Document Categories
    CATEGORIES = [
        'Notes',
        'Research',
        'Presentation',
        'Code',
        'Media',
        'Legal',
        'Archive',
        'Other'
    ]

    # Category color badges for UI presentation
    CATEGORY_COLORS = {
        'Notes': 'primary',
        'Research': 'success',
        'Presentation': 'warning',
        'Code': 'info',
        'Media': 'danger',
        'Legal': 'secondary',
        'Archive': 'dark',
        'Other': 'light'
    }
