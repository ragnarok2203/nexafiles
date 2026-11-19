# -*- coding: utf-8 -*-
"""
Test Cases for Multi-Attribute Search Engine
Corresponds to Table 6.1 (TC-09)
"""

import io

def test_tc09_multi_attribute_search(auth_client):
    """TC-09: Filtering across keywords, categories, and file types."""
    # Seed 3 distinct files
    files = [
        ('machine_learning_paper.pdf', 'Research', 'deeplearning, neuralnet', b'Research paper content'),
        ('lecture1_notes.docx', 'Notes', 'syllabus, cse', b'Lecture notes content'),
        ('database_migration.py', 'Code', 'sql, sqlite', b'print("hello migration")')
    ]
    
    for fn, cat, tags, content in files:
        auth_client.post('/upload', data={
            'file': (io.BytesIO(content), fn),
            'category': cat,
            'tags': tags
        }, content_type='multipart/form-data', follow_redirects=True)
        
    # 1. Search by Keyword 'machine'
    res = auth_client.get('/api/search?q=machine')
    results = res.get_json()['results']
    assert len(results) == 1
    assert 'machine_learning_paper.pdf' in results[0]['filename']
    
    # 2. Search by Category 'Code'
    res = auth_client.get('/api/search?category=Code')
    results = res.get_json()['results']
    assert len(results) == 1
    assert 'database_migration.py' in results[0]['filename']
    
    # 3. Search by File Type 'docx'
    res = auth_client.get('/api/search?type=docx')
    results = res.get_json()['results']
    assert len(results) == 1
    assert 'lecture1_notes.docx' in results[0]['filename']
    
    # 4. Search by Tag 'syllabus'
    res = auth_client.get('/api/search?q=syllabus')
    results = res.get_json()['results']
    assert len(results) == 1
    assert 'lecture1_notes.docx' in results[0]['filename']

def test_metrics_api(auth_client):
    """Verify aggregated metrics endpoint."""
    res = auth_client.get('/api/metrics')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'total_files' in data['metrics']
    assert 'formatted_size' in data['metrics']
    assert 'categories' in data['metrics']
