# Healthcare Security Implementation Guide

This guide provides step-by-step instructions for implementing comprehensive security controls in your healthcare audio file upload system using Google Cloud security services.

## 🏗️ Architecture Overview

Your healthcare application now includes:
- **Frontend**: Flutter app (mobile/web)
- **Backend**: Python Flask API on Cloud Run
- **Data Storage**: Cloud Storage (audio files), BigQuery (metadata), Cloud SQL (relational data)
- **FHIR Compliance**: Healthcare interoperability standards

## 🔐 1. Cloud KMS - Encryption Key Management

### Implementation Status: ✅ IMPLEMENTED

**What it does**: Manages encryption keys and encrypts sensitive data at rest.

**Features added**:
- Automatic key ring and crypto key creation
- Patient ID and operator name encryption
- Cloud Storage bucket encryption
- Sensitive data encryption/decryption methods

**Configuration**:
```bash
# Grant KMS permissions to your service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
    --role="roles/cloudkms.admin"
```

## 📋 2. Cloud Audit Logs - Immutable Activity Logs

### Implementation Status: ✅ IMPLEMENTED

**What it does**: Creates immutable logs of all admin and data access activities for HIPAA compliance.

**Features added**:
- Healthcare data access logging
- FHIR resource access tracking
- Authentication event logging
- Admin action logging
- Structured logging with compliance labels

**Configuration**:
```bash
# Enable audit logs for all services
gcloud logging sinks create healthcare-audit-sink \
    bigquery.googleapis.com/projects/YOUR_PROJECT_ID/datasets/audit_logs \
    --log-filter='protoPayload.serviceName="storage.googleapis.com" OR 
                 protoPayload.serviceName="bigquery.googleapis.com" OR
                 protoPayload.serviceName="run.googleapis.com" OR
                 jsonPayload.event_type!=null'
```

## 🛡️ 3. VPC Service Controls - Network Isolation

### Implementation Status: ⚙️ SETUP REQUIRED

**What it does**: Creates secure perimeters around your healthcare data to prevent data exfiltration.

**Setup Instructions**:

1. **Create Service Perimeter**:
```bash
# Create access policy
gcloud access-context-manager policies create \
    --title="Healthcare Data Policy" \
    --organization=YOUR_ORG_ID

# Get policy ID
POLICY_ID=$(gcloud access-context-manager policies list --format="value(name)")

# Create service perimeter
gcloud access-context-manager perimeters create healthcare_perimeter \
    --title="Healthcare Data Perimeter" \
    --resources=projects/YOUR_PROJECT_ID \
    --restricted-services=bigquery.googleapis.com,storage.googleapis.com,run.googleapis.com \
    --policy=$POLICY_ID
```

2. **Configure Ingress/Egress Rules**:
```bash
# Allow access from your IP ranges
gcloud access-context-manager perimeters update healthcare_perimeter \
    --add-ingress-policies=ingress_policy.yaml \
    --policy=$POLICY_ID
```

Create `ingress_policy.yaml`:
```yaml
- ingressFrom:
    sources:
    - accessLevel: projects/YOUR_PROJECT_ID/accessPolicies/$POLICY_ID/accessLevels/trusted_networks
  ingressTo:
    resources:
    - projects/YOUR_PROJECT_ID
    operations:
    - serviceName: bigquery.googleapis.com
    - serviceName: storage.googleapis.com
```

## 🛡️ 4. Cloud Armor - API Protection

### Implementation Status: ✅ IMPLEMENTED (Code) + ⚙️ SETUP REQUIRED (Infrastructure)

**What it does**: Protects your APIs from DDoS attacks, SQL injection, XSS, and other web-based attacks.

**Features added**:
- Request validation middleware
- Rate limiting per IP
- Malicious pattern detection
- Healthcare-specific request validation
- Security headers

**Infrastructure Setup**:

1. **Create Security Policy**:
```bash
# Create the security policy
gcloud compute security-policies create healthcare-api-protection \
    --description="Healthcare API protection policy"

# Add rate limiting rule
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

# Block SQL injection attempts
gcloud compute security-policies rules create 2000 \
    --security-policy=healthcare-api-protection \
    --expression="request.query.matches('.*union.*select.*')" \
    --action=deny-403 \
    --description="Block SQL injection attempts"

# Block XSS attempts
gcloud compute security-policies rules create 3000 \
    --security-policy=healthcare-api-protection \
    --expression="request.query.matches('.*<script.*>.*')" \
    --action=deny-403 \
    --description="Block XSS attempts"
```

2. **Set up Load Balancer and attach policy**:
```bash
# Create load balancer (if not exists)
gcloud compute url-maps create healthcare-api-lb \
    --default-service=YOUR_BACKEND_SERVICE

# Attach security policy
gcloud compute backend-services update YOUR_BACKEND_SERVICE \
    --security-policy=healthcare-api-protection \
    --global
```

## 🔍 5. Cloud DLP - Data Loss Prevention

### Implementation Status: ✅ IMPLEMENTED

**What it does**: Automatically detects, classifies, and redacts sensitive healthcare information (PHI).

**Features added**:
- PHI detection in text content
- FHIR resource scanning
- Data classification (PUBLIC, SENSITIVE, HIGHLY_SENSITIVE)
- Automatic redaction capabilities
- Healthcare-specific info types (SSN, Medical Record Numbers, etc.)

**Setup**:
```bash
# Grant DLP permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
    --role="roles/dlp.user"
```

## 🔒 6. Shielded VMs / Confidential VMs

### Implementation Status: ⚙️ SETUP REQUIRED

**What it does**: Provides verified boot and runtime protection for your compute instances.

**Setup for Cloud Run** (Recommended):
Your application runs on Cloud Run which provides built-in security. For additional VM-level security:

**Setup for Custom VMs** (If needed):
```bash
# Create Shielded VM
gcloud compute instances create healthcare-secure-vm \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --machine-type=e2-standard-2 \
    --zone=us-central1-a
```

**For Confidential Computing**:
```bash
# Create Confidential VM
gcloud compute instances create healthcare-confidential-vm \
    --image-family=ubuntu-2004-lts \
    --image-project=confidential-vm-images \
    --machine-type=n2d-standard-2 \
    --confidential-compute \
    --zone=us-central1-a
```

## 🛡️ 7. Security Command Center

### Implementation Status: ⚙️ SETUP REQUIRED

**What it does**: Centralized threat detection and security posture management.

**Setup**:
```bash
# Enable Security Command Center API
gcloud services enable securitycenter.googleapis.com

# Grant Security Command Center permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
    --role="roles/securitycenter.admin"
```

**Configure Notifications**:
```bash
# Create notification config
gcloud scc notifications create healthcare-security-alerts \
    --organization=YOUR_ORG_ID \
    --pubsub-topic=projects/YOUR_PROJECT_ID/topics/security-alerts \
    --filter="state=\"ACTIVE\" AND category=\"MALWARE\""
```

## 📦 8. Artifact Registry + Binary Authorization

### Implementation Status: ⚙️ SETUP REQUIRED

**What it does**: Ensures only verified and scanned container images are deployed.

**Setup Artifact Registry**:
```bash
# Create repository
gcloud artifacts repositories create healthcare-images \
    --repository-format=docker \
    --location=us-central1 \
    --description="Healthcare application container images"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

**Setup Binary Authorization**:
```bash
# Enable Binary Authorization
gcloud services enable binaryauthorization.googleapis.com

