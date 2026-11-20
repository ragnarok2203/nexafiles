# -*- coding: utf-8 -*-
"""
NexaFiles Vercel Serverless Function Entry Point
Initializes the Flask application and seeds demo state for cloud serverless execution.
"""

import sys
from pathlib import Path

# Add project root directory to system search path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from run import seed_demo_environment

# Initialize production Flask application instance for Vercel WSGI
app = create_app()

# Auto-seed the demo environment (account: akshit / password123 + sample documents)
try:
    with app.app_context():
        seed_demo_environment()
except Exception as e:
    print(f"[Vercel Initialization] Serverless environment notice: {e}")
