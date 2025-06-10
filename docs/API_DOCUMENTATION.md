# API Documentation

## Base URL
**Production**: `https://data-api-887192895309.us-central1.run.app`  
**Development**: `http://localhost:5000`

## Authentication
Currently, no authentication is required. For production deployment, consider implementing:
- API keys
- JWT tokens
- OAuth 2.0

## Endpoints

### 1. Health Check

**GET** `/`

Check if the API is running.

**Response:**
```
Hello, World!
```

**Status Codes:**
- `200 OK`: Service is running

---

### 2. Generate Upload URL

**POST** `/generate_upload_url`

Generate a signed URL for uploading files directly to Google Cloud Storage.

**Request Body:**
```json
{
  "filename": "audio_recording.mp3",
  "user_id": "user_12345"
}
```

**Request Headers:**
```
Content-Type: application/json
```

**Response:**
```json
{
  "upload_url": "https://storage.googleapis.com/healthcare_audio_analyzer_fhir/audio_files/user_12345_20241215_143022_audio_recording.mp3?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=...",
  "file_path": "audio_files/user_12345_20241215_143022_audio_recording.mp3"
}
```

**Status Codes:**
- `200 OK`: URL generated successfully
- `400 Bad Request`: Missing or invalid parameters
- `500 Internal Server Error`: Server error

**Usage Example:**
```bash
curl -X POST https://data-api-887192895309.us-central1.run.app/generate_upload_url \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "my_audio.mp3",
    "user_id": "user123"
  }'
```

---

### 3. Register File in BigQuery

**POST** `/register_file`

Register uploaded file metadata in BigQuery for tracking and analytics.

**Request Body:**
```json
{
  "user_id": "user_12345",
  "filename": "audio_recording.mp3",
  "file_path": "audio_files/user_12345_20241215_143022_audio_recording.mp3",
  "file_size": 2048576
}
```

**Request Headers:**
```
Content-Type: application/json
```

**Response:**
```json
{
  "message": "File registered successfully",
  "bigquery_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes:**
- `200 OK`: File registered successfully
- `400 Bad Request`: Missing or invalid parameters
- `500 Internal Server Error`: Database error

**Usage Example:**
```bash
curl -X POST https://data-api-887192895309.us-central1.run.app/register_file \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "filename": "my_audio.mp3",
    "file_path": "audio_files/user123_20241215_143022_my_audio.mp3",
    "file_size": 1048576
  }'
```

---

### 4. Team Upload Interface

**GET** `/team_upload`

Web interface for team members to upload files through a browser.

**Response:**
HTML page with upload form

**Status Codes:**
- `200 OK`: Page loaded successfully

**Features:**
- Drag & drop file upload
- Multiple file selection
- Upload progress indicators
- Real-time status updates

---

### 5. Direct File Upload (Team Interface)

**POST** `/upload`

Direct file upload endpoint used by the team interface.

**Request:**
```
Content-Type: multipart/form-data

