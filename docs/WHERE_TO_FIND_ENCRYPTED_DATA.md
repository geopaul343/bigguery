# Where to Find Your Encrypted Data

## 🔍 Two Types of Encryption in Your System

### 1. **Encrypted Data Strings (in BigQuery)**
**Location**: BigQuery table `app-audio-analyzer.healthcare_audio_data.fhir_resources`

**What gets encrypted**: Patient IDs and operator names are encrypted using Cloud KMS and stored as encrypted strings like:
```
CiQAX8sF4xK9M2jHvYa8fK3nR7pQ1zM5bV4cD8wL0iU6eT9yN3hS4A8bC2dF5gH7jK9mN1qR3tV6wY8zA0cE4fH9jL2mP5rS7uX9zA2cF5hI8kN0pS3vY6zB9eH1jM4oQ7tW0yC3fI6lO9rU2xA5dG8kN1qT4wZ7cF0jM3pS6vY9zC2fH5kN8qU1tX4wA7dJ0mP3sV6yB9eH2kN5qT8wZ1dG4jM7pS0vY3zA6fI9lO2rU5xA8dK1nQ4tW7yC0fH3jM6pS9vY2zA5dH8kN1qT4wZ7cF0jM3pS6vY9zC2fH5kN8qU1tX4wA7dJ0mP3sV6yB9eH2k
```

### 2. **KMS-Encrypted Files at Rest (in Cloud Storage)**
**Location**: Cloud Storage bucket `healthcare_audio_analyzer_fhir`

**What gets encrypted**: Audio files are encrypted by Google Cloud KMS at rest, but they appear as normal files in the bucket.

---

## 🔍 How to Find Encrypted Data Strings

### Method 1: Using Google Cloud Console
1. Go to [BigQuery Console](https://console.cloud.google.com/bigquery)
2. Navigate to your project: `app-audio-analyzer`
3. Open dataset: `healthcare_audio_data`
4. Open table: `fhir_resources`
5. Click "Preview" tab
6. Look for columns with encrypted data strings

### Method 2: Using BigQuery SQL Query
```sql
SELECT 
    file_name,
    patient_id,
    resource_id,
    created_at,
    SUBSTR(fhir_resource, 1, 100) as encrypted_data_sample
FROM `app-audio-analyzer.healthcare_audio_data.fhir_resources`
WHERE patient_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

### Method 3: Using the Python API
```python
from google.cloud import bigquery

# Initialize BigQuery client
client = bigquery.Client(project='app-audio-analyzer')

# Query encrypted data
query = """
SELECT file_name, patient_id, resource_id, created_at, fhir_resource
FROM `app-audio-analyzer.healthcare_audio_data.fhir_resources`
WHERE patient_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 5
"""

query_job = client.query(query)
results = query_job.result()

for row in results:
    print(f"File: {row.file_name}")
    print(f"Patient ID: {row.patient_id}")
    print(f"Encrypted Data: {row.fhir_resource[:100]}...")
    print("---")
```

---

## 🔍 How to Find KMS-Encrypted Files

### Method 1: Using Google Cloud Console
1. Go to [Cloud Storage Console](https://console.cloud.google.com/storage)
2. Open bucket: `healthcare_audio_analyzer_fhir`
3. Files appear normal but are KMS-encrypted at rest
4. Click on any file → "Edit metadata" → Look for "KMS key name"

### Method 2: Check KMS Encryption Status
```python
from google.cloud import storage

# Initialize client
client = storage.Client()
bucket = client.bucket('healthcare_audio_analyzer_fhir')

# List files and check encryption
for blob in bucket.list_blobs():
    print(f"File: {blob.name}")
    print(f"KMS Key: {blob.kms_key_name}")
    print(f"Encrypted: {'Yes' if blob.kms_key_name else 'No'}")
    print("---")
```

---

## 🔍 Quick Commands to Find Your Encrypted Data

### 1. Find Recent Encrypted Records
```bash
# Using gcloud CLI
gcloud alpha bq query --use_legacy_sql=false \
  'SELECT file_name, patient_id, SUBSTR(fhir_resource, 1, 50) as encrypted_sample 
   FROM `app-audio-analyzer.healthcare_audio_data.fhir_resources` 
   WHERE patient_id IS NOT NULL 
   ORDER BY created_at DESC 
   LIMIT 5'
```

### 2. List KMS-Encrypted Files
```bash
# List files in bucket
gsutil ls gs://healthcare_audio_analyzer_fhir/

# Check encryption status of specific file
gsutil stat gs://healthcare_audio_analyzer_fhir/your-file-name.wav
```

### 3. Verify KMS Keys Are Being Used
```bash
# List KMS keys
gcloud kms keys list --location=us-central1 --keyring=healthcare-audio-keyring
```

---

## 🔍 What You Should See

### In BigQuery (`fhir_resources` table):
- `patient_id`: May contain encrypted string if PHI was detected
- `fhir_resource`: JSON containing encrypted patient identifiers
- `resource_id`: FHIR resource identifiers
- `created_at`: Timestamp when data was encrypted and stored

### In Cloud Storage (`healthcare_audio_analyzer_fhir` bucket):
- Files appear as normal `.wav`, `.mp3`, etc.
- But they're encrypted at rest using your KMS key
- Metadata shows KMS key name: `projects/app-audio-analyzer/locations/us-central1/keyRings/healthcare-audio-keyring/cryptoKeys/patient-data-key`

---

## 🔍 Troubleshooting

### If you don't see encrypted data:
1. **Check if you uploaded data through the Flutter app** (not just file upload)
2. **Verify the security pipeline is working** by checking logs
3. **Ensure KMS keys are properly configured**

### If BigQuery table is empty:
1. Check if the upload went through the `/register-upload-fhir` endpoint
2. Verify BigQuery permissions
3. Check application logs for errors

### If files aren't KMS-encrypted:
1. Verify KMS keys were created successfully
2. Check if bucket default encryption is set to KMS
3. Ensure proper IAM permissions for KMS

---

## 🔍 Example Expected Output

**BigQuery Encrypted Data:**
```json
{
  "file_name": "patient_audio_20241210_143022.wav",
  "patient_id": "CiQAX8sF4xK9M2jHvYa8fK3nR7pQ1zM5bV4cD8wL0iU6eT9yN3hS...",
  "resource_id": "audio-bundle-12345",
  "fhir_resource": "{\"resourceType\":\"Bundle\",\"id\":\"audio-bundle-12345\",\"entry\":[{\"resource\":{\"resourceType\":\"Patient\",\"id\":\"CiQAX8sF4xK9M2jHvYa8...\"}}]}"
}
```

**Cloud Storage File with KMS:**
```
File: patient_audio_20241210_143022.wav
Size: 2.3 MB
KMS Key: projects/app-audio-analyzer/locations/us-central1/keyRings/healthcare-audio-keyring/cryptoKeys/patient-data-key
Encrypted: Yes
```

The encrypted data strings are the long base64-encoded values you see in BigQuery, while the files in Cloud Storage are transparently encrypted by Google Cloud KMS. 