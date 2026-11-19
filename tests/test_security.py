# -*- coding: utf-8 -*-
"""
Security Verification Suite for NexaFiles:
- SEC-01: HTTP Security Headers Enforcement (OWASP A05)
- SEC-02: Session Cookie Security Flags (HttpOnly, SameSite) (OWASP A02/A07)
- SEC-03: Path Traversal Containment (OWASP A01)
- SEC-04: Open Redirect Defense on Login (OWASP A01 / CWE-601)
- SEC-05: IDOR Access Control Boundary Isolation (OWASP A01)
- SEC-06: Brute-Force Rate Limiter Functional Validation (OWASP A04)
"""

import io
from services.metadata_service import create_file_record
from services.storage_service import storage_service
from app import is_rate_limited, record_failed_attempt, clear_failed_attempts, is_safe_url

def test_sec01_http_security_headers(client):
    """SEC-01: Response contains OWASP recommended security headers."""
    response = client.get('/login')
    assert response.status_code == 200
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert response.headers.get('X-XSS-Protection') == '1; mode=block'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert 'Content-Security-Policy' in response.headers
    assert "default-src 'self'" in response.headers['Content-Security-Policy']
    assert 'Permissions-Policy' in response.headers

def test_sec02_session_cookie_flags(client):
    """SEC-02: Authenticated session cookies enforce HttpOnly and SameSite."""
    res = client.post('/login', data={'username_or_email': 'akshit', 'password': 'password123'})
    set_cookie = res.headers.get('Set-Cookie', '')
    assert 'HttpOnly' in set_cookie
    assert 'SameSite=Lax' in set_cookie

def test_sec03_path_traversal_rejection(client):
    """SEC-03: Attempting path traversal with ../ via local stream route is blocked."""
    response = client.get('/storage/stream/..%2F..%2F..%2Fwindows%2Fwin.ini?expires=9999999999&sig=invalidsig')
    # Must be rejected before or during path verification (400 or 403)
    assert response.status_code in (400, 403, 404)

def test_sec04_open_redirect_defense(client):
    """SEC-04: External open redirect query is neutralized to internal dashboard."""
    response = client.post('/login?next=https://malicious-external-phishing.com', data={
        'username_or_email': 'akshit',
        'password': 'password123'
    }, follow_redirects=False)
    
    assert response.status_code in (302, 307)
    location = response.headers['Location']
    assert not location.startswith('https://malicious-external-phishing.com')
    assert '/dashboard' in location or location.startswith('/')

def test_sec05_idor_boundary_isolation(app, auth_client):
    """SEC-05: User B cannot access, preview, or delete User A's private documents."""
    # User 1 (auth_client) uploads a private document
    upload_res = auth_client.post('/upload', data={
        'file': (io.BytesIO(b"Akshit's confidential personal notes."), 'akshit_private.txt'),
        'category': 'Notes'
    }, content_type='multipart/form-data', follow_redirects=True)
    assert upload_res.status_code == 200

    # Retrieve file ID from search
    search_res = auth_client.get('/api/search?q=akshit_private.txt')
    file_id = search_res.get_json()['results'][0]['id']

    # Create an independent test client for User 2 (attacker)
    attacker_client = app.test_client()
    attacker_client.post('/register', data={
        'username': 'attacker_user',
        'email': 'attacker@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    attacker_client.post('/login', data={'username_or_email': 'attacker_user', 'password': 'password123'}, follow_redirects=True)

    # User 2 attempts to preview User 1's file -> 404 (IDOR blocked)
    prev_res = attacker_client.get(f'/api/preview/{file_id}')
    assert prev_res.status_code == 404

    # User 2 attempts to download User 1's file -> 404 (IDOR blocked)
    dl_res = attacker_client.get(f'/download/{file_id}')
    assert dl_res.status_code == 404

    # User 2 attempts to delete User 1's file -> 404 (IDOR blocked)
    del_res = attacker_client.post(f'/delete/{file_id}')
    assert del_res.status_code == 404

def test_sec06_brute_force_rate_limiter_logic():
    """SEC-06: Unit test for sliding-window rate limiting tracker."""
    tracker = {}
    ip = '192.168.1.100'
    from collections import defaultdict
    tracker = defaultdict(list)

    assert is_rate_limited(ip, tracker, max_attempts=3, window=10) is False
    record_failed_attempt(ip, tracker)
    record_failed_attempt(ip, tracker)
    assert is_rate_limited(ip, tracker, max_attempts=3, window=10) is False

    record_failed_attempt(ip, tracker)
    assert is_rate_limited(ip, tracker, max_attempts=3, window=10) is True

    clear_failed_attempts(ip, tracker)
    assert is_rate_limited(ip, tracker, max_attempts=3, window=10) is False
