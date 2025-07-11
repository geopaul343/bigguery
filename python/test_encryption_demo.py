#!/usr/bin/env python3
"""
Demo script to test encryption with realistic PHI data that will trigger DLP detection
"""
import requests
import json
import time

# Your Cloud Run endpoint
ENDPOINT = "https://data-api-887192895309.us-central1.run.app"

def test_encryption_with_phi():
    """Test encryption with realistic PHI data that should trigger DLP detection"""
    
    print("🧪 TESTING ENCRYPTION WITH REALISTIC PHI DATA")
    print("=" * 60)
    
    # Test cases with realistic PHI data
    test_cases = [
        {
            "name": "Real Patient Name",
            "data": {
                "file_name": "patient_audio_john_smith.wav",
                "file_size": 1048576,
                "file_type": "audio/wav",
                "patient_id": "John Smith",  # Real name - should trigger PHI detection
                "operator_name": "Dr. Sarah Johnson",  # Real name - should trigger PHI detection
                "duration_seconds": 30,
                "reason": "Heart murmur examination"
            }
        },
        {
            "name": "Medical Record Number",
            "data": {
                "file_name": "patient_audio_mrn_123456789.wav", 
                "file_size": 2097152,
                "file_type": "audio/wav",
                "patient_id": "MRN-123456789",  # Medical record format - should trigger PHI detection
                "operator_name": "Dr. Michael Chen",
                "duration_seconds": 45,
                "reason": "Respiratory assessment"
            }
        },
        {
            "name": "Social Security Number",
            "data": {
                "file_name": "patient_audio_ssn_test.wav",
                "file_size": 1572864,
                "file_type": "audio/wav", 
                "patient_id": "SSN-123-45-6789",  # SSN format - should definitely trigger PHI detection
                "operator_name": "Dr. Emily Rodriguez",
                "duration_seconds": 60,
                "reason": "Cardiac examination"
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔬 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Send request to the secure endpoint
            response = requests.post(
                f"{ENDPOINT}/register-upload-fhir",
                json=test_case['data'],
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success: {result.get('message', 'Data uploaded')}")
                
                # Show security scan results
                security_scan = result.get('security_scan', {})
                print(f"🔍 PHI Detected: {security_scan.get('phi_detected', 'Unknown')}")
                print(f"⚠️  Risk Level: {security_scan.get('risk_level', 'Unknown')}")
                
                # Show FHIR resources created
                fhir_count = result.get('fhir_resources_created', 0)
                print(f"📝 FHIR Resources Created: {fhir_count}")
                
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # Wait between requests to avoid rate limiting
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print("🔍 Now check BigQuery again - you should see encrypted data!")
    print("Look for long base64 strings in the patient_id field")

def show_bigquery_query():
    """Show the BigQuery query to find encrypted data"""
    print("\n📊 USE THIS BIGQUERY QUERY TO FIND ENCRYPTED DATA:")
    print("=" * 60)
    
    query = """
    SELECT 
        file_name,
        patient_id,
        resource_id,
        created_at,
        CASE 
            WHEN LENGTH(patient_id) > 50 THEN 'ENCRYPTED' 
            ELSE 'NOT ENCRYPTED' 
        END as encryption_status,
        SUBSTR(fhir_resource, 1, 200) as fhir_sample
    FROM `app-audio-analyzer.healthcare_audio_data.fhir_resources`
    WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
    ORDER BY created_at DESC
    LIMIT 10
    """
    
    print(query)
    print("\n💡 Look for rows where encryption_status = 'ENCRYPTED'")
    print("💡 Those will have long base64 strings in patient_id field")

if __name__ == "__main__":
    test_encryption_with_phi()
    show_bigquery_query() 