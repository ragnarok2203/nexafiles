# NexaFiles: Cloud-Based Intelligent File Organization and Retrieval System

**Major Project (Course Code: EEC401)**  
*School of Engineering, Design and Automation — Department of Computer Science & Engineering*  
*GNA University, Phagwara, Punjab*  
*Candidate: Harleen Kaur (Registration Roll No.: GU-2023-3456)*  

---

## 1. Project Overview

NexaFiles is an intelligent, cloud-integrated document organization and retrieval system that decisively resolves the fragmentation, naming inconsistency, and search latency inherent to traditional personal file storage.

### Core Architectural Features
- **Decoupled Cloud Architecture**: Binary document payloads are persisted in cloud object storage (Amazon S3 / Local Cloud Vault), while rich, queryable metadata is indexed in a relational database engine.
- **Dynamic Multi-Dimensional Categorization**: Files are organized into standardized academic and professional categories (`Notes`, `Research`, `Presentation`, `Code`, `Media`, `Legal`, `Archive`) with custom user metadata tags.
- **Multi-Attribute Search Engine**: Instant full-text and parameterized query synthesis across filenames, categories, extensions, tags, and date ranges.
- **Zero-Trust Ephemeral Access**: Download tokens utilize time-limited Pre-Signed URLs (valid for 15 minutes) with cryptographic HMAC-SHA256 signatures, ensuring private cloud buckets remain completely protected against unauthorized public exposure.
- **Dual-Storage Engine**: Seamlessly operates in **AWS S3 Cloud Mode** (using Amazon Boto3 SDK with SSE-S3 encryption) or in **Local Cloud Vault Emulation Mode** (for offline testing without an active AWS credit card).

---

## 2. Directory Structure

```
nexafiles/
├── app.py                  # Flask application factory and HTTP routing controllers
├── config.py               # AWS S3 credentials and runtime environment configuration
├── run.py                  # Server launcher and automatic demo data seeder
├── requirements.txt        # Python dependency manifest
├── .env.example            # Environment variables template
├── services/
│   ├── auth_service.py     # Password hashing, user registration, and session security
│   ├── storage_service.py  # AWS S3 Boto3 API client & pre-signed URL generator
│   └── metadata_service.py # Relational database schema, indexing, and search engine
├── templates/              # Responsive Jinja2 HTML5 interface templates
│   ├── base.html           # Master layout with navbar, notifications, and upload modal
│   ├── login.html          # Authentication view with demo login autofill
│   ├── register.html       # User registration view
│   ├── dashboard.html      # Centralized metrics, category cards, and recent uploads
│   ├── search.html         # Multi-attribute search and filtering engine
│   └── error.html          # Custom HTTP error view (404, 413, 500)
├── static/
│   ├── css/style.css       # Modern CSS styling (Flexbox, Grid, badges, animations)
│   └── js/app.js           # Drag-and-drop ingestion, live search, star toggling
├── data/                   # SQLite database (nexafiles.db) & local vault storage
└── tests/                  # Automated Pytest suite
    ├── conftest.py         # Test fixtures and temporary database isolation
    ├── test_auth.py        # Authentication and session test cases (TC-01 to TC-05)
    ├── test_storage.py     # File validation, S3 upload, and signed URLs (TC-06 to TC-08, TC-10 to TC-12)
    └── test_search.py      # Multi-attribute search query tests (TC-09)
```

---

## 3. Quick Start (Running the Application)

### Step 1: Navigate to Project Directory
```bash
cd D:\project
```

### Step 2: Install Dependencies (Optional if already present)
```bash
pip install -r requirements.txt
```
*(Flask, Werkzeug, Jinja2, and pytest are already pre-installed in your Python environment).*

### Step 3: Launch NexaFiles Server
```bash
python run.py
```

The application will automatically:
1. Initialize the SQLite database and performance indexes.
2. Seed the demo user (`harleen` / `password123`) and 5 sample documents if running for the first time.
3. Start the web server at: **http://127.0.0.1:5000**

---

## 4. Default Login Credentials
- **Username / Email**: `harleen` (or `harleen@gnauniversity.edu.in`)
- **Password**: `password123`
*(You can also click the **"Use Demo Account"** button on the login screen to autofill).*

---

## 5. Live AWS S3 Cloud Storage Setup (Optional)

To connect NexaFiles to an actual Amazon Web Services S3 bucket:

1. Open `.env` (or copy `.env.example` to `.env`).
2. Update the configuration keys:
   ```env
   STORAGE_MODE=s3
   AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
   AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your-unique-s3-bucket-name
   ```
3. Restart `python run.py`. The top navbar will display the green **"AWS S3 Live"** badge!

---

## 6. Running Automated Verification Tests

Run the full automated test suite covering all 12 major test cases defined in the project report:

```bash
pytest tests/ -v
```

All test cases verify:
- Registration, password hashing, and session management.
- File upload, format validation, and SHA-256 fingerprinting.
- Multi-dimensional search queries and metrics calculation.
- Pre-signed URL token generation and secure file deletion.
