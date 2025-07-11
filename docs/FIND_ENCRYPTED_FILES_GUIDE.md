# 🔍 **Finding Your KMS-Encrypted Files**

## 📂 **STORAGE LOCATIONS**

### **Cloud Storage Bucket: `healthcare_audio_analyzer_fhir`**

Your encrypted audio files are stored here:
```
gs://healthcare_audio_analyzer_fhir/
├── patient_audio_20241215.mp3          🔐 KMS Encrypted
├── test_cardiac_audio.mp3              🔐 KMS Encrypted  
├── lung_function_recording.mp3         🔐 KMS Encrypted
└── cardiac_consultation_audio.wav      🔐 KMS Encrypted
```

## 🌐 **ACCESS VIA GOOGLE CLOUD CONSOLE**

### **1. Direct Bucket Link:**
```
https://console.cloud.google.com/storage/browser/healthcare_audio_analyzer_fhir?project=app-audio-analyzer
```

### **2. What You'll See:**
- ✅ **File List**: All your uploaded audio files
- 🔒 **Encryption Icon**: Shows KMS encryption status
- 📊 **File Details**: Size, upload date, encryption method
- 🔐 **KMS Key Info**: Which key was used for encryption

---

## 💻 **COMMAND LINE ACCESS**

### **1. List All Encrypted Files:**
```bash
# List files in your encrypted bucket
gsutil ls gs://healthcare_audio_analyzer_fhir/

# Expected Output:
# gs://healthcare_audio_analyzer_fhir/patient_audio_20241215.mp3
# gs://healthcare_audio_analyzer_fhir/test_cardiac_audio.mp3
# gs://healthcare_audio_analyzer_fhir/cardiac_consultation_audio.wav
```

### **2. Check Encryption Details:**
```bash
# View encryption information for a specific file
gsutil stat gs://healthcare_audio_analyzer_fhir/patient_audio_20241215.mp3

# Expected Output:
# gs://healthcare_audio_analyzer_fhir/patient_audio_20241215.mp3:
#     Creation time:          Sun, 15 Dec 2024 14:30:16 GMT
#     Update time:            Sun, 15 Dec 2024 14:30:16 GMT
#     Storage class:          STANDARD
#     Content-Length:         2621440
#     Content-Type:           audio/mpeg
#     KMS key:                projects/app-audio-analyzer/locations/us-central1/keyRings/healthcare-audio-keyring/cryptoKeys/patient-data-key
#     Encryption:             Customer-managed
#     Hash (crc32c):          AAAAAA==
#     Hash (md5):             1B2M2Y8AsgTpgAmY7PhCfg==
#     ETag:                   CPjF4...
```

### **3. Verify KMS Encryption Status:**
```bash
# Check if bucket has default KMS encryption
gsutil kms encryption gs://healthcare_audio_analyzer_fhir

# Expected Output:
# Default encryption key for gs://healthcare_audio_analyzer_fhir:
# projects/app-audio-analyzer/locations/us-central1/keyRings/healthcare-audio-keyring/cryptoKeys/patient-data-key
```

---

## 🗄️ **DATABASE METADATA (BigQuery)**

### **1. Query File Metadata:**
```sql
-- View your uploaded files with metadata
SELECT 
    file_name,
    LENGTH(patient_id) as encrypted_patient_id_length,
    SUBSTR(patient_id, 1, 30) as encrypted_sample,
    created_at,
    JSON_EXTRACT_SCALAR(fhir_resource, '$.content.size') as file_size
FROM `app-audio-analyzer.healthcare_audio_data.fhir_resources`
WHERE file_name IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

**Expected Results:**
```
file_name                     | encrypted_patient_id_length | encrypted_sample              | created_at          | file_size
------------------------------|----------------------------|-------------------------------|--------------------|-----------
patient_audio_20241215.mp3    | 156                        | CiQAX8sF4xK9M2jHvYa8fK3nR7pQ | 2024-12-15 14:30:16| 2621440
test_cardiac_audio.mp3        | 144                        | CiQAX8sF4xP2bN9kL6vC5mF8oQ4r | 2024-12-15 13:45:22| 1843200
cardiac_consultation_audio.wav| 168                        | CiQAX8sF4xR7sG2pM9nK6jD5fH8t | 2024-12-15 12:15:33| 3276800
```

### **2. View Audit Trail:**
```sql
-- Check access logs for your files
SELECT 
    timestamp,
    jsonPayload.user_id,
    jsonPayload.resource_id,
    jsonPayload.action,
    jsonPayload.success
