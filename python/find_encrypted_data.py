#!/usr/bin/env python3
"""
Script to help locate encrypted data in your Google Cloud infrastructure
"""
import os
import json
from google.cloud import bigquery
from google.cloud import storage
from generate_token import generate_token
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_encrypted_data_in_bigquery():
    """Find encrypted data in BigQuery tables"""
    print("🔍 Searching for encrypted data in BigQuery...")
    
    try:
        # Initialize BigQuery client
        credentials, project_id = generate_token()
        client = bigquery.Client(credentials=credentials, project=project_id)
        
        # Query for encrypted data
        query = """
        SELECT 
            file_name,
            patient_id,
            resource_id,
            created_at,
            SUBSTR(fhir_resource, 1, 100) as encrypted_data_sample
        FROM `app-audio-analyzer.healthcare_audio_data.fhir_resources`
        WHERE patient_id IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 10
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        print("\n📊 ENCRYPTED DATA FOUND IN BIGQUERY:")
        print("=" * 60)
        
        found_data = False
        for row in results:
            found_data = True
            print(f"🔐 File: {row.file_name}")
            print(f"📅 Created: {row.created_at}")
            print(f"🆔 Resource ID: {row.resource_id}")
            print(f"🔒 Encrypted Patient ID: {row.patient_id}")
            print(f"📝 Encrypted Data Sample: {row.encrypted_data_sample}...")
            print("-" * 60)
        
        if not found_data:
            print("❌ No encrypted data found in BigQuery")
            print("💡 This could mean:")
            print("   - No data has been uploaded through the Flutter app")
            print("   - Data was uploaded but not through the secure /register-upload-fhir endpoint")
            print("   - KMS encryption is not working properly")
            
    except Exception as e:
        print(f"❌ Error accessing BigQuery: {e}")
        print("💡 Check your credentials and project permissions")

def find_encrypted_files_in_storage():
    """Find KMS-encrypted files in Cloud Storage"""
    print("\n🔍 Searching for KMS-encrypted files in Cloud Storage...")
    
    try:
        # Initialize Storage client
        credentials, project_id = generate_token()
        client = storage.Client(credentials=credentials, project=project_id)
        
        bucket_name = 'healthcare_audio_analyzer_fhir'
        bucket = client.bucket(bucket_name)
        
        print(f"\n📁 FILES IN BUCKET: {bucket_name}")
        print("=" * 60)
        
        found_files = False
        for blob in bucket.list_blobs():
            found_files = True
            print(f"📄 File: {blob.name}")
            print(f"📏 Size: {blob.size} bytes")
            print(f"📅 Created: {blob.time_created}")
            print(f"🔐 KMS Key: {blob.kms_key_name or 'No KMS key (default encryption)'}")
            print(f"🔒 Encrypted: {'Yes (KMS)' if blob.kms_key_name else 'Yes (default)'}")
            print("-" * 60)
        
        if not found_files:
            print("❌ No files found in Cloud Storage bucket")
            print("💡 This could mean:")
            print("   - No files have been uploaded yet")
            print("   - Bucket name is incorrect")
            print("   - Insufficient permissions to access bucket")
            
    except Exception as e:
        print(f"❌ Error accessing Cloud Storage: {e}")
        print("💡 Check your credentials and bucket permissions")

def check_kms_keys():
    """Check if KMS keys are properly configured"""
    print("\n🔍 Checking KMS key configuration...")
    
    try:
        from google.cloud import kms
        
        credentials, project_id = generate_token()
        client = kms.KeyManagementServiceClient(credentials=credentials)
        
        # List key rings
        location = "us-central1"
        parent = f"projects/{project_id}/locations/{location}"
        
        print(f"\n🔑 KMS KEYS IN PROJECT: {project_id}")
        print("=" * 60)
        
        key_rings = client.list_key_rings(request={"parent": parent})
        found_keys = False
        
        for key_ring in key_rings:
            print(f"🔐 Key Ring: {key_ring.name}")
            
            # List crypto keys in this key ring
            crypto_keys = client.list_crypto_keys(request={"parent": key_ring.name})
            for crypto_key in crypto_keys:
                found_keys = True
                print(f"  🔑 Crypto Key: {crypto_key.name}")
                print(f"  🎯 Purpose: {crypto_key.purpose.name}")
                print(f"  📅 Created: {crypto_key.create_time}")
                print("-" * 60)
        
        if not found_keys:
            print("❌ No KMS keys found")
            print("💡 KMS keys may not be properly configured")
            
    except Exception as e:
        print(f"❌ Error accessing KMS: {e}")
        print("💡 Check your KMS permissions")

def main():
    """Main function to run all checks"""
    print("🔍 ENCRYPTED DATA FINDER")
    print("=" * 60)
    print("This script will help you locate encrypted data in your Google Cloud infrastructure")
    print()
    
    # Check each component
    find_encrypted_data_in_bigquery()
    find_encrypted_files_in_storage()
    check_kms_keys()
    
    print("\n✅ SEARCH COMPLETE!")
    print("=" * 60)
    print("💡 If you don't see encrypted data:")
    print("   1. Make sure you uploaded data through the Flutter app")
    print("   2. Check that the security services are properly configured")
    print("   3. Verify your Google Cloud permissions")
    print("   4. Check the application logs for any errors")

if __name__ == "__main__":
    main() 