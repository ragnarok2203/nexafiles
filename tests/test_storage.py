# -*- coding: utf-8 -*-
"""
Test Cases for File Ingestion, Validation, Cloud Storage, and Pre-Signed Downloads
Corresponds to Table 6.1 (TC-06, TC-07, TC-08, TC-10, TC-11, TC-12)
"""

import io
import hashlib

def test_tc06_file_upload_success(auth_client):
    """TC-06: Valid file upload with metadata is accepted."""
    file_content = b"NexaFiles: Cloud-Based Intelligent File Organization and Retrieval System test payload."
    data = {
        'file': (io.BytesIO(file_content), 'cloud_notes.pdf'),
        'category': 'Notes',
        'tags': 'unit1, midsem, cloud'
    }
    
    response = auth_client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b"successfully uploaded" in response.data
    assert b"cloud_notes.pdf" in response.data

def test_tc07_prohibited_extension_rejection(auth_client):
    """TC-07: Prohibited file extension (.exe) is rejected with error."""
    data = {
        'file': (io.BytesIO(b"malicious executable payload"), 'malware.exe'),
        'category': 'Other'
    }
    
    response = auth_client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b"not permitted" in response.data

def test_tc08_checksum_calculation(auth_client):
    """TC-08: SHA-256 fingerprint is calculated and stored correctly."""
    payload = b"Unique content verification string 12345."
    expected_hash = hashlib.sha256(payload).hexdigest()
    
    data = {
        'file': (io.BytesIO(payload), 'checksum_test.txt'),
        'category': 'Code',
        'tags': 'hash, test'
    }
    
    response = auth_client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify through API search
    res = auth_client.get('/api/search?q=checksum_test')
    json_data = res.get_json()
    assert json_data['success'] is True
    assert len(json_data['results']) >= 1
    assert json_data['results'][0]['checksum'] == expected_hash

def test_tc10_presigned_download_url_generation(auth_client):
    """TC-10: Ephemeral signed download token is issued."""
    data = {
        'file': (io.BytesIO(b"Download content sample."), 'sample_download.txt'),
        'category': 'Notes'
    }
    auth_client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    # Get file ID from search
    res = auth_client.get('/api/search?q=sample_download')
    file_id = res.get_json()['results'][0]['id']
    
    # Request download
    download_res = auth_client.get(f'/download/{file_id}', follow_redirects=False)
    assert download_res.status_code in (302, 307)
    assert 'expires=' in download_res.headers['Location'] or 's3.amazonaws.com' in download_res.headers['Location']

def test_tc11_star_toggle(auth_client):
    """TC-11: Toggling favorite star status."""
    data = {
        'file': (io.BytesIO(b"Important research doc."), 'important_doc.pdf'),
        'category': 'Research'
    }
    auth_client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    res = auth_client.get('/api/search?q=important_doc')
    file_id = res.get_json()['results'][0]['id']
    
    # Toggle Star on
    toggle_res = auth_client.post(f'/toggle-star/{file_id}')
    assert toggle_res.get_json()['is_starred'] is True
    
    # Toggle Star off
    toggle_res2 = auth_client.post(f'/toggle-star/{file_id}')
    assert toggle_res2.get_json()['is_starred'] is False

def test_tc12_file_deletion(auth_client):
    """TC-12: Deleting a file removes it from search and repository."""
    data = {
        'file': (io.BytesIO(b"Delete me soon."), 'temporary_file.txt'),
        'category': 'Other'
    }
    auth_client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    res = auth_client.get('/api/search?q=temporary_file')
    file_id = res.get_json()['results'][0]['id']
    
    # Delete file
    del_res = auth_client.post(f'/delete/{file_id}', follow_redirects=True)
    assert del_res.status_code == 200
    assert b"deleted successfully" in del_res.data
    
    # Verify search returns 0 results
    res_after = auth_client.get('/api/search?q=temporary_file')
    assert len(res_after.get_json()['results']) == 0
