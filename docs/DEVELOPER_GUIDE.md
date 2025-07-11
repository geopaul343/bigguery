# Developer Guide

This guide helps developers understand the codebase structure, development workflow, and how to extend the Healthcare Audio File Upload System.

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Flutter App    │    │  Python Backend │    │  Google Cloud   │
│                 │    │                 │    │                 │
│  • File Picker  │───▶│  • Flask API    │───▶│  • Cloud Storage│
│  • Upload UI    │    │  • Storage      │    │  • BigQuery     │
│  • Status Track │    │  • BigQuery     │    │  • Cloud Run    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow

1. **File Selection**: User picks audio file using Flutter file picker
2. **Upload URL**: App requests signed URL from backend
3. **Direct Upload**: File uploads directly to Cloud Storage
4. **Registration**: Metadata registers in BigQuery via backend
5. **Tracking**: File status tracked throughout process

## 📱 Flutter App Structure

### File Organization

```
lib/
└── main.dart                 # Single file containing entire app
  
```

### User Interface Components

#### Main Buttons
1. **Test Connection**: Verifies backend connectivity
2. **Pick Audio File**: Opens file picker for audio selection
3. **Upload to Cloud**: Uploads selected file to storage
4. **Register in BigQuery**: Records file metadata

#### Status Display
- Real-time status messages
- Loading indicators
- Error handling with user feedback

### Development Workflow

#### 1. Setting Up Development Environment
```bash
# Clone repository
git clone https://github.com/geopaul343/bigguery.git
cd bigguery

# Install Flutter dependencies
flutter pub get

# Run in development mode
flutter run -d chrome  # For web
flutter run            # For mobile
```

#### 2. Hot Reload Development
```bash
# Enable hot reload for rapid development
flutter run --hot
# Hot restart if needed
r
# Quit
q
```

#### 3. Adding New Features

**Example: Adding File Validation**

```dart
bool _validateAudioFile(PlatformFile file) {
  // Check file extension
  final allowedExtensions = ['mp3', 'wav', 'ogg', 'm4a'];
  final extension = file.extension?.toLowerCase();
  
  if (!allowedExtensions.contains(extension)) {
    setState(() {
      statusMessage = 'Invalid file type. Please select an audio file.';
    });
    return false;
  }
  
  // Check file size (10MB limit)
  if (file.size > 10 * 1024 * 1024) {
    setState(() {
      statusMessage = 'File too large. Maximum size is 10MB.';
    });
    return false;
  }
  
  return true;
}
```

#### 4. Error Handling Patterns

```dart
Future<void> _performAction() async {
  setState(() {
    isLoading = true;
    statusMessage = 'Processing...';
  });
  
  try {
    // Perform action
    final result = await ApiService.someAction();
    
    setState(() {
      statusMessage = 'Success: ${result['message']}';
    });
  } catch (e) {
    setState(() {
      statusMessage = 'Error: $e';
    });
  } finally {
    setState(() {
      isLoading = false;
    });
  }
}
```

## 🐍 Python Backend Structure

### File Organization

```
python/
├── app.py                    # Main Flask application
├── storage_handler.py        # Google Cloud Storage operations
├── fhir_converter.py         # FHIR data conversion
├── team_upload.html          # Web interface template
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container configuration
├── deploy.sh               # Deployment script
└── schema.sql              # Database schema
```

### Core Modules

#### 1. app.py - Main Application
```python
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from storage_handler import StorageHandler
import os

app = Flask(__name__)
CORS(app)

# Initialize storage handler
storage_handler = StorageHandler()
```

**Key Routes:**
- `/`: Health check
- `/generate_upload_url`: Create signed upload URLs
- `/register_file`: Register file metadata in BigQuery
- `/upload`: Direct file upload (for web interface)
- `/team_upload`: Web interface for team uploads

#### 2. storage_handler.py - Cloud Integration
```python
class StorageHandler:
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(BUCKET_NAME)
        self.bigquery_client = bigquery.Client()
    
    def generate_upload_url(self, filename, user_id):
        """Generate signed URL for file upload"""
        
    def upload_to_bigquery(self, file_data):
        """Insert file metadata into BigQuery"""
        
    def create_file_path(self, user_id, filename):
        """Create structured file path"""
```

#### 3. fhir_converter.py - FHIR Integration
```python
class FHIRConverter:
    def convert_audio_to_fhir(self, file_data):
        """Convert audio file metadata to FHIR Media resource"""
        return {
            "resourceType": "Media",
            "id": str(uuid.uuid4()),
            "status": "completed",
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/media-type",
                    "code": "audio",
                    "display": "Audio"
                }]
            },
            # ... more FHIR fields
        }
```

### Development Workflow

#### 1. Local Development Setup
```bash
cd python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run development server
python app.py
```