Form data:
- audio: [file]
- user_id: string
```

**Response:**
```json
{
  "message": "File uploaded successfully",
  "filename": "user_12345_20241215_143022_audio_recording.mp3",
  "gcs_url": "gs://healthcare_audio_analyzer_fhir/audio_files/user_12345_20241215_143022_audio_recording.mp3",
  "bigquery_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes:**
- `200 OK`: File uploaded successfully
- `400 Bad Request`: No file or invalid parameters
- `500 Internal Server Error`: Upload error

---

### 6. Convert to FHIR

**POST** `/convert_to_fhir`

Convert audio file metadata to FHIR format.

**Request Body:**
```json
{
  "user_id": "user_12345",
  "filename": "audio_recording.mp3",
  "file_size": 2048576,
  "upload_timestamp": "2024-12-15T14:30:22Z"
}
```

**Response:**
```json
{
  "fhir_resource": {
    "resourceType": "Media",
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "type": {
      "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/media-type",
        "code": "audio",
        "display": "Audio"
      }]
    },
    "subject": {
      "reference": "Patient/user_12345"
    },
    "createdDateTime": "2024-12-15T14:30:22Z",
    "content": {
      "contentType": "audio/mpeg",
      "url": "gs://healthcare_audio_analyzer_fhir/audio_files/user_12345_20241215_143022_audio_recording.mp3",
      "size": 2048576
    }
  }
}
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "error": "Error message",
  "details": "Additional error details",
  "timestamp": "2024-12-15T14:30:22Z"
}
```

### Common Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Endpoint doesn't exist |
| 413 | Payload Too Large - File size exceeds limit |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Temporary service issue |

## Rate Limiting

Currently no rate limiting is implemented. For production, consider:
- Request rate limits per user/IP
- File upload size limits
- Concurrent upload limits

## Data Models

### Upload URL Request
```typescript
interface UploadUrlRequest {
  filename: string;    // Original filename with extension
  user_id: string;     // User identifier
}
```

### Upload URL Response
```typescript
interface UploadUrlResponse {
  upload_url: string;  // Signed URL for upload
  file_path: string;   // Storage path in bucket
}
```

### File Registration Request
```typescript
interface FileRegistrationRequest {
  user_id: string;     // User identifier
  filename: string;    // Original filename
  file_path: string;   // Storage path from upload URL response
  file_size: number;   // File size in bytes
}
```

### File Registration Response
```typescript
interface FileRegistrationResponse {
  message: string;     // Success message
  bigquery_id: string; // Unique record ID in BigQuery
}
```

## Integration Examples

### Flutter Integration

```dart
class ApiService {
  static const String baseUrl = 'https://data-api-887192895309.us-central1.run.app';
  
  // Generate upload URL
  static Future<Map<String, dynamic>> generateUploadUrl(
    String filename, 
    String userId
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/generate_upload_url'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'filename': filename,
        'user_id': userId,
      }),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to generate upload URL');
    }
  }
  
  // Register file in BigQuery
  static Future<Map<String, dynamic>> registerFile(
    String userId,
    String filename,
    String filePath,
    int fileSize,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/register_file'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'user_id': userId,
        'filename': filename,
        'file_path': filePath,
        'file_size': fileSize,
      }),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to register file');
    }
  }
}
```

### JavaScript/Web Integration

```javascript
class AudioUploadAPI {
  constructor(baseUrl = 'https://data-api-887192895309.us-central1.run.app') {
    this.baseUrl = baseUrl;
  }
  
  async generateUploadUrl(filename, userId) {
    const response = await fetch(`${this.baseUrl}/generate_upload_url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        filename: filename,
        user_id: userId,
      }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to generate upload URL');
    }
    
    return await response.json();
  }
  
  async uploadFile(uploadUrl, file) {
    const response = await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to upload file');
    }
    
    return response;
  }
  
  async registerFile(userId, filename, filePath, fileSize) {
    const response = await fetch(`${this.baseUrl}/register_file`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        filename: filename,
        file_path: filePath,
        file_size: fileSize,
      }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to register file');
    }
    
    return await response.json();
  }
}
```

## Testing

### Unit Tests

Test each endpoint with various inputs and edge cases:

```bash
# Health check
curl -X GET https://data-api-887192895309.us-central1.run.app/

# Upload URL generation
curl -X POST https://data-api-887192895309.us-central1.run.app/generate_upload_url \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.mp3","user_id":"test_user"}'

# File registration
curl -X POST https://data-api-887192895309.us-central1.run.app/register_file \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","filename":"test.mp3","file_path":"audio_files/test.mp3","file_size":1024}'
```

### Load Testing

Use tools like Apache Bench or Artillery for load testing:

```bash
# Test concurrent requests
ab -n 100 -c 10 https://data-api-887192895309.us-central1.run.app/
```

## Monitoring

Monitor these metrics in production:
- Response times per endpoint
- Error rates
- File upload success rates
- BigQuery write latencies
- Storage usage

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-15 | Initial API implementation |

---

For additional support, refer to the main README.md or create an issue in the GitHub repository. 