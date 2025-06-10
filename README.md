# Healthcare Audio File Upload System

A comprehensive Flutter mobile application with Python Flask backend for healthcare audio file management using Google Cloud services.

## 🏗️ Project Architecture

This project consists of two main components:

### 1. Flutter Mobile Application (`/lib/`)
- **Purpose**: Mobile client for audio file selection and upload
- **Technology**: Flutter/Dart
- **Key Features**: 
  - Audio file picker (mp3, wav, ogg, m4a)
  - 3-step upload process (Pick → Upload → Register)
  - Backend connectivity testing
  - Real-time status updates

### 2. Python Flask Backend (`/python/`)
- **Purpose**: RESTful API for file processing and cloud integration
- **Technology**: Python Flask
- **Key Features**:
  - Google Cloud Storage integration
  - BigQuery metadata tracking
  - FHIR data conversion
  - Team web interface
  - Secure credential management

### 3. Google Cloud Services
- **Cloud Storage**: File storage in `healthcare_audio_analyzer_fhir` bucket
- **BigQuery**: Metadata tracking in `app-audio-analyzer.healthcare_audio_data.audio_files`
- **Cloud Run**: Backend deployment at `https://data-api-887192895309.us-central1.run.app`

## 📊 System Flow

```
Mobile App → Backend API → Cloud Storage → BigQuery
     ↓            ↓             ↓           ↓
Pick File → Upload URL → Store File → Log Metadata
```

## 🚀 Quick Start

### Prerequisites

1. **Development Environment**:
   - Flutter SDK (3.7.2+)
   - Python 3.9+
   - Google Cloud CLI
   - Git

2. **Google Cloud Setup**:
   - Google Cloud Project: `app-audio-analyzer`
   - Service Account with permissions:
     - Storage Admin
     - BigQuery Admin
     - Cloud Run Admin

### Clone Repository

```bash
git clone https://github.com/geopaul343/bigguery.git
cd bigguery
```

## 🔧 Essential Setup Commands

### 1. Google Cloud CLI Setup

```bash
# Install Google Cloud CLI (if not already installed)
# For macOS:
brew install google-cloud-sdk

# For Ubuntu/Debian:
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-sdk

# For Windows (PowerShell):
# Download and run GoogleCloudSDKInstaller.exe from https://cloud.google.com/sdk/docs/install

# Authenticate with Google Cloud
gcloud auth login

# Set default project
gcloud config set project app-audio-analyzer

# Set default region
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
```

### 2. Enable Required Google Cloud APIs

```bash
# Enable all required APIs in one command
gcloud services enable \
  storage.googleapis.com \
  bigquery.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com

# Verify enabled APIs
gcloud services list --enabled
```

### 3. Create Google Cloud Resources

```bash
# Create Cloud Storage bucket
gsutil mb -p app-audio-analyzer gs://healthcare_audio_analyzer_fhir

# Set bucket permissions (make it publicly readable if needed)
gsutil iam ch allUsers:objectViewer gs://healthcare_audio_analyzer_fhir

# Create BigQuery dataset
bq mk --dataset --description "Healthcare audio data storage" app-audio-analyzer:healthcare_audio_data

# Create BigQuery table
bq mk --table app-audio-analyzer:healthcare_audio_data.audio_files \
  id:STRING,user_id:STRING,original_filename:STRING,file_path:STRING,file_size:INTEGER,upload_timestamp:TIMESTAMP,file_url:STRING
```

### 4. Service Account Setup

```bash
# Create service account
gcloud iam service-accounts create audio-upload-service \
  --description="Service account for audio upload API" \
  --display-name="Audio Upload Service"

# Add required IAM roles
gcloud projects add-iam-policy-binding app-audio-analyzer \
  --member="serviceAccount:audio-upload-service@app-audio-analyzer.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding app-audio-analyzer \
  --member="serviceAccount:audio-upload-service@app-audio-analyzer.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding app-audio-analyzer \
  --member="serviceAccount:audio-upload-service@app-audio-analyzer.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Create and download service account key
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=audio-upload-service@app-audio-analyzer.iam.gserviceaccount.com

# Move key to python directory
mv service-account-key.json python/

# Base64 encode the key for Cloud Run deployment
base64 -i python/service-account-key.json | tr -d '\n' > encoded-key.txt
echo "Save this encoded key for Cloud Run environment variable:"
cat encoded-key.txt
```

## 🌐 Required Google Cloud APIs

The following APIs must be enabled in your Google Cloud project:

| API | Purpose | Enable Command |
|-----|---------|----------------|
| **Cloud Storage API** | File storage in buckets | `gcloud services enable storage.googleapis.com` |
| **BigQuery API** | Data warehouse for metadata | `gcloud services enable bigquery.googleapis.com` |
| **Cloud Run API** | Backend deployment | `gcloud services enable run.googleapis.com` |
| **Cloud Build API** | Container building | `gcloud services enable cloudbuild.googleapis.com` |
| **Secret Manager API** | Secure credential storage | `gcloud services enable secretmanager.googleapis.com` |
| **IAM API** | Identity and access management | `gcloud services enable iam.googleapis.com` |
| **Cloud Resource Manager API** | Project resource management | `gcloud services enable cloudresourcemanager.googleapis.com` |

### Enable All APIs at Once:
```bash
gcloud services enable storage.googleapis.com bigquery.googleapis.com run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com iam.googleapis.com cloudresourcemanager.googleapis.com
```

## ✅ Setup Verification Checklist

Use these commands to verify your environment is properly set up:

### 1. Check Prerequisites
```bash
# Verify Flutter installation
flutter doctor

# Verify Python installation  
python --version
python3 --version

# Verify Google Cloud CLI
gcloud version
gcloud auth list
gcloud config get-value project

# Verify Git
git --version
```

### 2. Verify Google Cloud APIs
```bash
# Check if required APIs are enabled
gcloud services list --enabled --filter="name:(storage.googleapis.com OR bigquery.googleapis.com OR run.googleapis.com)"
```

### 3. Verify Google Cloud Resources
```bash
# Check if bucket exists
gsutil ls gs://healthcare_audio_analyzer_fhir

# Check if BigQuery dataset exists
bq ls | grep healthcare_audio_data

# Check if BigQuery table exists
bq show healthcare_audio_data.audio_files

# Check service accounts
gcloud iam service-accounts list --filter="email:audio-upload-service@app-audio-analyzer.iam.gserviceaccount.com"
```

### 4. Test Project Components
```bash
# Test Flutter app
cd /path/to/project
flutter pub get
flutter analyze
flutter test

# Test Python backend locally
cd python
source venv/bin/activate
python -c "import flask, google.cloud.storage, google.cloud.bigquery; print('All packages imported successfully')"

# Test backend API (if running)
curl http://localhost:5000/
```

### 5. Production Deployment Verification
```bash
# Test deployed API
curl https://data-api-887192895309.us-central1.run.app/

# Check Cloud Run service status
gcloud run services describe data-api --region=us-central1 --format="value(status.conditions[0].type,status.conditions[0].status)"
```

## 🔑 Environment Variables Reference

### Required Environment Variables

#### For Local Development (python/.env)
```env
GOOGLE_CLOUD_PROJECT=app-audio-analyzer
BUCKET_NAME=healthcare_audio_analyzer_fhir
DATASET_ID=healthcare_audio_data
TABLE_ID=audio_files
GOOGLE_APPLICATION_CREDENTIALS=service-account-key.json
FLASK_ENV=development
DEBUG=True
```

#### For Cloud Run Production
```bash
# Set these via gcloud command:
gcloud run services update data-api \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=app-audio-analyzer,BUCKET_NAME=healthcare_audio_analyzer_fhir,DATASET_ID=healthcare_audio_data,TABLE_ID=audio_files,SERVICE_ACCOUNT_KEY=<base64-encoded-key>,FLASK_ENV=production" \
  --region=us-central1
```

### API Keys and Credentials

#### Service Account Key Structure
Your `service-account-key.json` should look like:
```json
{
  "type": "service_account",
  "project_id": "app-audio-analyzer",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "audio-upload-service@app-audio-analyzer.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

## 🚀 One-Command Setup Script

Save this as `setup.sh` for quick project setup:

```bash
#!/bin/bash
set -e

echo "🚀 Starting Healthcare Audio Upload System setup..."

# Check prerequisites
echo "📋 Checking prerequisites..."
flutter doctor || { echo "Flutter not found. Install Flutter first."; exit 1; }
python3 --version || { echo "Python3 not found. Install Python first."; exit 1; }
gcloud version || { echo "Google Cloud CLI not found. Install gcloud first."; exit 1; }

# Set up Google Cloud
echo "☁️ Setting up Google Cloud..."
gcloud config set project app-audio-analyzer
gcloud services enable storage.googleapis.com bigquery.googleapis.com run.googleapis.com cloudbuild.googleapis.com