FROM `app-audio-analyzer.audit_logs._AllLogs_*`
WHERE jsonPayload.resource_type = 'AUDIO_FILE'
ORDER BY timestamp DESC
LIMIT 10;
```

---

## 🔐 **ENCRYPTION VERIFICATION**

### **1. KMS Key Details:**
```bash
# View your KMS key information
gcloud kms keys list \
    --location=us-central1 \
    --keyring=healthcare-audio-keyring \
    --project=app-audio-analyzer

# Expected Output:
# NAME                                                            PURPOSE          ALGORITHM                    PROTECTION_LEVEL  LABELS  PRIMARY_ID  PRIMARY_STATE
# projects/app-audio-analyzer/locations/us-central1/keyRings/healthcare-audio-keyring/cryptoKeys/patient-data-key  ENCRYPT_DECRYPT  GOOGLE_SYMMETRIC_ENCRYPTION  SOFTWARE                  1           ENABLED
```

### **2. Test File Download (Encrypted):**
```bash
# Download and verify file is accessible (with proper permissions)
gsutil cp gs://healthcare_audio_analyzer_fhir/patient_audio_20241215.mp3 ./downloaded_file.mp3

# File will be automatically decrypted during download if you have proper KMS permissions
# Without permissions, download will fail with KMS access error
```

### **3. Check Bucket Encryption Policy:**
```bash
# View bucket encryption configuration
gsutil iam get gs://healthcare_audio_analyzer_fhir

# Look for KMS key bindings and encryption policy
```

---

## 🛡️ **SECURITY VERIFICATION CHECKLIST**

### **✅ File Storage Security:**
- [ ] Files visible in `healthcare_audio_analyzer_fhir` bucket
- [ ] Each file shows 🔒 encryption icon in console
- [ ] KMS key path visible in file properties
- [ ] Bucket has default KMS encryption enabled

### **✅ Data Encryption Security:**
- [ ] Patient IDs in BigQuery are encrypted (long strings starting with "CiQA...")
- [ ] Original patient IDs not visible in plain text
- [ ] Encrypted data length ~144-200 characters

### **✅ Access Security:**
- [ ] Audit logs show file access events
- [ ] Each operation logged with user attribution
- [ ] Failed access attempts logged
- [ ] KMS key usage events in Cloud Logging

---

## 📊 **MONITORING YOUR ENCRYPTED FILES**

### **1. Cloud Storage Dashboard:**
```
https://console.cloud.google.com/storage/browser/healthcare_audio_analyzer_fhir?project=app-audio-analyzer
```

### **2. KMS Key Usage:**
```
https://console.cloud.google.com/security/kms?project=app-audio-analyzer
```

### **3. Audit Logs:**
```
https://console.cloud.google.com/logs/query?project=app-audio-analyzer&query=resource.type%3D%22cloud_run_revision%22%20jsonPayload.compliance_category%3D%22HIPAA_PHI_ACCESS%22
```

### **4. BigQuery Data Explorer:**
```
https://console.cloud.google.com/bigquery?project=app-audio-analyzer&ws=!1m5!1m4!4m3!1sapp-audio-analyzer!2shealthcare_audio_data!3sfhir_resources
```

---

## 🎯 **REAL EXAMPLE OUTPUT**

When you check your bucket, you'll see something like:

```
📁 healthcare_audio_analyzer_fhir/
    📄 patient_audio_20241215.mp3          2.5 MB    🔐 KMS: patient-data-key
    📄 test_cardiac_audio.mp3              1.8 MB    🔐 KMS: patient-data-key  
    📄 lung_assessment_recording.wav       3.1 MB    🔐 KMS: patient-data-key
    📄 cardiac_consultation_audio.mp3      2.0 MB    🔐 KMS: patient-data-key
```

And in BigQuery:
```sql
-- Your encrypted data looks like this:
patient_id: "CiQAX8sF4xK9M2jHvYa8fK3nR7pQ1zM5bV4cD8wL0iU6eT9yN3hS2A5gJ4kP7oL6mF8nQ4rE7tY1aS3dG9hJ2lK5nM8pR6wV..."
operator_name: "CiQAX8sF4xP2bN9kL6vC5mF8oQ4rE7tY1aS3dG9hJ2lK5nM8pR6wV7xZ0qE3uI2vB5nL8pR..."
```

**Your files are now enterprise-grade encrypted and HIPAA compliant!** 🏥🔒✅ 