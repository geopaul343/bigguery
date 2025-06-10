# Deployment Guide

This guide covers deploying the Healthcare Audio File Upload System to various environments.

## 📋 Prerequisites

### Required Tools
- Google Cloud CLI (`gcloud`)
- Docker
- Flutter SDK
- Python 3.9+
- Git

### Google Cloud Setup
1. **Project**: `app-audio-analyzer`
2. **Required APIs**:
   - Cloud Storage API
   - BigQuery API
   - Cloud Run API
   - Cloud Build API

3. **Service Account Permissions**:
   - Storage Admin
   - BigQuery Admin
   - Cloud Run Admin

## 🐍 Backend Deployment

### Local Development

#### 1. Environment Setup
```bash
cd python
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Environment Variables
Create `python/.env`:
```env
GOOGLE_CLOUD_PROJECT=app-audio-analyzer
BUCKET_NAME=healthcare_audio_analyzer_fhir
DATASET_ID=healthcare_audio_data
TABLE_ID=audio_files
GOOGLE_APPLICATION_CREDENTIALS=service-account-key.json
```

#### 3. Run Development Server
```bash
python app.py
```
Server runs on `http://localhost:5000`

### Google Cloud Run Deployment

#### 1. Prepare Service Account
```bash
# Create service account
gcloud iam service-accounts create audio-upload-service \
  --description="Service account for audio upload API" \
  --display-name="Audio Upload Service"

# Add required roles
gcloud projects add-iam-policy-binding app-audio-analyzer \
  --member="serviceAccount:audio-upload-service@app-audio-analyzer.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding app-audio-analyzer \
  --member="serviceAccount:audio-upload-service@app-audio-analyzer.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"

# Create and download key
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=audio-upload-service@app-audio-analyzer.iam.gserviceaccount.com
```

#### 2. Prepare Deployment
```bash
cd python

# Base64 encode service account key
SERVICE_ACCOUNT_KEY=$(base64 -i service-account-key.json | tr -d '\n')
echo $SERVICE_ACCOUNT_KEY
```

#### 3. Build and Deploy
```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

#### 4. Set Environment Variables
```bash
gcloud run services update data-api \
  --set-env-vars="SERVICE_ACCOUNT_KEY=$SERVICE_ACCOUNT_KEY" \
  --region=us-central1
```

#### 5. Verify Deployment
```bash
# Test health endpoint
curl https://data-api-887192895309.us-central1.run.app/

# Test upload URL generation
curl -X POST https://data-api-887192895309.us-central1.run.app/generate_upload_url \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.mp3","user_id":"test_user"}'
```

### Custom Domain Setup (Optional)

#### 1. Reserve Static IP
```bash
gcloud compute addresses create audio-api-ip --global
```

#### 2. Set up Load Balancer
```bash
# Create load balancer with Cloud Run backend
gcloud compute backend-services create audio-api-backend \
  --global \
  --load-balancing-scheme=EXTERNAL

# Add Cloud Run service to backend
gcloud compute backend-services add-backend audio-api-backend \
  --global \
  --network-endpoint-group=data-api-neg \
  --network-endpoint-group-region=us-central1
```

#### 3. Configure SSL Certificate
```bash
# Create SSL certificate
gcloud compute ssl-certificates create audio-api-ssl \
  --domains=your-domain.com
```

## 📱 Flutter App Deployment

### Development Setup

#### 1. Install Dependencies
```bash
flutter pub get
```

#### 2. Update Configuration
Edit `lib/main.dart`:
```dart
static const String baseUrl = 'https://data-api-887192895309.us-central1.run.app';
```

#### 3. Run Development
```bash
flutter run -d chrome   # Web
flutter run -d android  # Android
flutter run -d ios     # iOS
```

### Web Deployment

#### 1. Build for Web
```bash
flutter build web --release
```

#### 2. Deploy to Firebase Hosting
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Initialize Firebase
firebase init hosting

# Deploy
firebase deploy
```

