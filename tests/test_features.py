# -*- coding: utf-8 -*-
"""
Test Cases for NexaFiles Enterprise Features:
- TC-13: In-Browser Document & Code Preview Engine
- TC-14: AI Document Summarization & Smart Tag Extraction
- TC-15: Ephemeral Secure Share Link Generation & Password Verification
- TC-16: Smart Revision Control & Version Rollback
- TC-17: Real-Time Content Deduplication
- TC-18: Security Audit Trail & CSV Export
"""

import io
import json

def test_tc13_in_browser_preview(auth_client):
    """TC-13: Code file preview returns syntax-highlightable text payload."""
    payload = b"def calculate_checksum(data):\n    import hashlib\n    return hashlib.sha256(data).hexdigest()\n"
    res = auth_client.post('/upload', data={
        'file': (io.BytesIO(payload), 'checksum_calc.py'),
        'category': 'Code',
        'tags': 'python, hashing'
    }, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200

    # Search for the created file ID
    search_res = auth_client.get('/api/search?q=checksum_calc')
    file_id = search_res.get_json()['results'][0]['id']

    # Preview API
    prev_res = auth_client.get(f'/api/preview/{file_id}')
    assert prev_res.status_code == 200
    data = prev_res.get_json()
    assert data['success'] is True
    assert data['preview_type'] == 'code'
    assert data['language'] == 'python'
    assert 'def calculate_checksum' in data['content']

def test_tc14_ai_summarization_and_tagging(auth_client):
    """TC-14: AI Document Summarizer produces 3 bullets and extracts smart tags."""
    doc_text = b"Cloud computing provides scalable virtual infrastructure. AWS S3 provides high availability object storage with 99.999999999% durability. Microservices communicate via RESTful APIs and event driven pipelines."
    auth_client.post('/upload', data={
        'file': (io.BytesIO(doc_text), 'cloud_architecture_overview.txt'),
        'category': 'Research',
        'tags': 'cloud'
    }, content_type='multipart/form-data', follow_redirects=True)

    search_res = auth_client.get('/api/search?q=cloud_architecture_overview')
    file_id = search_res.get_json()['results'][0]['id']

    # Call AI Summarizer
    ai_res = auth_client.post(f'/api/ai/summarize/{file_id}')
    assert ai_res.status_code == 200
    ai_data = ai_res.get_json()
    assert ai_data['success'] is True
    assert len(ai_data['bullets']) == 3
    assert len(ai_data['suggested_tags']) > 0

    # Apply AI Tags
    apply_res = auth_client.post(f'/api/ai/apply-tags/{file_id}', json={
        'tags': 'cloud, aws, microservices, architecture',
        'summary': ai_data['summary_text']
    })
    assert apply_res.status_code == 200
    assert apply_res.get_json()['success'] is True

def test_tc15_ephemeral_share_link_and_download(client, auth_client):
    """TC-15: Ephemeral share link generation with password protection and public access."""
    file_payload = b"Top secret exam study guide for EEC401."
    auth_client.post('/upload', data={
        'file': (io.BytesIO(file_payload), 'secret_exam_guide.txt'),
        'category': 'Notes',
        'tags': 'exam, confidential'
    }, content_type='multipart/form-data', follow_redirects=True)

    search_res = auth_client.get('/api/search?q=secret_exam_guide')
    file_id = search_res.get_json()['results'][0]['id']

    # Create password-protected share link (24h, password: 'vaultpass123')
    share_res = auth_client.post(f'/api/share/{file_id}', json={
        'expires_hours': 24,
        'password': 'vaultpass123',
        'max_downloads': 5
    })
    assert share_res.status_code == 200
    share_data = share_res.get_json()
    assert share_data['success'] is True
    token = share_data['token']

    # Public user views the landing page (unauthenticated client)
    portal_res = client.get(f'/share/{token}')
    assert portal_res.status_code == 200
    assert b"secret_exam_guide.txt" in portal_res.data
    assert b"DOCUMENT ACCESS PASSPHRASE" in portal_res.data

    # Incorrect password fails
    fail_res = client.post(f'/share/{token}/download', data={'password': 'wrong'}, follow_redirects=True)
    assert b"Incorrect password" in fail_res.data

    # Correct password downloads
    success_res = client.post(f'/share/{token}/download', data={'password': 'vaultpass123'}, follow_redirects=True)
    assert success_res.status_code == 200
    assert b"Top secret exam study guide" in success_res.data

def test_tc16_smart_versioning_and_rollback(auth_client):
    """TC-16: Uploading duplicate filename creates v2, and rollback restores v1."""
    # Upload Version 1
    v1_content = b"Draft 1: Preliminary project synopsis."
    auth_client.post('/upload', data={
        'file': (io.BytesIO(v1_content), 'synopsis.txt'),
        'category': 'Notes'
    }, content_type='multipart/form-data', follow_redirects=True)

    search_res = auth_client.get('/api/search?q=synopsis.txt')
    file_id = search_res.get_json()['results'][0]['id']

    # Upload Version 2 with same filename
    v2_content = b"Draft 2: Final approved project synopsis with guide signature."
    auth_client.post('/upload', data={
        'file': (io.BytesIO(v2_content), 'synopsis.txt'),
        'category': 'Notes'
    }, content_type='multipart/form-data', follow_redirects=True)

    # Check version history API
    ver_res = auth_client.get(f'/api/versions/{file_id}')
    assert ver_res.status_code == 200
    ver_data = ver_res.get_json()
    assert ver_data['current_version'] == 2
    assert len(ver_data['versions']) == 2

    # Verify downloading currently returns v2
    dl_v2 = auth_client.get(f'/download/{file_id}', follow_redirects=True)
    assert b"Draft 2" in dl_v2.data

    # Roll back to Version 1
    v1_record = [v for v in ver_data['versions'] if v['version_number'] == 1][0]
    restore_res = auth_client.post(f'/restore-version/{file_id}/{v1_record["id"]}', follow_redirects=True)
    assert restore_res.status_code == 200

    # Verify download now returns v1
    dl_restored = auth_client.get(f'/download/{file_id}', follow_redirects=True)
    assert b"Draft 1" in dl_restored.data

def test_tc17_content_deduplication(auth_client):
    """TC-17: Uploading identical payload under different name links shared object."""
    shared_payload = b"Universal physics constants: c = 299792458 m/s, h = 6.626e-34 J*s"
    
    # Ingest first copy
    res1 = auth_client.post('/upload', data={
        'file': (io.BytesIO(shared_payload), 'physics_constants.txt'),
        'category': 'Notes'
    }, content_type='multipart/form-data', follow_redirects=True)
    assert res1.status_code == 200

    # Ingest second copy with different name
    res2 = auth_client.post('/upload', data={
        'file': (io.BytesIO(shared_payload), 'copied_constants.txt'),
        'category': 'Research'
    }, content_type='multipart/form-data', follow_redirects=True)
    assert res2.status_code == 200
    assert b"Deduplication active" in res2.data

def test_tc18_activity_audit_logs_and_csv(auth_client):
    """TC-18: Verify activity logging and CSV audit trail export."""
    # View Activity Log HTML page
    act_res = auth_client.get('/activity')
    assert act_res.status_code == 200
    assert b"Security Audit Trail" in act_res.data
    assert b"UPLOAD" in act_res.data

    # Export CSV
    csv_res = auth_client.get('/activity/export.csv')
    assert csv_res.status_code == 200
    assert csv_res.headers['Content-Type'].startswith('text/csv')
    assert b"Action,Details,IP Address,Timestamp" in csv_res.data