# Create resources
echo "🏗️ Creating Cloud resources..."
gsutil mb -p app-audio-analyzer gs://healthcare_audio_analyzer_fhir 2>/dev/null || echo "Bucket already exists"
bq mk --dataset app-audio-analyzer:healthcare_audio_data 2>/dev/null || echo "Dataset already exists"
bq mk --table app-audio-analyzer:healthcare_audio_data.audio_files id:STRING,user_id:STRING,original_filename:STRING,file_path:STRING,file_size:INTEGER,upload_timestamp:TIMESTAMP,file_url:STRING 2>/dev/null || echo "Table already exists"

# Set up Flutter
echo "📱 Setting up Flutter..."
flutter pub get

# Set up Python
echo "🐍 Setting up Python backend..."
cd python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

echo "✅ Setup complete! Read the documentation for next steps."
```

Make it executable and run:
```bash
chmod +x setup.sh
./setup.sh
```

## 📱 Flutter App Setup

### 1. Install Dependencies

```bash
flutter pub get
```

### 2. Update Backend URL (if needed)

Edit `lib/main.dart` line 15:
```dart
static const String baseUrl = 'YOUR_BACKEND_URL';
```

### 3. Run the App

```bash
# For development
flutter run

# For specific platform
flutter run -d chrome        # Web
flutter run -d android       # Android
flutter run -d ios          # iOS
```

### 4. App Features

- **Test Connection**: Verify backend connectivity
- **Pick Audio File**: Select from device storage
- **Upload to Cloud**: Upload to Google Cloud Storage
- **Register in BigQuery**: Log file metadata

## 🐍 Python Backend Setup

### 1. Create Virtual Environment

```bash
cd python
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create `.env` file in `/python/` directory:
```env
GOOGLE_CLOUD_PROJECT=app-audio-analyzer
BUCKET_NAME=healthcare_audio_analyzer_fhir
DATASET_ID=healthcare_audio_data
TABLE_ID=audio_files
SERVICE_ACCOUNT_KEY=your_base64_encoded_service_account_key
```

### 4. Service Account Setup

```bash
# Create service account key
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=your-service-account@app-audio-analyzer.iam.gserviceaccount.com

# Base64 encode for environment variable
base64 -i service-account-key.json
```

### 5. Run Development Server

```bash
python app.py
```

Backend will be available at `http://localhost:5000`

## 📟 Complete Terminal Commands Reference

### Project Development Commands

#### Flutter Commands
```bash
# Check Flutter installation and doctor
flutter doctor
flutter --version

# Create new Flutter project (if starting from scratch)
flutter create bigquery_sample_new
cd bigquery_sample_new

# Install dependencies
flutter pub get

# Run the app on different platforms
flutter run                    # Default device
flutter run -d chrome         # Web browser
flutter run -d android        # Android device/emulator
flutter run -d ios           # iOS device/simulator
flutter run -d macos         # macOS desktop
flutter run -d windows       # Windows desktop
flutter run -d linux         # Linux desktop

# Build for different platforms
flutter build web --release           # Web build
flutter build apk --release          # Android APK
flutter build appbundle --release    # Android App Bundle
flutter build ios --release          # iOS build
flutter build macos --release        # macOS build
flutter build windows --release      # Windows build
flutter build linux --release        # Linux build

# Testing commands
flutter test                  # Unit tests
flutter test integration_test # Integration tests
flutter analyze              # Static analysis
flutter format .             # Format code

# Clean and reset
flutter clean
flutter pub get
```

#### Python Backend Commands
```bash
# Navigate to python directory
cd python

# Create virtual environment
python -m venv venv
python3 -m venv venv  # On some systems

# Activate virtual environment
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows

# Deactivate virtual environment
deactivate

# Install dependencies
pip install -r requirements.txt
pip install --upgrade pip

# Run development server
python app.py
python3 app.py  # On some systems

# Run with specific host and port
python app.py --host=0.0.0.0 --port=8080

# Install new packages and update requirements
pip install package-name
pip freeze > requirements.txt

# Run tests
python -m pytest
python -m pytest tests/
python -m pytest -v         # Verbose output
python -m pytest --cov      # Coverage report
```

### Google Cloud Deployment Commands

#### Cloud Run Deployment
```bash
# Build and deploy using the deploy script
cd python
chmod +x deploy.sh
./deploy.sh

# Manual deployment steps
gcloud builds submit --tag gcr.io/app-audio-analyzer/data-api
gcloud run deploy data-api \
  --image gcr.io/app-audio-analyzer/data-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Update service with environment variables
gcloud run services update data-api \
  --set-env-vars="SERVICE_ACCOUNT_KEY=$SERVICE_ACCOUNT_KEY" \
  --region=us-central1

# View service details
gcloud run services describe data-api --region=us-central1

# View logs
gcloud logs read "resource.type=cloud_run_revision" --limit=50

# Delete service
gcloud run services delete data-api --region=us-central1
```

