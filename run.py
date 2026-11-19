# -*- coding: utf-8 -*-
"""
NexaFiles: Server Launcher and Auto-Seeder
Run this script to launch the NexaFiles web application.
"""

import sys
import io
from pathlib import Path
from config import Config
from app import create_app
from services.metadata_service import init_db, get_db_connection, create_file_record
from services.auth_service import register_user
from services.storage_service import storage_service

def seed_demo_environment():
    """Seed initial demo user and sample documents if database is new."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM users')
    user_count = cursor.fetchone()['count']
    
    if user_count == 0:
        print("[*] First-time setup detected: Seeding demo account and sample files...")
        
        # 1. Create Demo User
        success, msg, user_id = register_user(
            username='akshit',
            email='akshit@gnauniversity.edu.in',
            password='password123'
        )
        
        if success and user_id:
            # 2. Seed Sample Academic Files
            sample_documents = [
                (
                    "Cloud_Computing_Unit1_Notes.pdf",
                    "Notes",
                    "cloud, virtualization, eec401, unit1",
                    b"%PDF-1.4 NexaFiles Cloud Virtualization and Infrastructure Lecture Notes."
                ),
                (
                    "Decoupled_Object_Storage_Research.docx",
                    "Research",
                    "aws, s3, storage, research-paper",
                    b"NexaFiles Research Paper: Empirical Evaluation of Decoupled S3 Cloud Storage Architectures."
                ),
                (
                    "Major_Project_Midterm_Presentation.pptx",
                    "Presentation",
                    "slides, midsem, evaluation, gna-university",
                    b"PowerPoint Presentation Deck for Major Project EEC401 Mid-Semester Review."
                ),
                (
                    "boto3_s3_storage_controller.py",
                    "Code",
                    "python, backend, boto3, aws-sdk",
                    b"# NexaFiles Cloud Controller\nimport boto3\nprint('Boto3 client initialized successfully.')\n"
                ),
                (
                    "GNA_University_Academic_Guidelines.pdf",
                    "Legal",
                    "guidelines, university, regulations",
                    b"School of Engineering, Design and Automation - Major Project Guidelines Document."
                )
            ]
            
            for fname, cat, tags, content in sample_documents:
                s3_key = storage_service.generate_s3_key(user_id, fname)
                ext = fname.rsplit('.', 1)[-1].lower()
                ok, checksum, fsize, _ = storage_service.upload_stream(
                    io.BytesIO(content), s3_key, mime_type='application/octet-stream'
                )
                if ok:
                    create_file_record(
                        user_id=user_id,
                        filename=fname,
                        original_filename=fname,
                        s3_key=s3_key,
                        file_size=fsize,
                        file_type=ext,
                        mime_type='application/octet-stream',
                        category=cat,
                        tags=tags,
                        checksum=checksum
                    )
            print("[+] Seeded demo user 'akshit' (password: password123) with 5 sample documents!")
    
    conn.close()

if __name__ == '__main__':
    print("=" * 70)
    print("  NEXAFILES: CLOUD-BASED INTELLIGENT FILE ORGANIZATION SYSTEM")
    print("  GNA University Major Project Report Implementation (EEC401)")
    print("=" * 70)
    
    app = create_app()
    seed_demo_environment()
    
    status = storage_service.get_status()
    print(f"[*] Storage Engine : {status['storage_mode'].upper()} mode ({'AWS S3 Connected' if status['is_cloud_live'] else 'Local Cloud Vault Emulation'})")
    print(f"[*] Database Path  : {Config.DATABASE}")
    print(f"[*] Local Vault    : {Config.LOCAL_STORAGE_PATH}")
    print(f"[*] Access Portal  : http://127.0.0.1:{Config.PORT}")
    print(f"[*] Demo User      : akshit / password123")
    print("=" * 70)
    print("Press CTRL+C to stop the server.\n")
    
    app.run(host='127.0.0.1', port=Config.PORT, debug=Config.DEBUG)