#### 3. Deploy to Netlify
```bash
# Build
flutter build web --release

# Deploy to Netlify (drag & drop build/web folder)
# Or use Netlify CLI
netlify deploy --prod --dir=build/web
```

### Android Deployment

#### 1. Configure Signing
Create `android/key.properties`:
```properties
storePassword=your_store_password
keyPassword=your_key_password
keyAlias=your_key_alias
storeFile=your_keystore_file
```

Update `android/app/build.gradle`:
```gradle
android {
    signingConfigs {
        release {
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
            storeFile file(keystoreProperties['storeFile'])
            storePassword keystoreProperties['storePassword']
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
        }
    }
}
```

#### 2. Build APK
```bash
flutter build apk --release
```

#### 3. Build App Bundle (for Play Store)
```bash
flutter build appbundle --release
```

#### 4. Deploy to Google Play Console
1. Upload `build/app/outputs/bundle/release/app-release.aab`
2. Complete store listing
3. Submit for review

### iOS Deployment

#### 1. Configure Xcode Project
```bash
flutter build ios --release
open ios/Runner.xcworkspace
```

#### 2. Set up Provisioning
- Configure signing in Xcode
- Set up App Store Connect app
- Create provisioning profiles

#### 3. Build for App Store
```bash
flutter build ipa --release
```

#### 4. Upload to App Store
- Use Xcode Organizer
- Or Application Loader
- Submit for review

## 🔄 CI/CD Pipeline

### GitHub Actions Setup

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Google Cloud Run

