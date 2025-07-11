# 🧪 **Complete Security Demo Test Guide**

This guide walks you through **testing every security feature** in your Flutter + Python + GCP healthcare app and seeing **real encrypted outputs**.

## 🎯 **TESTING OVERVIEW**

Your app now demonstrates these security layers:
- **Flutter App**: Real-time security status with visual feedback
- **Cloud Armor**: DDoS protection and malicious request blocking  
- **Security Middleware**: Rate limiting and input validation
- **Cloud DLP**: PHI detection and risk classification
- **Cloud KMS**: Sensitive data encryption
- **Audit Logging**: HIPAA compliance tracking

---

## 📱 **STEP 1: Test Flutter App with Security Features**

### **Run Your Enhanced Flutter App:**

```bash
# Navigate to your project directory
cd /Users/geopaulson/flutterprojects/bigquery_sample_new

# Get dependencies
flutter pub get

# Run the app on device/simulator
flutter run
```

### **Test Scenario 1: Normal Healthcare Data**

**Fill out the form with:**
```
Patient ID: PAT-567890
Operator Name: Dr. Emily Chen
Reason: Lung function assessment
Audio File: (pick any audio file)
```

**Expected Security Log Output in App:**
```
14:30:15 - Testing backend connection with security features
14:30:15 - ✅ Backend connection successful - Security middleware active
14:30:16 - 🔍 File picker opened with audio format validation
14:30:16 - ✅ Audio file validated: test_audio.mp3
14:30:16 - 🔐 Requesting KMS-encrypted upload URL
14:30:16 - ✅ Secure signed URL generated with Cloud Armor protection
14:30:17 - ✅ File uploaded to healthcare_audio_analyzer_fhir bucket
14:30:17 - 🔐 File encrypted at rest with Cloud KMS
14:30:17 - 🔍 Starting comprehensive security scan
14:30:17 - 📋 Patient ID will be encrypted with KMS
14:30:17 - 📋 Operator name will be encrypted with KMS
14:30:17 - 🔍 Running Cloud DLP scan for PHI detection...
14:30:18 - 🔍 Cloud DLP scan completed
14:30:18 - 📊 PHI detected: true
14:30:18 - ⚠️ Risk level: MEDIUM
14:30:18 - 📋 Audit log entry created for HIPAA compliance
14:30:18 - 💾 Data stored in healthcare_audio_data.fhir_resources
14:30:18 - 🔐 Sensitive data encrypted with KMS keys
```

**Expected App Response:**
```
✅ FHIR resources created with security! Bundle ID: 550e8400-e29b-41d4-a716-446655440000

🔍 Security Scan Results:
- PHI Detected: true
- Risk Level: MEDIUM
- Resources Created: 3
```

### **Test Scenario 2: High-Risk PHI Data**

**Fill out the form with HIGH-RISK data:**
```
Patient ID: 123-45-6789
Operator Name: Dr. John Smith, NPI: 1234567890
Reason: Patient has diabetes, DOB: 01/15/1980, SSN: 987-65-4321
```

**Expected Higher Security Response:**
```
🔍 Security Scan Results:
- PHI Detected: true
- Risk Level: HIGH
- Resources Created: 3
```

---

## 🛠️ **STEP 2: Test Backend Security via API**

### **Test Script: Complete Security Flow**

```bash
#!/bin/bash
# Save as test_security.sh and run: bash test_security.sh

echo "🏥 Healthcare Security Demo - Complete Flow Test"
echo "=============================================="

BACKEND_URL="https://data-api-887192895309.us-central1.run.app"

echo ""
echo "🔍 TEST 1: Backend Health Check"
echo "curl $BACKEND_URL/health"
curl -s $BACKEND_URL/health | jq .
echo ""

echo "🔐 TEST 2: PHI Detection & Encryption"
echo "Testing with sensitive healthcare data..."
curl -X POST $BACKEND_URL/register-upload-fhir \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "test_cardiac_audio.mp3",
    "file_size": 2048576,
    "file_type": "audio/mp3",
    "patient_id": "PAT-789012",
    "operator_name": "Dr. Sarah Johnson",
    "reason": "Cardiac consultation",
    "duration_seconds": 120
  }' | jq .
echo ""

echo "⚡ TEST 3: Rate Limiting Protection"
echo "Making rapid requests to test rate limiting..."
for i in {1..6}; do
  echo "Request $i:"
  curl -s -w "HTTP Status: %{http_code}\n" $BACKEND_URL/health -o /dev/null
  sleep 1
done
echo ""

echo "🛡️ TEST 4: Security Headers Check"
echo "Checking security headers..."
curl -I $BACKEND_URL/health
echo ""

echo "🔍 TEST 5: FHIR Resource Query (Audit Logged)"
echo "Querying FHIR resources (this access will be audit logged)..."
curl -s "$BACKEND_URL/fhir/Media?patient=PAT-789012" | jq .
echo ""

echo "🧪 TEST 6: Malicious Request Blocking"
echo "Testing XSS protection..."
curl -s -w "HTTP Status: %{http_code}\n" \
  "$BACKEND_URL/fhir/Media?patient=<script>alert('xss')</script>" \
  -o /dev/null
echo ""

echo "✅ Security Demo Complete!"
echo "Check your Cloud Console for audit logs and encrypted data."
```

