# Project-Specific Security Configuration

This document contains the **exact configuration commands** for your healthcare audio analyzer project using your specific infrastructure.

## 📋 Your Infrastructure Details ✅ CORRECTED

- **Project ID**: `app-audio-analyzer`
- **Dataset ID**: `healthcare_audio_data` ✅ (corrected from BigQuery console URL)
- **Table**: `fhir_resources`
- **Bucket Name**: `healthcare_audio_analyzer_fhir`

### 🔍 Quick Verification Commands

Before proceeding, verify your infrastructure:

```bash
# Set your project
gcloud config set project app-audio-analyzer

# Verify BigQuery dataset and table exist
bq ls app-audio-analyzer:healthcare_audio_data
bq show app-audio-analyzer:healthcare_audio_data.fhir_resources

# Verify bucket exists
gsutil ls gs://healthcare_audio_analyzer_fhir/

# Check current Cloud Run service
gcloud run services list --region=us-central1
```

**Expected Output:**
- ✅ Dataset: `healthcare_audio_data` 
- ✅ Table: `fhir_resources` with schema (resource_type, resource_id, fhir_resource, created_at, patient_id, file_name)
- ✅ Bucket: `healthcare_audio_analyzer_fhir`
- ✅ Cloud Run: `data-api` service

## 🔐 1. Cloud KMS Configuration

### Set up encryption for your specific bucket:

```bash
# Set your project
export PROJECT_ID="app-audio-analyzer"
export BUCKET_NAME="healthcare_audio_analyzer_fhir"
export LOCATION="us-central1"

# Grant KMS permissions to your service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:audio-upload-service@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:audio-upload-service@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudkms.admin"

# Enable KMS API
gcloud services enable cloudkms.googleapis.com

# The KMS keys will be created automatically by your application:
# - Key Ring: "healthcare-audio-keyring"
# - Crypto Key: "patient-data-key"
```

## 📋 2. Cloud Audit Logs Configuration

### Create audit log sink for your specific resources:

```bash
# Create BigQuery dataset for audit logs
bq mk --dataset \
    --location=$LOCATION \
    ${PROJECT_ID}:audit_logs

# Create audit log sink
gcloud logging sinks create healthcare-audit-sink \
    bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/audit_logs \
    --log-filter='
    (
        protoPayload.serviceName="storage.googleapis.com" AND
        protoPayload.resourceName:"healthcare_audio_analyzer_fhir"
    ) OR (
        protoPayload.serviceName="bigquery.googleapis.com" AND
        protoPayload.resourceName:"healthcare_audio_data.fhir_resources"
    ) OR (
        protoPayload.serviceName="run.googleapis.com"
    ) OR (
        jsonPayload.event_type!=null AND
        jsonPayload.compliance_category!=null
    )'

# Grant sink permissions
export SINK_SA=$(gcloud logging sinks describe healthcare-audit-sink --format="value(writerIdentity)")

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="${SINK_SA}" \
    --role="roles/bigquery.dataEditor"
```

## 🔍 3. Cloud DLP Configuration

### Set up DLP for your FHIR resources table:

```bash
# Grant DLP permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:audio-upload-service@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/dlp.user"

# Enable DLP API
gcloud services enable dlp.googleapis.com
```

### Create DLP job to scan your existing FHIR data:

```bash
# Create DLP scan job for your fhir_resources table
cat > dlp_job_config.json << EOF
{
  "inspectJob": {
    "inspectConfig": {
      "infoTypes": [
        {"name": "PERSON_NAME"},
        {"name": "PHONE_NUMBER"},
        {"name": "EMAIL_ADDRESS"},
        {"name": "US_SOCIAL_SECURITY_NUMBER"},
        {"name": "MEDICAL_RECORD_NUMBER"},
        {"name": "US_HEALTHCARE_NPI"}
      ],
      "minLikelihood": "POSSIBLE",
      "limits": {
        "maxFindingsPerRequest": 1000
      },
      "includeQuote": true
    },
    "storageConfig": {
      "bigQueryOptions": {
        "tableReference": {
          "projectId": "${PROJECT_ID}",
          "datasetId": "healthcare_audio_data",
          "tableId": "fhir_resources"
        },
        "identifyingFields": [
          {"name": "resource_id"},
          {"name": "file_name"}
        ],
        "rowsLimit": 1000
      }
    }
  }
}
EOF

# Run the DLP scan
gcloud dlp inspect projects/$PROJECT_ID --config-from-file=dlp_job_config.json
```

## 🛡️ 4. Cloud Armor Configuration

### Create security policy for your API:

```bash
# Create security policy
gcloud compute security-policies create healthcare-api-protection \
    --description="Protection for healthcare audio analyzer API"

# Add rate limiting rule (100 requests per minute per IP)
gcloud compute security-policies rules create 1000 \
    --security-policy=healthcare-api-protection \
    --expression="true" \
    --action=rate-based-ban \
    --rate-limit-threshold-count=100 \
    --rate-limit-threshold-interval-sec=60 \
    --ban-duration-sec=600 \
    --conform-action=allow \
    --exceed-action=deny-429 \
    --enforce-on-key=IP

# Block SQL injection targeting your FHIR endpoints
gcloud compute security-policies rules create 2000 \
    --security-policy=healthcare-api-protection \
    --expression="request.path.matches('/fhir/.*') && request.query.matches('.*union.*select.*')" \
    --action=deny-403 \
    --description="Block SQL injection on FHIR endpoints"

# Block XSS attempts on upload endpoints
gcloud compute security-policies rules create 3000 \
    --security-policy=healthcare-api-protection \
    --expression="request.path.matches('/.*upload.*') && request.query.matches('.*<script.*>.*')" \
    --action=deny-403 \
    --description="Block XSS on upload endpoints"

# Block suspicious file upload attempts
gcloud compute security-policies rules create 4000 \
    --security-policy=healthcare-api-protection \
    --expression="request.path.matches('/upload.*') && !request.headers['content-type'].matches('audio/.*|multipart/form-data')" \
    --action=deny-403 \
    --description="Block non-audio file uploads"

# Geographic restrictions (example: block from high-risk countries)
gcloud compute security-policies rules create 5000 \
    --security-policy=healthcare-api-protection \
    --expression="origin.region_code == 'CN' || origin.region_code == 'RU' || origin.region_code == 'KP'" \
    --action=deny-403 \
    --description="Block high-risk geographic regions"
```

## 🌐 5. VPC Service Controls

### Create service perimeter for your healthcare data:

```bash
# Get your organization ID
export ORG_ID=$(gcloud organizations list --format="value(name)" --filter="displayName:YOUR_ORG_NAME")

# Create access policy
gcloud access-context-manager policies create \
    --title="Healthcare Audio Analyzer Policy" \
    --organization=$ORG_ID

# Get policy ID
export POLICY_ID=$(gcloud access-context-manager policies list --format="value(name)")

# Create service perimeter
gcloud access-context-manager perimeters create healthcare_audio_perimeter \
    --title="Healthcare Audio Data Perimeter" \
    --resources=projects/$PROJECT_ID \
    --restricted-services=bigquery.googleapis.com,storage.googleapis.com,run.googleapis.com,cloudsql.googleapis.com \
    --policy=$POLICY_ID

# Create access level for trusted networks
gcloud access-context-manager levels create trusted_healthcare_networks \
    --title="Trusted Healthcare Networks" \
    --basic-level-spec=trusted_networks.yaml \
    --policy=$POLICY_ID
```

Create `trusted_networks.yaml`:
```yaml
conditions:
- ipSubnetworks:
  - "YOUR_OFFICE_IP/32"  # Replace with your office IP
  - "YOUR_VPN_RANGE/24"  # Replace with your VPN range
  devicePolicy:
    requireScreenlock: true
```

## 🛡️ 6. Security Command Center

### Enable and configure Security Command Center:

```bash
# Enable Security Command Center API
gcloud services enable securitycenter.googleapis.com

# Create Pub/Sub topic for security alerts
gcloud pubsub topics create healthcare-security-alerts

# Create notification channel
gcloud scc notifications create healthcare-phi-alerts \
    --organization=$ORG_ID \
    --pubsub-topic=projects/$PROJECT_ID/topics/healthcare-security-alerts \
    --filter='category="SENSITIVE_DATA_DETECTION" OR category="MALWARE" OR state="ACTIVE"'

# Set up email notifications (optional)
gcloud pubsub subscriptions create healthcare-alerts-email \
    --topic=healthcare-security-alerts \
    --push-endpoint=https://your-notification-webhook.com/alerts
```

## 📦 7. Binary Authorization & Artifact Registry

### Set up secure container deployment:

```bash
# Create Artifact Registry repository
gcloud artifacts repositories create healthcare-images \
    --repository-format=docker \
    --location=$LOCATION \
    --description="Healthcare audio analyzer container images"

# Configure Docker authentication
gcloud auth configure-docker ${LOCATION}-docker.pkg.dev

# Enable Binary Authorization
gcloud services enable binaryauthorization.googleapis.com

# Create attestor
gcloud container binauthz attestors create prod-attestor \
    --attestation-authority-note=projects/$PROJECT_ID/notes/prod-attestor-note \
    --attestation-authority-note-public-key-id=prod-key \
    --attestation-authority-note-public-key-ascii-armor-file=public_key.asc

# Create Binary Authorization policy
cat > binauthz_policy.yaml << EOF
defaultAdmissionRule:
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
  requireAttestationsBy:
  - projects/$PROJECT_ID/attestors/prod-attestor
admissionWhitelistPatterns:
- namePattern: ${LOCATION}-docker.pkg.dev/$PROJECT_ID/healthcare-images/*
EOF

gcloud container binauthz policy import binauthz_policy.yaml
```

## 🚀 8. Update Your Cloud Run Deployment

### Deploy with all security features enabled:

```bash
# Build and push secure image
docker build -t ${LOCATION}-docker.pkg.dev/$PROJECT_ID/healthcare-images/api:latest python/
docker push ${LOCATION}-docker.pkg.dev/$PROJECT_ID/healthcare-images/api:latest

# Deploy to Cloud Run with security configuration
gcloud run deploy data-api \
    --image=${LOCATION}-docker.pkg.dev/$PROJECT_ID/healthcare-images/api:latest \
    --platform=managed \
    --region=$LOCATION \
    --allow-unauthenticated \
    --set-env-vars="BUCKET_NAME=healthcare_audio_analyzer_fhir" \
    --set-env-vars="DATASET_ID=healthcare_audio_data" \
    --set-env-vars="TABLE_ID=audio_records" \
    --set-env-vars="FHIR_TABLE_ID=fhir_resources" \
    --set-env-vars="ENABLE_SECURITY_FEATURES=true" \
    --set-env-vars="KMS_LOCATION=us-central1" \
    --set-env-vars="DLP_ENABLED=true" \
    --memory=2Gi \
    --cpu=2 \
    --max-instances=10 \
    --vpc-connector=healthcare-vpc-connector
```

## 🔍 9. Test Security Implementation

### Test DLP with your FHIR data structure:

```bash
# Test PHI detection in FHIR resource
curl -X POST https://your-cloud-run-url/register-upload-fhir \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "patient_audio_20241215.mp3",
    "file_size": 2048576,
    "file_type": "audio/mp3",
    "patient_id": "PAT-123456",
    "operator_name": "Dr. Sarah Johnson",
    "reason": "Routine consultation recording"
  }'
```

### Test Cloud Armor protection:

```bash
# Test rate limiting
for i in {1..150}; do
  curl -s https://your-cloud-run-url/health > /dev/null &
done

# Test SQL injection blocking
curl "https://your-cloud-run-url/fhir/Media?patient='; DROP TABLE fhir_resources; --"

# Test XSS blocking
curl "https://your-cloud-run-url/upload?test=<script>alert('xss')</script>"
```

### Query your specific audit logs:

```sql
-- Query audit logs for your bucket and table
SELECT
  timestamp,
  severity,
  jsonPayload.event_type,
  jsonPayload.user_id,
  jsonPayload.resource_type,
  jsonPayload.patient_id,
  jsonPayload.action
FROM `app-audio-analyzer.audit_logs._AllLogs_*`
WHERE 
  jsonPayload.event_type IS NOT NULL
  AND (
    jsonPayload.resource_type = 'FHIR_RESOURCE' OR
    jsonPayload.resource_type = 'AUDIO_FILE'
  )
ORDER BY timestamp DESC
LIMIT 100;
```

### Query DLP findings in your FHIR table:

```sql
-- Check for PHI in your fhir_resources table
SELECT
  resource_id,
  file_name,
  patient_id,
  JSON_EXTRACT_SCALAR(fhir_resource, '$.resourceType') as resource_type,
  created_at
FROM `app-audio-analyzer.healthcare_audio_data.fhir_resources`
WHERE patient_id IS NOT NULL
ORDER BY created_at DESC;
```

## 📊 10. Monitoring Queries for Your Data

### Monitor PHI access in your system:

```sql
-- PHI access monitoring
SELECT
  DATE(timestamp) as access_date,
  jsonPayload.user_id,
  COUNT(*) as phi_access_count,
  COUNT(DISTINCT jsonPayload.patient_id) as unique_patients_accessed
FROM `app-audio-analyzer.audit_logs._AllLogs_*`
WHERE
  jsonPayload.compliance_category = 'HIPAA_PHI_ACCESS'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY access_date, jsonPayload.user_id
ORDER BY access_date DESC, phi_access_count DESC;
```

### Monitor your bucket security:

```sql
-- Storage access monitoring
SELECT
  protoPayload.authenticationInfo.principalEmail as user,
  protoPayload.methodName as action,
  COUNT(*) as action_count
FROM `app-audio-analyzer.audit_logs._AllLogs_*`
WHERE
  protoPayload.resourceName LIKE '%healthcare_audio_analyzer_fhir%'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY user, action
ORDER BY action_count DESC;
```

## 🔧 11. Environment-Specific Configuration

### Development Environment:
```bash
export ENV="development"
export ENABLE_DEBUG_LOGS="true"
export DLP_SAMPLE_RATE="0.1"  # Sample 10% of requests
```

### Production Environment:
```bash
export ENV="production"
export ENABLE_DEBUG_LOGS="false"
export DLP_SAMPLE_RATE="1.0"  # Scan 100% of requests
export ENFORCE_VPC_SC="true"
```

---

## ✅ CORRECTED Implementation Checklist

Using your **EXACT** infrastructure from BigQuery console:

- [ ] **Project**: `app-audio-analyzer`
- [ ] **Dataset**: `healthcare_audio_data` ✅ (corrected from BigQuery console)
- [ ] **Table**: `fhir_resources`
- [ ] **Bucket**: `healthcare_audio_analyzer_fhir`

### Security Implementation Steps:
- [ ] **KMS**: Configure encryption for `healthcare_audio_analyzer_fhir` bucket
- [ ] **Audit Logs**: Set up sink for `healthcare_audio_data.fhir_resources` table monitoring
- [ ] **DLP**: Scan existing data in `healthcare_audio_data.fhir_resources` table
- [ ] **Cloud Armor**: Protect FHIR endpoints and upload APIs
- [ ] **VPC SC**: Create perimeter around `app-audio-analyzer` project
- [ ] **Security Command Center**: Monitor PHI detection alerts
- [ ] **Binary Authorization**: Secure container deployment pipeline
- [ ] **Monitoring**: Set up dashboards for `healthcare_audio_data.fhir_resources` access

## 🔍 Verify Your Current Setup

### Check your current BigQuery data:
```bash
# View your FHIR resources table structure
bq show app-audio-analyzer:healthcare_audio_data.fhir_resources

# Count existing FHIR resources
bq query --use_legacy_sql=false \
"SELECT 
  resource_type,
  COUNT(*) as count 
FROM \`app-audio-analyzer.healthcare_audio_data.fhir_resources\` 
GROUP BY resource_type"

# Check recent uploads
bq query --use_legacy_sql=false \
"SELECT 
  file_name,
  patient_id,
  created_at,
  JSON_EXTRACT_SCALAR(fhir_resource, '$.resourceType') as resource_type
FROM \`app-audio-analyzer.healthcare_audio_data.fhir_resources\` 
ORDER BY created_at DESC 
LIMIT 10"
```

### Check your bucket contents:
```bash
# List recent files in your bucket
gsutil ls -l gs://healthcare_audio_analyzer_fhir/

# Check bucket configuration
gsutil lifecycle get gs://healthcare_audio_analyzer_fhir/
```

## 🎯 Next Steps

1. **Run the verification commands first** to confirm your setup
2. **Execute security configuration** using your corrected infrastructure details
3. **Test with sample FHIR data** to verify PHI detection works
4. **Monitor audit logs** for your specific `healthcare_audio_data.fhir_resources` table

### 🧪 Test Your Security Setup

```bash
# Test your actual API endpoint with real schema
curl -X POST https://data-api-887192895309.us-central1.run.app/register-upload-fhir \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "test_patient_audio_20241215.mp3",
    "file_size": 2048576,
    "file_type": "audio/mp3",
    "patient_id": "PAT-456789",
    "operator_name": "Dr. John Smith",
    "reason": "Follow-up consultation recording"
  }'

# Check if the data was inserted into your actual table
bq query --use_legacy_sql=false \
"SELECT 
  file_name,
  patient_id,
  JSON_EXTRACT_SCALAR(fhir_resource, '$.resourceType') as resource_type,
  created_at
FROM \`app-audio-analyzer.healthcare_audio_data.fhir_resources\` 
WHERE file_name = 'test_patient_audio_20241215.mp3'"
```

Your healthcare audio analyzer with **corrected infrastructure details** is now ready for enterprise-grade security! 🏥🔒

**All commands now use your EXACT setup:**
- ✅ Project: `app-audio-analyzer`
- ✅ Dataset: `healthcare_audio_data` 
- ✅ Table: `fhir_resources`
- ✅ Bucket: `healthcare_audio_analyzer_fhir` 