#### 2. Adding New Endpoints

**Example: Adding File List Endpoint**

```python
@app.route('/files/<user_id>', methods=['GET'])
def list_user_files(user_id):
    """List all files for a specific user"""
    try:
        # Query BigQuery for user files
        query = f"""
        SELECT id, original_filename, upload_timestamp, file_size
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE user_id = @user_id
        ORDER BY upload_timestamp DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
            ]
        )
        
        query_job = storage_handler.bigquery_client.query(query, job_config=job_config)
        results = query_job.result()
        
        files = []
        for row in results:
            files.append({
                'id': row.id,
                'filename': row.original_filename,
                'upload_time': row.upload_timestamp.isoformat(),
                'size': row.file_size
            })
        
        return jsonify({
            'files': files,
            'count': len(files)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

#### 3. Testing New Features

```bash
# Run unit tests
python -m pytest tests/

# Test specific endpoint
curl -X GET http://localhost:5000/files/test_user

# Test with different HTTP methods
curl -X POST http://localhost:5000/new_endpoint \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

#### 4. Error Handling Best Practices

```python
from functools import wraps
import logging

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({
                'error': 'Internal server error',
                'message': str(e)
            }), 500
    return decorated_function

@app.route('/protected_endpoint')
@handle_errors
def protected_endpoint():
    # Endpoint logic here
    pass
```

## 🔧 Configuration Management

### Environment Variables

#### Development (.env)
```env
GOOGLE_CLOUD_PROJECT=app-audio-analyzer
BUCKET_NAME=healthcare_audio_analyzer_fhir
DATASET_ID=healthcare_audio_data
TABLE_ID=audio_files
GOOGLE_APPLICATION_CREDENTIALS=service-account-key.json
FLASK_ENV=development
DEBUG=True
```

#### Production (Cloud Run)
```bash
gcloud run services update data-api \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=app-audio-analyzer" \
  --set-env-vars="BUCKET_NAME=healthcare_audio_analyzer_fhir" \
  --set-env-vars="DATASET_ID=healthcare_audio_data" \
  --set-env-vars="TABLE_ID=audio_files" \
  --set-env-vars="SERVICE_ACCOUNT_KEY=$SERVICE_ACCOUNT_KEY"
```

### Configuration Classes

```python
import os
from dataclasses import dataclass

@dataclass
class Config:
    PROJECT_ID: str = os.getenv('GOOGLE_CLOUD_PROJECT', 'app-audio-analyzer')
    BUCKET_NAME: str = os.getenv('BUCKET_NAME', 'healthcare_audio_analyzer_fhir')
    DATASET_ID: str = os.getenv('DATASET_ID', 'healthcare_audio_data')
    TABLE_ID: str = os.getenv('TABLE_ID', 'audio_files')
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'

config = Config()
```

## 🗄️ Database Schema

### BigQuery Table Structure

```sql
CREATE TABLE `app-audio-analyzer.healthcare_audio_data.audio_files` (
  id STRING NOT NULL,
  user_id STRING NOT NULL,
  original_filename STRING NOT NULL,
  file_path STRING NOT NULL,
  file_size INT64 NOT NULL,
  upload_timestamp TIMESTAMP NOT NULL,
  file_url STRING
);
```

### Schema Migration

```python
def create_or_update_table():
    """Create or update BigQuery table schema"""
    schema = [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("original_filename", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("file_path", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("file_size", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("upload_timestamp", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("file_url", "STRING", mode="NULLABLE"),
    ]
    
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    table = bigquery.Table(table_id, schema=schema)
    
    try:
        table = bigquery_client.create_table(table)
        print(f"Created table {table.table_id}")
    except Exception as e:
        print(f"Table already exists: {e}")
```

## 🧪 Testing Strategy

### Flutter Testing

#### Unit Tests
```dart
// test/api_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:mockito/mockito.dart';

class MockClient extends Mock implements http.Client {}

void main() {
  group('ApiService Tests', () {
    test('testConnection returns true on success', () async {
      final client = MockClient();
      
      when(client.get(Uri.parse('${ApiService.baseUrl}/')))
          .thenAnswer((_) async => http.Response('Hello, World!', 200));
      
      final result = await ApiService.testConnection();
      expect(result, true);
    });
    
    test('generateUploadUrl returns correct data', () async {
      // Test implementation
    });
  });
}
```

#### Widget Tests
```dart
// test/widget_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bigquery_sample_new/main.dart';

void main() {
  testWidgets('App has required buttons', (WidgetTester tester) async {
    await tester.pumpWidget(AudioUploadApp());
    
    expect(find.text('Test Connection'), findsOneWidget);
    expect(find.text('Pick Audio File'), findsOneWidget);
    expect(find.text('Upload to Cloud'), findsOneWidget);
    expect(find.text('Register in BigQuery'), findsOneWidget);
  });
}
```