**Run the test:**
```bash
# Make executable and run
chmod +x test_security.sh
./test_security.sh
```

---

## 🔍 **STEP 3: Verify Encrypted Data in BigQuery**

### **Query Your Encrypted Data:**

```sql
-- 1. View encrypted patient data
SELECT
  file_name,
  LENGTH(patient_id) as encrypted_patient_id_length,
  SUBSTR(patient_id, 1, 50) as encrypted_sample,
  JSON_EXTRACT_SCALAR(fhir_resource, '$.resourceType') as resource_type,
  created_at
FROM `app-audio-analyzer.healthcare_audio_data.fhir_resources`
WHERE patient_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 5;

-- Expected Output:
-- file_name: "test_cardiac_audio.mp3"
-- encrypted_patient_id_length: 156
-- encrypted_sample: "CiQAX8sF4xK9M2jHvYa8fK3nR7pQ1zM5bV4cD8wL0iU6eT9yN3hS..."
-- resource_type: "Bundle"
```

### **View Audit Logs:**

```sql
-- 2. Check HIPAA compliance audit trail
SELECT
  timestamp,
  jsonPayload.user_id,
  jsonPayload.event_type,
  jsonPayload.patient_id,
  jsonPayload.source_ip,
  jsonPayload.success
FROM `app-audio-analyzer.audit_logs._AllLogs_*`
WHERE 
  jsonPayload.compliance_category = 'HIPAA_PHI_ACCESS'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
ORDER BY timestamp DESC
LIMIT 10;

-- Expected Output:
-- timestamp: "2024-12-15 14:30:18.234 UTC"
-- user_id: "Dr. Sarah Johnson"
-- event_type: "FHIR_ACCESS"
-- patient_id: "PAT-789012"
-- source_ip: "192.168.1.100"
-- success: true
```

### **Monitor PHI Detection:**

```sql
-- 3. Check PHI detection statistics
SELECT
  JSON_EXTRACT_SCALAR(jsonPayload.additional_context, '$.risk_level') as risk_level,
  COUNT(*) as detection_count,
  MIN(timestamp) as first_detection,
  MAX(timestamp) as latest_detection
FROM `app-audio-analyzer.audit_logs._AllLogs_*`
WHERE 
  jsonPayload.event_type = 'PHI_DETECTION'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY risk_level
ORDER BY detection_count DESC;

-- Expected Output:
-- risk_level: "MEDIUM", detection_count: 3
-- risk_level: "HIGH", detection_count: 1
```

---

## 📊 **STEP 4: Monitor Security Dashboard**

### **Cloud Console Monitoring:**

1. **Visit Cloud Logging:**
   ```
   https://console.cloud.google.com/logs/query?project=app-audio-analyzer
   ```

2. **Search for security events:**
   ```
   resource.type="cloud_run_revision"
   jsonPayload.compliance_category="HIPAA_PHI_ACCESS"
   ```

3. **Monitor KMS key usage:**
   ```
   https://console.cloud.google.com/security/kms?project=app-audio-analyzer
   ```

4. **Check Cloud Armor rules:**
   ```
   https://console.cloud.google.com/net-security/securitypolicies?project=app-audio-analyzer
   ```

---

## 🎯 **STEP 5: Real-Time Security Testing**

### **1. Test Rate Limiting:**
```bash
# Rapid-fire requests (should trigger rate limiting)
for i in {1..50}; do
  curl -s -w "%{http_code} " https://data-api-887192895309.us-central1.run.app/health
done
echo ""

# Expected: First ~20 requests return 200, then 429 (Too Many Requests)
```

### **2. Test DLP PHI Detection:**
```bash
# High-risk PHI data
curl -X POST https://data-api-887192895309.us-central1.run.app/register-upload-fhir \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "sensitive_audio.mp3",
    "file_size": 1024,
    "file_type": "audio/mp3",
    "patient_id": "123-45-6789",
    "operator_name": "Dr. John Smith, NPI: 1234567890",
    "reason": "Patient has diabetes, DOB: 01/15/1980"
  }'

# Expected Response:
# {
#   "success": true,
#   "security_scan": {
#     "phi_detected": true,
#     "risk_level": "HIGH"
#   }
# }
```

