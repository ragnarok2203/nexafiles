# ⚡ NexaFiles — Enterprise Cloud-Based Intelligent File Organization & Retrieval Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask 3.0](https://img.shields.io/badge/Flask-3.0%2B-black.svg)](https://flask.palletsprojects.com/)
[![AWS S3](https://img.shields.io/badge/AWS-S3%20Boto3-orange.svg)](https://aws.amazon.com/s3/)
[![Tests Passing](https://img.shields.io/badge/Pytest-26%2F26%20Passed-brightgreen.svg)]()
[![Security Audit](https://img.shields.io/badge/OWASP%20Top%2010-Hardened-blue.svg)]()

> **NexaFiles** is an enterprise-grade, cloud-integrated document organization, retrieval, and intelligence platform. Architected with decoupled object storage and relational indexing, it delivers sub-second parametric search, in-browser code and document previews, AI-powered document summarization, smart version control, zero-trust password-protected sharing, and automated security audit logging.

---

## 🌟 Key Platform Features

### 1. 👁 In-Browser Multi-Format Document & Code Previewer
- Instant browser-native rendering for source code (`.py`, `.js`, `.html`, `.css`, `.json`, `.sql`, `.sh`, `.md`), images (`.png`, `.jpg`, `.jpeg`, `.gif`), and PDF documents.
- Includes formatted code container with syntax recognition and 1-click **Copy Code** clipboard action.

### 2. 🤖 AI-Powered Document Intelligence & Auto-Tagging
- Synthesizes an executive **3-Bullet Summary** of document payloads (PDF, DOCX, text, and code) on demand.
- Automatically extracts the top representative technical keywords and recommends them as indexing search tags with 1-click application.

### 3. 🕒 Smart Revision Control & Version Rollback
- Automatically detects updates to existing documents and records revisions (`v1`, `v2`, `v3`...).
- Interactive **Revision History** modal displaying timestamp, file size changes, SHA-256 fingerprints, and 1-click **Restore Previous Revision** capability.

### 4. 🔐 Ephemeral Password-Protected Public Sharing Links
- Generate secure share links (`/share/<token>`) with custom expiration windows (1 hour, 24 hours, 7 days, 30 days).
- Optional cryptographic passphrase authentication and maximum download limits with auto-expiration.

### 5. ⚡ Real-Time Content Deduplication
- SHA-256 fingerprint hashing performed prior to storage allocation.
- Automatically detects duplicate payloads across the repository, linking shared cloud object keys to prevent redundant disk/cloud cost.

### 6. 🛡 Security Audit Trail & CSV Exporter
- Zero-trust audit logging tracking all platform operations (`UPLOAD`, `DOWNLOAD`, `PREVIEW`, `DELETE`, `STAR_TOGGLE`, `CREATE_SHARE`, `VERSION_UPLOAD`).
- Dedicated Audit Trail page (`/activity`) with action filtering and 1-click export to `nexafiles_security_audit.csv`.

### 7. 🎨 Obsidian Glassmorphic SaaS Interface & Dark Mode
- Linear/Vercel-inspired UI with custom status badges, animated dropzone, format capsules, and an instant Light/Dark mode switcher.

---

## 📁 Directory Structure

```
D:\project/
├── app.py                            # Flask application factory and route controllers
├── config.py                         # AWS S3 and runtime environment configurations
├── run.py                            # Server launcher and automatic demo data seeder
├── requirements.txt                  # Python dependencies manifest
├── .env / .env.example               # Environment variables configuration
├── .gitignore                        # Git ignore rules for virtualenvs, caches & executables
├── README.md                         # Platform documentation
├── NexaFiles_Major_Project_Report.docx# Complete GNA University Major Project Report (EEC401)
├── docs/
│   └── NexaFiles_Major_Project_Report.docx
├── services/
│   ├── ai_service.py                 # Document text extraction, 3-bullet summarizer & keyword tagging
│   ├── auth_service.py               # PBKDF2 password hashing & session management
│   ├── metadata_service.py           # SQLite relational modeling, versioning & audit trail
│   └── storage_service.py            # AWS S3 / Local Cloud Vault with HMAC-SHA256 Pre-Signed URLs
├── templates/
│   ├── base.html                     # Navbar, dark mode toggle, modals (Preview, AI, Share, Version)
│   ├── dashboard.html                # Metrics counters, category cards & recent files
│   ├── search.html                   # Parametric search (keyword, extension, category, tags)
│   ├── activity.html                 # Security audit trail & CSV export view
│   ├── share.html                    # Public password-protected download portal
│   ├── login.html / register.html    # Authentication screens with 1-click Demo Account button
│   └── error.html                    # Standard HTTP error handler (404, 413, 500)
├── static/
│   ├── css/style.css                 # Obsidian glassmorphism, badges, card animations
│   └── js/app.js                     # Previewer, AI integration, drag-drop, toasts & sharing
├── data/
│   ├── nexafiles.db                  # Initialized SQLite database with demo dataset
│   └── storage/users/                # Cloud Vault storage directory
└── tests/
    ├── conftest.py                   # Pytest fixtures & isolated DB runner
    ├── test_auth.py                  # Test Cases TC-01 to TC-05 (Authentication & Sessions)
    ├── test_storage.py               # Test Cases TC-06 to TC-08, TC-10 to TC-12 (Ingestion & S3)
    ├── test_search.py                # Test Case TC-09 (Multi-Attribute Filtering & Metrics)
    ├── test_features.py              # Test Cases TC-13 to TC-18 (Preview, AI, Sharing, Versions, Audit)
    └── test_security.py              # Security Verification SEC-01 to SEC-06 (OWASP Hardening)
```

---

## 🚀 Quick Start (Running the Application)

### Step 1: Navigate to Project Directory
```powershell
cd "D:\project"
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Launch NexaFiles Server
```powershell
python run.py
```

* **Web Portal URL**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
* **Pre-seeded Demo User**: `akshit` (or `akshit@gnauniversity.edu.in`)
* **Password**: `password123` *(or click the **"Use Demo Account"** button on the login screen)*

---

## 🧪 Comprehensive Verification Suite (26/26 Test Cases)

Run the full automated test suite covering all core requirements, enterprise extensions, and OWASP security checks:

```powershell
cd "D:\project"
python -m pytest tests/ -v
```

```
tests/test_auth.py::test_tc01_user_registration_success PASSED
tests/test_auth.py::test_tc02_duplicate_user_registration_rejection PASSED
tests/test_auth.py::test_tc03_user_login_success PASSED
tests/test_auth.py::test_tc04_invalid_password_rejection PASSED
tests/test_auth.py::test_tc05_unauthorized_access_redirect PASSED
tests/test_auth.py::test_user_logout PASSED
tests/test_features.py::test_tc13_in_browser_preview PASSED
tests/test_features.py::test_tc14_ai_summarization_and_tagging PASSED
tests/test_features.py::test_tc15_ephemeral_share_link_and_download PASSED
tests/test_features.py::test_tc16_smart_versioning_and_rollback PASSED
tests/test_features.py::test_tc17_content_deduplication PASSED
tests/test_features.py::test_tc18_activity_audit_logs_and_csv PASSED
tests/test_search.py::test_tc09_multi_attribute_search PASSED
tests/test_search.py::test_metrics_api PASSED
tests/test_security.py::test_sec01_http_security_headers PASSED
tests/test_security.py::test_sec02_session_cookie_flags PASSED
tests/test_security.py::test_sec03_path_traversal_rejection PASSED
tests/test_security.py::test_sec04_open_redirect_defense PASSED
tests/test_security.py::test_sec05_idor_boundary_isolation PASSED
tests/test_security.py::test_sec06_brute_force_rate_limiter_logic PASSED
tests/test_storage.py::test_tc06_file_upload_success PASSED
tests/test_storage.py::test_tc07_prohibited_extension_rejection PASSED
tests/test_storage.py::test_tc08_checksum_calculation PASSED
tests/test_storage.py::test_tc10_presigned_download_url_generation PASSED
tests/test_storage.py::test_tc11_star_toggle PASSED
tests/test_storage.py::test_tc12_file_deletion PASSED

======================== 26 passed in 47.25s ========================
```

---

## 🛡 Enterprise Security & OWASP Top 10 Hardening

| Vector / OWASP Category | Vulnerability Surface | Defensive Mitigation & Implementation | Verification Test |
| :--- | :--- | :--- | :--- |
| **A01: Broken Access Control** | Path Traversal in streaming | `pathlib.Path.is_relative_to(base_dir)` strictly enforces storage root isolation; rejects `../` traversal | `test_sec03_path_traversal_rejection` |
| **A01: Broken Access Control** | IDOR on downloads & preview | Relational user boundary (`WHERE user_id = ?`) asserted on all file preview, download, and delete operations | `test_sec05_idor_boundary_isolation` |
| **A01: Broken Access Control** | Open Redirect on `/login` | Host validation via `is_safe_url` ensures redirection stays within original domain | `test_sec04_open_redirect_defense` |
| **A02: Cryptographic Failures** | Cookie theft & interception | `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, PBKDF2 password hashing | `test_sec02_session_cookie_flags` |
| **A03: Injection** | SQL Injection & DOM XSS | SQLite parameterized queries (`?`), `document.createTextNode` DOM sanitization, HTML attribute `data-*` safety | Core Test Suite |
| **A04: Insecure Design** | Credential brute force | Sliding-window IP rate limiter on login and password-protected ephemeral shares | `test_sec06_brute_force_rate_limiter_logic` |
| **A05: Security Misconfiguration** | Missing HTTP Security Headers | Middleware adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, CSP, and Permissions-Policy | `test_sec01_http_security_headers` |

---

## 🌐 Live AWS S3 Cloud Storage Setup (Optional)

To switch NexaFiles from Local Vault Emulation to live AWS S3:

1. Open `.env` (or copy `.env.example` to `.env`).
2. Update the credentials:
   ```env
   STORAGE_MODE=s3
   AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
   AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your-s3-bucket-name
   ```
3. Restart `python run.py`. The top navbar will display the green **"AWS S3 Live"** badge!
