# -*- coding: utf-8 -*-
"""
Pytest Fixtures for NexaFiles Automated Testing Suite
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from services.metadata_service import init_db
from services.auth_service import register_user

@pytest.fixture
def app():
    """Create an isolated test application instance with temporary database."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    storage_temp = tempfile.mkdtemp()
    
    test_config = {
        'TESTING': True,
        'DATABASE': db_path,
        'STORAGE_MODE': 'local',
        'LOCAL_STORAGE_PATH': storage_temp,
        'SECRET_KEY': 'test-secret-key-12345',
        'WTF_CSRF_ENABLED': False
    }
    
    app = create_app(test_config)
    
    with app.app_context():
        # Pre-seed a test user (harleen / password123)
        register_user('harleen', 'harleen@gnauniversity.edu.in', 'password123')
        
    yield app
    
    # Teardown
    os.close(db_fd)
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except OSError:
            pass
    import shutil
    shutil.rmtree(storage_temp, ignore_errors=True)

@pytest.fixture
def client(app):
    """Test client for HTTP request dispatching."""
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """Pre-authenticated test client."""
    client.post('/login', data={
        'username_or_email': 'harleen',
        'password': 'password123'
    }, follow_redirects=True)
    return client