### **3. Test Malicious Input Blocking:**
```bash
# XSS attempt
curl "https://data-api-887192895309.us-central1.run.app/fhir/Media?patient=<script>alert('xss')</script>"

# Expected: HTTP 403 Forbidden (blocked by Cloud Armor)
```

---

## 📋 **STEP 6: Expected Security Outputs**

### **1. Encrypted Patient ID Example:**
```
Original: "PAT-789012"
Encrypted: "CiQAX8sF4xK9M2jHvYa8fK3nR7pQ1zM5bV4cD8wL0iU6eT9yN3hS2A5gJ4kP7oL6mF8nQ4rE7tY1aS3dG9hJ2lK5nM8pR6wV..."
```

### **2. DLP Scan Results:**
```json
{
  "has_phi": true,
  "findings_count": 2,
  "risk_level": "MEDIUM",
  "classification": "SENSITIVE",
  "findings": [
    {
      "info_type": "PERSON_NAME",
      "likelihood": "VERY_LIKELY",
      "quote": "Dr. Sarah Johnson"
    },
    {
      "info_type": "MEDICAL_RECORD_NUMBER",
      "likelihood": "LIKELY", 
      "quote": "PAT-789012"
    }
  ]
}
```

### **3. Audit Log Entry:**
```json
{
  "timestamp": "2024-12-15T14:30:16.234Z",
  "event_type": "FHIR_ACCESS",
  "user_id": "Dr. Sarah Johnson",
  "patient_id": "PAT-789012",
  "action": "CREATE",
  "compliance_category": "HIPAA_PHI_ACCESS",
  "additional_context": {
    "phi_detected": true,
    "risk_level": "MEDIUM",
    "encryption_applied": true
  },
  "success": true
}
```

### **4. Security Headers:**
```http
HTTP/1.1 200 OK
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
X-HIPAA-Compliance: enabled
```

---

## ✅ **VERIFICATION CHECKLIST**

After running all tests, verify:

- [ ] **Flutter App Security Widget**: Shows real-time PHI detection and encryption status
- [ ] **Encrypted Data in BigQuery**: Patient IDs are long encrypted strings, not plain text
- [ ] **Audit Logs**: Every data access is logged with user attribution  
- [ ] **Rate Limiting**: Excessive requests return 429 status codes
- [ ] **PHI Detection**: DLP correctly identifies sensitive healthcare data
- [ ] **Malicious Blocking**: XSS/injection attempts return 403 Forbidden
- [ ] **KMS Encryption**: Sensitive data is encrypted before storage
- [ ] **FHIR Compliance**: Resources follow healthcare standards
- [ ] **Security Headers**: Proper security headers in HTTP responses
- [ ] **Cloud Monitoring**: Events appear in Cloud Console dashboards

---

## 🏥 **DEMO SCRIPT FOR PRESENTATION**

### **Complete 5-Minute Security Demo:**

```bash
echo "🏥 Healthcare Security Demo - Live Presentation"
echo "=============================================="

# 1. Show Flutter app with security features
echo "📱 DEMO 1: Flutter App Security Interface"
echo "- Open Flutter app"
echo "- Fill Patient ID: PAT-123456"
echo "- Fill Doctor: Dr. Demo"
echo "- Upload audio file"
echo "- Watch real-time security log"
echo ""

# 2. Show encrypted data in database
echo "🔐 DEMO 2: Encrypted Data Storage"
echo "SELECT file_name, LENGTH(patient_id), SUBSTR(patient_id, 1, 20) FROM healthcare_audio_data.fhir_resources LIMIT 3;"
echo ""

# 3. Show audit compliance
echo "📋 DEMO 3: HIPAA Audit Trail"
echo "SELECT timestamp, jsonPayload.user_id, jsonPayload.patient_id FROM audit_logs._AllLogs_* WHERE jsonPayload.compliance_category = 'HIPAA_PHI_ACCESS' ORDER BY timestamp DESC LIMIT 5;"
echo ""

# 4. Show PHI detection
echo "🔍 DEMO 4: PHI Detection in Action"
curl -X POST https://data-api-887192895309.us-central1.run.app/register-upload-fhir \
  -H "Content-Type: application/json" \
  -d '{"file_name": "demo.mp3", "file_size": 1024, "file_type": "audio/mp3", "patient_id": "DEMO-123", "operator_name": "Dr. Demo"}' | jq '.security_scan'
echo ""

# 5. Show rate limiting
echo "⚡ DEMO 5: Rate Limiting Protection"
for i in {1..5}; do curl -s -w "Status: %{http_code} " https://data-api-887192895309.us-central1.run.app/health -o /dev/null; done
echo ""

echo "✅ DEMO COMPLETE: Enterprise healthcare security in action!"
```

Your healthcare application now provides **real-time security visibility** with **enterprise-grade protection**! 🏥🔒🎯 