# Create policy
cat > policy.yaml << EOF
admissionWhitelistPatterns:
- namePattern: us-central1-docker.pkg.dev/YOUR_PROJECT_ID/healthcare-images/*
defaultAdmissionRule:
  requireAttestationsBy:
  - projects/YOUR_PROJECT_ID/attestors/prod-attestor
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
EOF

gcloud container binauthz policy import policy.yaml
```

**Build and Deploy Secure Images**:
```bash
# Build with vulnerability scanning
gcloud builds submit --config=cloudbuild-secure.yaml .
```

Create `cloudbuild-secure.yaml`:
```yaml
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/healthcare-images/api:$SHORT_SHA', '.']
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/healthcare-images/api:$SHORT_SHA']
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: 'bash'
  args:
  - '-c'
  - |
    gcloud container images scan us-central1-docker.pkg.dev/$PROJECT_ID/healthcare-images/api:$SHORT_SHA
```

## 🚀 Deployment Checklist

### Pre-deployment Security Checklist:

- [ ] **KMS**: Encryption keys created and storage configured
- [ ] **Audit Logs**: Logging sink configured and tested
- [ ] **VPC Service Controls**: Perimeter created with proper access rules
- [ ] **Cloud Armor**: Security policy created and attached to load balancer
- [ ] **DLP**: Inspection templates created and tested
- [ ] **Shielded VMs**: VMs configured with security features (if using VMs)
- [ ] **Security Command Center**: Notifications configured
- [ ] **Binary Authorization**: Policy configured and attestors created

### Environment Variables:
Add these to your Cloud Run service:
```bash
gcloud run services update data-api \
    --set-env-vars="ENABLE_SECURITY_FEATURES=true" \
    --set-env-vars="KMS_LOCATION=us-central1" \
    --set-env-vars="DLP_ENABLED=true" \
    --region=us-central1
```

### Monitoring and Alerts:
```bash
# Create uptime check
gcloud monitoring uptime-check-configs create \
    --config-from-file=uptime-check.yaml

# Create alerting policy
gcloud alpha monitoring policies create \
    --policy-from-file=alert-policy.yaml
```

## 🔍 Testing Security Implementation

1. **Test DLP Detection**:
```bash
curl -X POST https://your-api-url/register-upload-fhir \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "test.mp3",
    "file_size": 1000,
    "file_type": "audio/mp3",
    "patient_id": "PAT-123456",
    "operator_name": "Dr. John Smith"
  }'
```

2. **Test Rate Limiting**:
```bash
# Run multiple requests rapidly to test rate limiting
for i in {1..150}; do
  curl https://your-api-url/health &
done
```

3. **Test Malicious Content Blocking**:
```bash
curl "https://your-api-url/health?test=<script>alert('xss')</script>"
```

## 🏥 HIPAA Compliance Features

The implemented security controls address these HIPAA requirements:

| HIPAA Requirement | Implementation |
|-------------------|----------------|
| **Access Control** | KMS encryption, VPC Service Controls |
| **Audit Controls** | Cloud Audit Logs, comprehensive logging |
| **Integrity** | Binary Authorization, Shielded VMs |
| **Transmission Security** | HTTPS, Cloud Armor protection |
| **Data Backup** | Cloud Storage with KMS encryption |
| **Access Management** | IAM roles, VPC perimeters |
| **Assigned Security** | Security Command Center |

## 🔧 Maintenance Tasks

### Weekly:
- [ ] Review audit logs for unusual access patterns
- [ ] Check Security Command Center for new findings
- [ ] Review DLP scanning results

### Monthly:
- [ ] Rotate KMS keys (if required by policy)
- [ ] Review and update Cloud Armor rules
- [ ] Update container images with latest security patches
- [ ] Review VPC Service Controls access patterns

### Quarterly:
- [ ] Security posture assessment
- [ ] Update DLP detection rules
- [ ] Review and test disaster recovery procedures

## 📞 Emergency Response

In case of security incident:

1. **Immediate**: Check Security Command Center for alerts
2. **Investigate**: Query audit logs for affected resources
3. **Contain**: Use VPC Service Controls to isolate compromised resources
4. **Recovery**: Use encrypted backups from Cloud Storage
5. **Report**: Generate compliance reports from audit logs

## 🔗 Additional Resources

- [Google Cloud Security Best Practices](https://cloud.google.com/security/best-practices)
- [HIPAA Compliance on Google Cloud](https://cloud.google.com/security/compliance/hipaa)
- [Healthcare Data Protection](https://cloud.google.com/solutions/healthcare-life-sciences) 