#### Cloud Storage Commands
```bash
# List buckets
gsutil ls

# List files in bucket
gsutil ls gs://healthcare_audio_analyzer_fhir

# Upload file to bucket
gsutil cp local-file.mp3 gs://healthcare_audio_analyzer_fhir/audio_files/

# Download file from bucket
gsutil cp gs://healthcare_audio_analyzer_fhir/audio_files/file.mp3 ./

# Set bucket permissions
gsutil iam ch allUsers:objectViewer gs://healthcare_audio_analyzer_fhir

# Delete file from bucket
gsutil rm gs://healthcare_audio_analyzer_fhir/audio_files/file.mp3

# Delete bucket
gsutil rb gs://healthcare_audio_analyzer_fhir
```

#### BigQuery Commands
```bash
# List datasets
bq ls

# List tables in dataset
bq ls healthcare_audio_data

# Show table schema
bq show healthcare_audio_data.audio_files

# Query table
bq query --use_legacy_sql=false "
SELECT * FROM \`app-audio-analyzer.healthcare_audio_data.audio_files\` 
LIMIT 10"

# Load data from file
bq load healthcare_audio_data.audio_files data.json

# Delete table
bq rm healthcare_audio_data.audio_files

# Delete dataset
bq rm -r healthcare_audio_data
```

### Development Workflow Commands

#### Git Commands for This Project
```bash
# Clone repository
git clone https://github.com/geopaul343/bigguery.git
cd bigguery

# Check status
git status
git log --oneline

# Create feature branch
git checkout -b feature/new-feature
git push -u origin feature/new-feature

# Stage and commit changes
git add .
git commit -m "feat: add new feature"

# Push changes
git push origin feature/new-feature

# Merge to main
git checkout main
git merge feature/new-feature
git push origin main

# Clean up
git branch -d feature/new-feature
git push origin --delete feature/new-feature
```

#### Testing Commands
```bash
# Backend API testing with curl
# Health check
curl https://data-api-887192895309.us-central1.run.app/

# Generate upload URL
curl -X POST https://data-api-887192895309.us-central1.run.app/generate_upload_url \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.mp3","user_id":"test_user"}'

# Register file
curl -X POST https://data-api-887192895309.us-central1.run.app/register_file \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","filename":"test.mp3","file_path":"audio_files/test.mp3","file_size":1024}'

# Load testing with Apache Bench (if installed)
ab -n 100 -c 10 https://data-api-887192895309.us-central1.run.app/
```

### Monitoring and Debugging Commands

#### Cloud Run Monitoring
```bash
# View service logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=data-api" --limit=50

# Stream logs in real-time
gcloud logs tail "resource.type=cloud_run_revision AND resource.labels.service_name=data-api"

# View metrics
gcloud run services describe data-api --region=us-central1

# List revisions
gcloud run revisions list --service=data-api --region=us-central1
```

#### Flutter Debugging Commands
```bash
# Run in debug mode with verbose output
flutter run --debug --verbose

# Run with performance monitoring
flutter run --profile

# Generate performance timeline
flutter run --trace-startup --profile

# Inspect widget tree
flutter inspector

# Hot reload
r

# Hot restart
R

# Quit
q
```

### Utility Commands

#### Environment Management
```bash
# Check versions
flutter --version
python --version
gcloud version
git --version

# Update tools
flutter upgrade
pip install --upgrade pip
gcloud components update

# Clean up
flutter clean
rm -rf python/venv
rm python/service-account-key.json
rm encoded-key.txt
```

#### File Operations
```bash
# Create directories
mkdir -p docs/assets
mkdir -p test/integration_test

# Copy files
cp python/service-account-key.json.example python/service-account-key.json

# Create environment file
echo "GOOGLE_CLOUD_PROJECT=app-audio-analyzer" > python/.env
echo "BUCKET_NAME=healthcare_audio_analyzer_fhir" >> python/.env

# Base64 encode files
base64 -i python/service-account-key.json | tr -d '\n'

# View file contents
cat python/requirements.txt
head -20 lib/main.dart
tail -10 python/app.py
```

## 🔧 Development Guide

### Backend API Endpoints

#### 1. Health Check
```http
GET /
Response: "Hello, World!"
```

