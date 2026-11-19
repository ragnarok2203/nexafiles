# -*- coding: utf-8 -*-
"""
NexaFiles: Cloud Storage Integration and Pre-Signed URL Generator
Supports Amazon Web Services (AWS) S3 Object Storage via Boto3
with automatic local cloud emulation fallback for offline testing.
"""

import os
import time
import hmac
import hashlib
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from config import Config

# Optional Boto3 import
try:
    import boto3
    from botocore.config import Config as BotoConfig
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

class StorageService:
    """Manages cloud object uploads, pre-signed URL generation, and deletions."""
    
    def __init__(self):
        self.mode = Config.STORAGE_MODE
        self.s3_client = None
        self.bucket_name = Config.S3_BUCKET_NAME
        self.local_storage_path = Path(Config.LOCAL_STORAGE_PATH)
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Check if AWS credentials are provided and Boto3 is installed
        has_aws_keys = bool(Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY)
        
        if self.mode == 's3' and BOTO3_AVAILABLE and has_aws_keys:
            try:
                boto_config = BotoConfig(
                    max_pool_connections=50,
                    connect_timeout=5.0,
                    read_timeout=5.0,
                    retries={'max_attempts': 3, 'mode': 'standard'}
                )
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                    region_name=Config.AWS_REGION,
                    config=boto_config
                )
                self.mode = 's3'
            except Exception as e:
                print(f"[StorageService] AWS initialization failed ({e}), falling back to local mode.")
                self.mode = 'local'
        else:
            self.mode = 'local'
            
    def _get_base_path(self):
        """Retrieve current base storage path (supporting test context isolation)."""
        try:
            from flask import current_app, has_app_context
            if has_app_context() and current_app.config.get('LOCAL_STORAGE_PATH'):
                return Path(current_app.config['LOCAL_STORAGE_PATH'])
        except Exception:
            pass
        return self.local_storage_path

    def generate_s3_key(self, user_id, filename):
        """Generate a globally unique cloud storage key."""
        clean_fn = secure_filename(filename) or "document.bin"
        unique_token = uuid.uuid4().hex[:12]
        return f"users/{user_id}/{unique_token}_{clean_fn}"

    def upload_stream(self, file_stream, s3_key, mime_type='application/octet-stream'):
        """
        Upload binary file stream to storage and compute SHA-256 fingerprint.
        Returns (success: bool, checksum: str, file_size: int, error: str | None).
        """
        hasher = hashlib.sha256()
        file_size = 0
        
        if self.mode == 's3' and self.s3_client:
            try:
                # Read stream in chunks to compute hash while spooling
                buffer = bytearray()
                while True:
                    chunk = file_stream.read(65536)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    file_size += len(chunk)
                    buffer.extend(chunk)
                
                # Upload to Amazon S3 with SSE-S3 AES-256 encryption
                import io
                self.s3_client.upload_fileobj(
                    io.BytesIO(buffer),
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ServerSideEncryption': 'AES256',
                        'ContentType': mime_type
                    }
                )
                return True, hasher.hexdigest(), file_size, None
            except Exception as e:
                return False, '', 0, f"AWS S3 Upload Error: {str(e)}"
        else:
            # Local Cloud Emulation Mode
            try:
                base_dir = self._get_base_path().resolve()
                target_path = (base_dir / s3_key).resolve()
                if not target_path.is_relative_to(base_dir):
                    return False, '', 0, "Security error: Path traversal attempt detected."
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(target_path, 'wb') as dst:
                    while True:
                        chunk = file_stream.read(65536)
                        if not chunk:
                            break
                        hasher.update(chunk)
                        file_size += len(chunk)
                        dst.write(chunk)
                        
                return True, hasher.hexdigest(), file_size, None
            except Exception as e:
                return False, '', 0, f"Local Storage Error: {str(e)}"

    def generate_presigned_download_url(self, s3_key, original_filename, expires_in=None):
        """
        Generate ephemeral signed URL for direct file download.
        Expires in 15 minutes (900 seconds) by default.
        """
        if expires_in is None:
            expires_in = Config.PRESIGNED_URL_EXPIRATION
            
        if self.mode == 's3' and self.s3_client:
            try:
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': s3_key,
                        'ResponseContentDisposition': f'attachment; filename="{original_filename}"'
                    },
                    ExpiresIn=expires_in
                )
                return url, 's3'
            except Exception as e:
                print(f"[StorageService] Failed to generate S3 pre-signed URL: {e}")
                # Fall back to local URL generator
                pass
                
        # Local Emulated Signed URL
        # Format: /download/stream/<s3_key>?expires=<timestamp>&signature=<hmac>
        expires_at = int(time.time()) + expires_in
        signature_data = f"{s3_key}:{expires_at}:{Config.SECRET_KEY}"
        sig = hmac.new(Config.SECRET_KEY.encode('utf-8'), signature_data.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Local streaming route
        url = f"/storage/stream/{s3_key}?expires={expires_at}&sig={sig}&filename={original_filename}"
        return url, 'local'

    def verify_local_download_signature(self, s3_key, expires_at_str, signature):
        """Verify HMAC-SHA256 signature for local emulated pre-signed URL."""
        try:
            expires_at = int(expires_at_str)
            if time.time() > expires_at:
                return False, "Download token has expired."
                
            signature_data = f"{s3_key}:{expires_at}:{Config.SECRET_KEY}"
            expected_sig = hmac.new(Config.SECRET_KEY.encode('utf-8'), signature_data.encode('utf-8'), hashlib.sha256).hexdigest()
            
            if hmac.compare_digest(expected_sig, signature):
                return True, None
            return False, "Invalid cryptographic download signature."
        except Exception as e:
            return False, f"Signature validation error: {str(e)}"

    def get_local_file_path(self, s3_key):
        """Retrieve local absolute path for direct file inspection (local mode)."""
        try:
            base_dir = self._get_base_path().resolve()
            target = (base_dir / s3_key).resolve()
            if not target.is_relative_to(base_dir):
                return None
            return target if target.exists() else None
        except Exception:
            return None

    def get_file_bytes(self, s3_key, max_bytes=None):
        """Read binary contents of a storage object."""
        if self.mode == 's3' and self.s3_client:
            try:
                resp = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                body = resp['Body']
                return body.read(max_bytes) if max_bytes else body.read()
            except Exception as e:
                print(f"[StorageService] Failed to read S3 object: {e}")
                return None
        else:
            target = self.get_local_file_path(s3_key)
            if not target:
                return None
            try:
                with open(target, 'rb') as f:
                    return f.read(max_bytes) if max_bytes else f.read()
            except Exception as e:
                print(f"[StorageService] Failed to read local file: {e}")
                return None

    def delete_object(self, s3_key):
        """Delete binary payload from storage."""
        if self.mode == 's3' and self.s3_client:
            try:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                return True
            except Exception as e:
                print(f"[StorageService] Failed to delete S3 object: {e}")
                return False
        else:
            try:
                base_dir = self._get_base_path().resolve()
                target_path = (base_dir / s3_key).resolve()
                if not target_path.is_relative_to(base_dir):
                    return False
                if target_path.exists():
                    target_path.unlink()
                return True
            except Exception as e:
                print(f"[StorageService] Failed to delete local file: {e}")
                return False

    def get_status(self):
        """Return operational cloud storage health metrics."""
        return {
            'storage_mode': self.mode,
            'is_cloud_live': self.mode == 's3',
            'bucket_name': self.bucket_name if self.mode == 's3' else 'local-emulated-vault',
            'boto3_installed': BOTO3_AVAILABLE,
            'local_storage_path': str(self._get_base_path())
        }

# Global singleton storage service
storage_service = StorageService()