on:
  push:
    branches: [ main ]
    paths: [ 'python/**' ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - id: 'auth'
      uses: 'google-github-actions/auth@v1'
      with:
        credentials_json: '${{ secrets.GCP_SA_KEY }}'
    
    - name: 'Set up Cloud SDK'
      uses: 'google-github-actions/setup-gcloud@v1'
    
    - name: 'Configure Docker'
      run: gcloud auth configure-docker
    
    - name: 'Build and Deploy'
      run: |
        cd python
        gcloud run deploy data-api \
          --source . \
          --region us-central1 \
          --allow-unauthenticated \
          --set-env-vars="SERVICE_ACCOUNT_KEY=${{ secrets.SERVICE_ACCOUNT_KEY }}"
```

### Flutter CI/CD

Create `.github/workflows/flutter.yml`:

```yaml
name: Flutter CI/CD

on:
  push:
    branches: [ main ]
    paths: [ 'lib/**', 'pubspec.yaml' ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: subosito/flutter-action@v2
      with:
        flutter-version: 3.7.2
    - run: flutter pub get
    - run: flutter test
    
  build-web:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: subosito/flutter-action@v2
      with:
        flutter-version: 3.7.2
    - run: flutter pub get
    - run: flutter build web --release
    - name: Deploy to Firebase
      uses: FirebaseExtended/action-hosting-deploy@v0
      with:
        repoToken: '${{ secrets.GITHUB_TOKEN }}'
        firebaseServiceAccount: '${{ secrets.FIREBASE_SERVICE_ACCOUNT }}'
        projectId: app-audio-analyzer
```

## 🔧 Environment Configuration

### Development Environment
```env
# python/.env
GOOGLE_CLOUD_PROJECT=app-audio-analyzer
BUCKET_NAME=healthcare_audio_analyzer_fhir
DATASET_ID=healthcare_audio_data
TABLE_ID=audio_files
GOOGLE_APPLICATION_CREDENTIALS=service-account-key.json
FLASK_ENV=development
DEBUG=True
```

### Production Environment
```bash
# Cloud Run environment variables
gcloud run services update data-api \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=app-audio-analyzer" \
  --set-env-vars="BUCKET_NAME=healthcare_audio_analyzer_fhir" \
  --set-env-vars="DATASET_ID=healthcare_audio_data" \
  --set-env-vars="TABLE_ID=audio_files" \
  --set-env-vars="SERVICE_ACCOUNT_KEY=$SERVICE_ACCOUNT_KEY" \
  --set-env-vars="FLASK_ENV=production" \
  --region=us-central1
```

## 📊 Monitoring & Logging

### Cloud Run Monitoring
```bash
# View logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=data-api" --limit=50

# Set up alerts
gcloud alpha monitoring policies create --policy-from-file=monitoring-policy.yaml
```

### Application Monitoring
```python
# Add to app.py
import logging
from google.cloud import logging as cloud_logging

# Configure logging
if not app.debug:
    client = cloud_logging.Client()
    client.setup_logging()
    
# Add metrics
from google.cloud import monitoring_v3

def track_upload_metrics():
    client = monitoring_v3.MetricServiceClient()
    # Custom metrics implementation
```

## 🔒 Security Configuration

### HTTPS Enforcement
```python
# Add to app.py
from flask_talisman import Talisman

if not app.debug:
    Talisman(app, force_https=True)
```

### CORS Configuration
```python
# Update CORS settings
CORS(app, origins=[
    'https://your-domain.com',
    'https://data-api-887192895309.us-central1.run.app'
])
```

### Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per minute")
def upload_file():
    # Implementation
```

## 🧪 Testing Deployment

### Automated Testing
```bash
# Backend tests
cd python
python -m pytest tests/

# Flutter tests
flutter test
flutter test integration_test/
```

### Manual Testing Checklist

#### Backend Tests
- [ ] Health check endpoint responds
- [ ] Upload URL generation works
- [ ] File registration works
- [ ] BigQuery integration works
- [ ] Error handling works properly

#### Frontend Tests
- [ ] App loads correctly
- [ ] Backend connection test passes
- [ ] File picker works
- [ ] Upload process completes
- [ ] Status messages display properly

### Load Testing
```bash
# Install artillery
npm install -g artillery

# Create test config (artillery-config.yml)
config:
  target: 'https://data-api-887192895309.us-central1.run.app'
  phases:
    - duration: 60
      arrivalRate: 10
scenarios:
  - name: "Health check"
    requests:
      - get:
          url: "/"

# Run load test
artillery run artillery-config.yml
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Service Account Key Issues
```bash
# Verify key format
cat service-account-key.json | jq .

# Re-encode for Cloud Run
base64 -i service-account-key.json | tr -d '\n'
```

#### 2. CORS Errors
```python
# Update CORS configuration
CORS(app, origins=['*'], allow_headers=['Content-Type'])
```

#### 3. Cloud Run Timeouts
```bash
# Increase timeout
gcloud run services update data-api \
  --timeout=300 \
  --region=us-central1
```

#### 4. Memory Issues
```bash
# Increase memory
gcloud run services update data-api \
  --memory=1Gi \
  --region=us-central1
```

### Rollback Procedures

#### Cloud Run Rollback
```bash
# List revisions
gcloud run revisions list --service=data-api --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic data-api \
  --to-revisions=REVISION_NAME=100 \
  --region=us-central1
```

#### Flutter App Rollback
```bash
# Revert to previous commit
git revert HEAD

# Rebuild and redeploy
flutter build web --release
firebase deploy
```

## 📈 Scaling Considerations

### Backend Scaling
- Cloud Run automatically scales based on traffic
- Configure max instances to control costs
- Use Cloud SQL for persistent data storage

### Frontend Scaling
- Use CDN for static assets
- Implement caching strategies
- Consider server-side rendering for SEO

### Database Scaling
- BigQuery handles large datasets automatically
- Partition tables by date for better performance
- Use clustering for frequently queried columns

---

This deployment guide provides comprehensive instructions for deploying the Healthcare Audio File Upload System to production. Follow the appropriate sections based on your deployment target and requirements. 