#### 2. Generate Upload URL
```http
POST /generate_upload_url
Content-Type: application/json

{
  "filename": "audio.mp3",
  "user_id": "user123"
}

Response:
{
  "upload_url": "https://storage.googleapis.com/...",
  "file_path": "audio_files/user123_timestamp_audio.mp3"
}
```

#### 3. Register File in BigQuery
```http
POST /register_file
Content-Type: application/json

{
  "user_id": "user123",
  "filename": "audio.mp3",
  "file_path": "audio_files/user123_timestamp_audio.mp3",
  "file_size": 1048576
}

Response:
{
  "message": "File registered successfully",
  "bigquery_id": "generated_uuid"
}
```

#### 4. Team Upload Interface
```http
GET /team_upload
Response: HTML interface for team file uploads
```

### Database Schema

**BigQuery Table**: `app-audio-analyzer.healthcare_audio_data.audio_files`

| Field | Type | Description |
|-------|------|-------------|
| id | STRING | Unique identifier (UUID) |
| user_id | STRING | User identifier |
| original_filename | STRING | Original file name |
| file_path | STRING | Cloud Storage path |
| file_size | INTEGER | File size in bytes |
| upload_timestamp | TIMESTAMP | Upload time |
| file_url | STRING | Public access URL |

### File Structure

```
bigquery_sample_new/
├── lib/
│   └── main.dart                 # Flutter app main file
├── python/
│   ├── app.py                   # Flask main application
│   ├── storage_handler.py       # Cloud Storage operations
│   ├── fhir_converter.py        # FHIR data conversion
│   ├── team_upload.html         # Web interface
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile              # Container configuration
│   └── deploy.sh               # Deployment script
├── pubspec.yaml                # Flutter dependencies
├── .gitignore                  # Git ignore rules
└── README.md                   # This documentation
```

## 🚀 Deployment

### Backend Deployment (Google Cloud Run)

#### 1. Build and Deploy

```bash
cd python
chmod +x deploy.sh
./deploy.sh
```

#### 2. Set Environment Variables

```bash
gcloud run services update data-api \
  --set-env-vars="SERVICE_ACCOUNT_KEY=your_base64_key" \
  --region=us-central1
```

#### 3. Verify Deployment

```bash
curl https://data-api-887192895309.us-central1.run.app/
```

### Flutter App Deployment

#### Web Deployment
```bash
flutter build web
# Deploy to your preferred hosting service
```

#### Mobile App Deployment
```bash
# Android
flutter build apk --release

# iOS
flutter build ios --release
```

## 🔒 Security Considerations

### 1. Credential Management
- **Never commit** service account keys to Git
- Use environment variables for sensitive data
- Base64 encode keys for Cloud Run deployment

### 2. Access Control
- Service account principle of least privilege
- CORS configuration for web interfaces
- User authentication (implement as needed)

### 3. File Validation
- Supported formats: mp3, wav, ogg, m4a
- File size limits configurable
- Malware scanning (recommended for production)

## 🧪 Testing

### Backend Testing

```bash
cd python

# Test health endpoint
curl http://localhost:5000/

# Test upload URL generation
curl -X POST http://localhost:5000/generate_upload_url \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.mp3","user_id":"test_user"}'
```

### Flutter Testing

```bash
# Run unit tests
flutter test

# Run integration tests
flutter test integration_test/
```

## 📝 Common Issues & Solutions

### 1. "You need a private key to sign credentials"
**Solution**: Ensure `SERVICE_ACCOUNT_KEY` environment variable is set with base64-encoded service account key.

### 2. CORS Errors in Web Browser
**Solution**: Check CORS configuration in `app.py` and ensure proper headers.

### 3. File Picker Not Working
**Solution**: Ensure `file_picker` dependency is properly configured for your target platform.

### 4. BigQuery Permission Denied
**Solution**: Verify service account has BigQuery Admin role and proper dataset permissions.

## 🔄 Future Enhancements

1. **User Authentication**: Implement Firebase Auth or OAuth
2. **File Processing**: Add audio transcription/analysis
3. **Real-time Updates**: WebSocket connection for live status
4. **Batch Operations**: Multiple file upload support
5. **Analytics Dashboard**: Usage statistics and reporting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## 📞 Support

For issues and questions:
1. Check existing GitHub issues
2. Create new issue with detailed description
3. Include logs and error messages
4. Specify environment details (OS, Flutter version, etc.)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Last Updated**: December 2024  
**Version**: 1.0.0  
**Maintainer**: Development Team