### Python Testing

#### Unit Tests
```python
# tests/test_storage_handler.py
import pytest
from unittest.mock import Mock, patch
from storage_handler import StorageHandler

class TestStorageHandler:
    @patch('storage_handler.storage.Client')
    def test_generate_upload_url(self, mock_client):
        handler = StorageHandler()
        
        # Mock blob and bucket
        mock_blob = Mock()
        mock_blob.generate_signed_url.return_value = 'https://test-url.com'
        handler.bucket.blob.return_value = mock_blob
        
        result = handler.generate_upload_url('test.mp3', 'user123')
        
        assert 'upload_url' in result
        assert result['upload_url'] == 'https://test-url.com'
    
    def test_create_file_path(self):
        handler = StorageHandler()
        result = handler.create_file_path('user123', 'test.mp3')
        
        assert result.startswith('audio_files/user123_')
        assert result.endswith('_test.mp3')
```

#### Integration Tests
```python
# tests/test_api.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.data == b'Hello, World!'

def test_generate_upload_url(client):
    response = client.post('/generate_upload_url', 
                          json={'filename': 'test.mp3', 'user_id': 'test'})
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'upload_url' in data
    assert 'file_path' in data
```

## 🔄 Git Workflow

### Branch Strategy
```bash
# Main branch for production
main

# Development branch
develop

# Feature branches
feature/user-authentication
feature/batch-upload
feature/file-analytics

# Hotfix branches
hotfix/cors-issue
hotfix/storage-timeout
```

### Commit Convention
```bash
# Format: type(scope): description
feat(backend): add file list endpoint
fix(flutter): resolve file picker crash
docs(api): update endpoint documentation
refactor(storage): optimize upload performance
test(backend): add integration tests
```

### Pull Request Process
1. Create feature branch from `develop`
2. Implement feature with tests
3. Update documentation
4. Create pull request to `develop`
5. Code review and approval
6. Merge to `develop`
7. Deploy to staging for testing
8. Merge to `main` for production

## 🚀 Development Tools

### Recommended IDE Setup

#### VS Code Extensions
- Flutter
- Dart
- Python
- Google Cloud Code
- GitLens
- REST Client

#### VS Code Settings (`.vscode/settings.json`)
```json
{
  "dart.flutterSdkPath": "/path/to/flutter",
  "python.defaultInterpreterPath": "./python/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "files.associations": {
    "*.yaml": "yaml"
  }
}
```

### Debugging

#### Flutter Debugging
```bash
# Run with debugging
flutter run --debug

# Profile mode
flutter run --profile

# Debug specific device
flutter run -d chrome --debug
```

#### Python Debugging
```python
# Add to app.py for debugging
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### Performance Monitoring

#### Flutter Performance
```dart
// Add performance tracking
import 'dart:developer' as developer;

void trackPerformance(String operation, Function action) async {
  final stopwatch = Stopwatch()..start();
  
  try {
    await action();
  } finally {
    stopwatch.stop();
    developer.log('$operation took ${stopwatch.elapsedMilliseconds}ms');
  }
}
```

#### Backend Performance
```python
import time
from functools import wraps

def timing_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        end_time = time.time()
        
        app.logger.info(f"{f.__name__} took {end_time - start_time:.2f} seconds")
        return result
    return decorated_function

@app.route('/upload')
@timing_decorator
def upload_file():
    # Implementation
    pass
```

## 📈 Future Development Roadmap

### Phase 1: Core Enhancements
- [ ] User authentication system
- [ ] File validation improvements
- [ ] Progress indicators
- [ ] Error recovery mechanisms

### Phase 2: Advanced Features
- [ ] Batch file upload
- [ ] Audio file analysis
- [ ] Real-time notifications
- [ ] File sharing capabilities

### Phase 3: Analytics & Insights
- [ ] Usage analytics dashboard
- [ ] Audio processing pipeline
- [ ] Machine learning integration
- [ ] Automated transcription

### Phase 4: Enterprise Features
- [ ] Multi-tenant architecture
- [ ] Advanced security features
- [ ] API rate limiting
- [ ] Compliance reporting

## 🤝 Contributing Guidelines

### Code Style

#### Flutter/Dart
- Follow [Dart Style Guide](https://dart.dev/guides/language/effective-dart/style)
- Use meaningful variable names
- Add comments for complex logic
- Format code with `dart format`

#### Python
- Follow [PEP 8](https://pep8.org/)
- Use type hints
- Document functions with docstrings
- Format code with `black`

### Code Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Error handling implemented

---

This developer guide provides comprehensive information for working with the Healthcare Audio File Upload System codebase. For specific implementation questions, refer to the code comments and API documentation. 