# -*- coding: utf-8 -*-
"""
Test Cases for User Registration, Authentication, and Session Security
Corresponds to Table 6.1 (TC-01 to TC-05) in NexaFiles Major Project Report
"""

def test_tc01_user_registration_success(client):
    """TC-01: Valid user registration creates account successfully."""
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'securepassword123',
        'confirm_password': 'securepassword123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Account created successfully" in response.data

def test_tc02_duplicate_user_registration_rejection(client):
    """TC-02: Duplicate username/email registration is rejected."""
    response = client.post('/register', data={
        'username': 'akshit',
        'email': 'akshit@gnauniversity.edu.in',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"already exists" in response.data

def test_tc03_user_login_success(client):
    """TC-03: Valid credentials authenticate and create session."""
    response = client.post('/login', data={
        'username_or_email': 'akshit',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Welcome back, akshit" in response.data
    assert b"Cloud Storage Dashboard" in response.data

def test_tc04_invalid_password_rejection(client):
    """TC-04: Incorrect password fails authentication."""
    response = client.post('/login', data={
        'username_or_email': 'akshit',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data

def test_tc05_unauthorized_access_redirect(client):
    """TC-05: Accessing protected endpoint without session redirects to login."""
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b"Please log in to access this page" in response.data

def test_user_logout(auth_client):
    """Verify logout terminates session."""
    response = auth_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"logged out successfully" in response.data
