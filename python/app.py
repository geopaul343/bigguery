from flask import Flask, jsonify, request, send_from_directory
import os
import json
import base64
import logging
from generate_token import generate_token
from google.cloud.sql.connector import Connector
import sqlalchemy
from datetime import datetime
from storage_handler import StorageHandler
from google.cloud import storage
from google.cloud import bigquery

# Import security services
from kms_manager import KMSManager
from audit_logger import AuditLogger
from dlp_manager import DLPManager
from security_middleware import SecurityMiddleware

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Initialize security middleware
security = SecurityMiddleware(app)

# Initialize the connector
connector = Connector()

# Initialize Google Cloud clients with credentials
credentials, project_id = generate_token()
if not credentials or not project_id:
    raise Exception("Failed to initialize Google Cloud credentials")

storage_client = storage.Client(credentials=credentials, project=project_id)
bigquery_client = bigquery.Client(credentials=credentials, project=project_id)

# Initialize StorageHandler with credentials
storage_handler = StorageHandler(credentials=credentials)

# Initialize security services
kms_manager = KMSManager(project_id)
audit_logger = AuditLogger(project_id)
dlp_manager = DLPManager(project_id)

# Configure KMS encryption for storage bucket
try:
    kms_manager.setup_storage_encryption(BUCKET_NAME)
    logger.info("KMS encryption configured for storage bucket")
except Exception as e:
    logger.warning(f"Could not configure KMS encryption: {e}")

# Constants
BUCKET_NAME = 'healthcare_audio_analyzer_fhir'
DATASET_ID = 'healthcare_audio_data'
TABLE_ID = 'audio_records'

# Function to get database connection
def get_db_connection():
    def getconn():
        instance_connection_name = os.environ.get('INSTANCE_CONNECTION_NAME')
        db_user = os.environ.get('DB_USER')
        db_pass = os.environ.get('DB_PASS')
        db_name = os.environ.get('DB_NAME')
        
        # Check if all required environment variables are set
        if not all([instance_connection_name, db_user, db_pass, db_name]):
            missing_vars = [var for var in ['INSTANCE_CONNECTION_NAME', 'DB_USER', 'DB_PASS', 'DB_NAME'] 
                          if not os.environ.get(var)]
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        logger.debug(f"Attempting to connect to database: {instance_connection_name}")
        try:
            conn = connector.connect(
                instance_connection_name,
                "pg8000",
                user=db_user,
                password=db_pass,
                db=db_name,
                enable_iam_auth=False
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise

    # Create connection pool
    try:
        pool = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=getconn,
        )
        # Test the connection
        with pool.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        return pool
    except Exception as e:
        logger.error(f"Failed to create database pool: {str(e)}")
        raise

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify the application is running correctly"""
    try:
        # List files to test GCS connection
        storage_handler.list_files()
        return jsonify({
            'status': 'healthy',
            'storage': 'connected'
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/get-token', methods=['GET'])
def get_token_endpoint():
    try:
        # Get service account key from environment variable
        service_account_key_base64 = os.environ.get('SERVICE_ACCOUNT_KEY')
        if not service_account_key_base64:
            logger.error("SERVICE_ACCOUNT_KEY environment variable not found")
            return jsonify({
                'success': False,
                'error': 'Service account key not configured'
            }), 500
        
        try:
            # Decode base64 service account key
            service_account_key = base64.b64decode(service_account_key_base64).decode('utf-8')
            logger.debug("Successfully decoded service account key")
        except Exception as e:
            logger.error(f"Failed to decode service account key: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Failed to decode service account key: {str(e)}'
            }), 500
            
        # Write the key to a temporary file
        try:
            with open('temp_key.json', 'w') as f:
                f.write(service_account_key)
            logger.debug("Successfully wrote service account key to temporary file")
        except Exception as e:
            logger.error(f"Failed to write service account key to file: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Failed to write service account key: {str(e)}'
            }), 500
            
        try:
            token = generate_token('temp_key.json')
            logger.debug("Token generation attempt completed")
        except Exception as e:
            logger.error(f"Error in generate_token: {str(e)}")
            if os.path.exists('temp_key.json'):
                os.remove('temp_key.json')
            return jsonify({
                'success': False,
                'error': f'Error generating token: {str(e)}'
            }), 500
        
        # Clean up the temporary file
        if os.path.exists('temp_key.json'):
            os.remove('temp_key.json')
            logger.debug("Cleaned up temporary file")
        
        if token:
            logger.info("Successfully generated token")
            return jsonify({
                'success': True,
                'token': token
            })
        else:
            logger.error("Token generation failed without raising an exception")
            return jsonify({
                'success': False,
                'error': 'Failed to generate token'
            }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        # Clean up the temporary file in case of error
        if os.path.exists('temp_key.json'):
            os.remove('temp_key.json')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/store-audio', methods=['POST'])
def store_audio():
    """Store audio file metadata in BigQuery"""
    try:
        data = request.get_json()
        required_fields = ['file_name', 'file_size', 'file_type']
        
        # Check for required fields
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        # Generate a signed URL for the file
        file_url = storage_handler.get_signed_url(data['file_name'])
        
        # Store the metadata in BigQuery
        storage_handler.store_audio_file_metadata(
            file_name=data['file_name'],
            file_data=file_url,  # Store the signed URL as file_data
            file_size=data['file_size'],
            file_type=data['file_type'],
            user_id=data.get('user_id'),  # Optional field
            analysis_status='pending'  # Default status
        )

        return jsonify({
            'success': True,
            'message': 'Audio metadata stored successfully',
            'file_url': file_url
        })
    except Exception as e:
        logger.error(f"Error storing audio metadata: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/update-analysis', methods=['POST'])
def update_analysis():
    """Update analysis status and result for a file"""
    try:
        data = request.get_json()
        if not data or 'file_name' not in data or 'status' not in data:
            return jsonify({
                'success': False,
                'error': 'file_name and status are required'
            }), 400

        storage_handler.update_analysis_status(
            file_name=data['file_name'],
            status=data['status'],
            result=data.get('result')
        )

        return jsonify({
            'success': True,
            'message': 'Analysis status updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating analysis status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-file-metadata', methods=['GET'])
def get_file_metadata():
    """Get metadata for a specific file"""
    try:
        file_name = request.args.get('file_name')
        if not file_name:
            return jsonify({
                'success': False,
                'error': 'file_name parameter is required'
            }), 400

        metadata = storage_handler.get_file_metadata(file_name)
        if metadata:
            return jsonify({
                'success': True,
                'metadata': metadata
            })
        else:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
    except Exception as e:
        logger.error(f"Error retrieving file metadata: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-pending-analyses', methods=['GET'])
def get_pending_analyses():
    """Get all files with pending analysis status"""
    try:
        pending_files = storage_handler.get_pending_analyses()
        return jsonify({
            'success': True,
            'pending_files': pending_files
        })
    except Exception as e:
        logger.error(f"Error retrieving pending analyses: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-upload-url', methods=['POST'])
def get_upload_url():
    """Generate a signed URL for uploading a file"""
    try:
        data = request.get_json()
        if not data or 'file_name' not in data:
            return jsonify({
                'success': False,
                'error': 'file_name is required'
            }), 400

        file_name = data['file_name']
        content_type = data.get('content_type', 'audio/wav')
        expiration = data.get('expiration', 3600)  # Default 1 hour expiration

        # Generate upload URL
        upload_url = storage_handler.generate_upload_url(
            file_name=file_name,
            content_type=content_type,
            expiration=expiration
        )

        # Return the upload URL and instructions
        return jsonify({
            'success': True,
            'upload_url': upload_url,
            'file_name': file_name,
            'instructions': {
                'method': 'PUT',
                'headers': {
                    'Content-Type': content_type
                },
                'curl_example': f'curl -X PUT -H "Content-Type: {content_type}" --upload-file ./your-file.wav "{upload_url}"'
            },
            'expiration_seconds': expiration
        })

    except Exception as e:
        logger.error(f"Error generating upload URL: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/register-upload', methods=['POST'])
def register_upload():
    """Register a successful file upload in BigQuery"""
    try:
        data = request.get_json()
        required_fields = ['file_name', 'file_size', 'file_type']
        
        # Check for required fields
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        # Generate a read URL for the file
        read_url = storage_handler.get_signed_url(data['file_name'])
        
        # Store the metadata in BigQuery
        storage_handler.store_audio_file_metadata(
            file_name=data['file_name'],
            file_data=read_url,
            file_size=data['file_size'],
            file_type=data['file_type'],
            user_id=data.get('user_id'),
            analysis_status='pending'
        )

        return jsonify({
            'success': True,
            'message': 'Upload registered successfully',
            'read_url': read_url
        })
    except Exception as e:
        logger.error(f"Error registering upload: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/generate-upload-url', methods=['POST'])
def generate_upload_url():
    """Generate a URL for uploading an audio file."""
    try:
        user_id = request.form.get('user_id')
        file_name = request.form.get('file_name')
        
        if not user_id or not file_name:
            return jsonify({'error': 'Both user_id and file_name are required'}), 400

        # Generate a unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{user_id}_{timestamp}_{file_name}"
        
        # Generate the GCS URL
        gcs_url = f"gs://{BUCKET_NAME}/audio_files/{unique_filename}"
        
        # Generate signed URL for direct upload (valid for 15 minutes)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"audio_files/{unique_filename}")
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.now() + datetime.timedelta(minutes=15),
            method="PUT",
            content_type="audio/*"
        )
        
        return jsonify({
            'upload_url': signed_url,
            'gcs_url': gcs_url,
            'file_name': unique_filename
        }), 200
        
    except Exception as e:
        print(f"Error generating URL: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_audio():
    """Upload an audio file and store metadata."""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        user_id = request.form.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'No user_id provided'}), 400

        if not audio_file.filename:
            return jsonify({'error': 'No selected file'}), 400

        # Generate a unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{user_id}_{timestamp}_{audio_file.filename}"
        
        try:
            # Upload to Google Cloud Storage
            bucket = storage_client.bucket(BUCKET_NAME)
            blob = bucket.blob(f"audio_files/{filename}")
            blob.upload_from_file(audio_file)
            
            # Get the URLs
            gcs_url = f"gs://{BUCKET_NAME}/audio_files/{filename}"
            public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/audio_files/{filename}"
            
            # Insert record into BigQuery
            table_ref = bigquery_client.dataset(DATASET_ID).table(TABLE_ID)
            table = bigquery_client.get_table(table_ref)
            
            rows_to_insert = [{
                'user_id': user_id,
                'file_name': filename,
                'gcs_url': gcs_url,
                'upload_timestamp': datetime.now().isoformat()
            }]
            
            errors = bigquery_client.insert_rows_json(table, rows_to_insert)
            
            if errors:
                print(f"BigQuery insert errors: {errors}")
                return jsonify({'error': f'BigQuery insert error: {errors}'}), 500
                
            return jsonify({
                'message': 'Upload successful',
                'file_name': filename,
                'gcs_url': gcs_url,
                'public_url': public_url,
                'user_id': user_id
            }), 200
            
        except Exception as e:
            print(f"Error during upload: {str(e)}")
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500
            
    except Exception as e:
        print(f"General error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def serve_upload_page():
    """Serve the main upload page"""
    try:
        with open('team_upload.html', 'r') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return jsonify({
            'error': 'Upload page not found',
            'message': 'Please use the API endpoints directly'
        }), 404

@app.route('/upload-page', methods=['GET'])
def upload_page():
    """Alternative route to serve the upload page"""
    return serve_upload_page()

@app.route('/register-upload-fhir', methods=['POST'])
def register_upload_fhir():
    """Register a successful file upload with FHIR resource creation"""
    try:
        data = request.get_json()
        required_fields = ['file_name', 'file_size', 'file_type']
        
        # Check for required fields
        for field in required_fields:
            if field not in data:
                audit_logger.log_data_access(
                    event_type="DATA_ACCESS",
                    user_id=data.get('operator_name', 'unknown'),
                    resource_type="FHIR_REGISTRATION",
                    resource_id=data.get('file_name', 'unknown'),
                    action="CREATE",
                    patient_id=data.get('patient_id'),
                    success=False,
                    error_message=f'Missing required field: {field}'
                )
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Scan for PHI in the request data
        request_text = json.dumps(data)
        phi_scan = dlp_manager.scan_text_for_phi(request_text)
        
        # Log PHI detection
        if phi_scan['has_phi']:
            audit_logger.log_data_access(
                event_type="PHI_DETECTION",
                user_id=data.get('operator_name', 'unknown'),
                resource_type="REQUEST_DATA",
                resource_id=data['file_name'],
                action="SCAN",
                patient_id=data.get('patient_id'),
                additional_context={
                    'phi_findings': phi_scan['findings_count'],
                    'risk_level': phi_scan['risk_level']
                }
            )
        
        # Encrypt sensitive data if present
        encrypted_data = data.copy()
        if data.get('patient_id'):
            encrypted_data['patient_id_encrypted'] = kms_manager.encrypt_sensitive_data(data['patient_id'])
            # Replace the original patient_id with encrypted version
            encrypted_data['patient_id'] = encrypted_data['patient_id_encrypted']
        if data.get('operator_name'):
            encrypted_data['operator_name_encrypted'] = kms_manager.encrypt_sensitive_data(data['operator_name'])
            # Replace the original operator_name with encrypted version
            encrypted_data['operator_name'] = encrypted_data['operator_name_encrypted']

        # Generate a read URL for the file
        read_url = storage_handler.get_signed_url(data['file_name'])
        
        # Store the metadata with FHIR resources using encrypted data
        result = storage_handler.store_audio_file_with_fhir(
            file_name=data['file_name'],
            file_data=read_url,
            file_size=data['file_size'],
            file_type=data['file_type'],
            patient_id=encrypted_data.get('patient_id'),  # Use encrypted version
            operator_name=encrypted_data.get('operator_name'),  # Use encrypted version
            duration_seconds=data.get('duration_seconds'),
            reason=data.get('reason')
        )
        
        # Log successful FHIR resource creation (use original unencrypted values for audit)
        audit_logger.log_fhir_access(
            user_id=data.get('operator_name', 'system'),
            fhir_resource_type="Bundle",
            fhir_resource_id=result['fhir_bundle']['id'],
            operation="CREATE",
            patient_id=data.get('patient_id')  # Original patient_id for audit trail
        )

        return jsonify({
            'success': True,
            'message': 'Upload registered with FHIR resources successfully',
            'read_url': read_url,
            'fhir_bundle_id': result['fhir_bundle']['id'],
            'fhir_resources_created': len(result['fhir_bundle']['entry']),
            'security_scan': {
                'phi_detected': phi_scan['has_phi'],
                'risk_level': phi_scan['risk_level']
            }
        })
        
    except Exception as e:
        # Log error with audit trail
        audit_logger.log_data_access(
            event_type="ERROR",
            user_id=data.get('operator_name', 'unknown') if 'data' in locals() else 'unknown',
            resource_type="FHIR_REGISTRATION",
            resource_id=data.get('file_name', 'unknown') if 'data' in locals() else 'unknown',
            action="CREATE",
            patient_id=data.get('patient_id') if 'data' in locals() else None,
            success=False,
            error_message=str(e)
        )
        logger.error(f"Error registering upload with FHIR: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-medical-records', methods=['GET'])
def get_medical_records():
    """Retrieve and decrypt medical records for display in Flutter app"""
    try:
        # Query BigQuery for encrypted medical records
        query = """
        SELECT 
            file_name,
            patient_id,
            resource_id,
            created_at,
            fhir_resource
        FROM `app-audio-analyzer.healthcare_audio_data.fhir_resources`
        WHERE patient_id IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 20
        """
        
        query_job = bigquery_client.query(query)
        results = query_job.result()
        
        decrypted_records = []
        
        for row in results:
            try:
                # Decrypt patient ID
                decrypted_patient_id = "Unknown Patient"
                if row.patient_id and len(row.patient_id) > 50:  # Encrypted data
                    try:
                        decrypted_patient_id = kms_manager.decrypt_sensitive_data(row.patient_id)
                    except Exception:
                        decrypted_patient_id = "Decryption Failed"
                else:
                    decrypted_patient_id = row.patient_id or "Unknown Patient"
                
                # Parse FHIR resource to extract operator name and reason
                doctor_name = "Unknown Doctor"
                reason = "Not specified"
                
                if row.fhir_resource:
                    try:
                        fhir_data = json.loads(row.fhir_resource)
                        
                        # Extract data from FHIR bundle
                        if 'entry' in fhir_data:
                            for entry in fhir_data['entry']:
                                resource = entry.get('resource', {})
                                
                                # Look for Practitioner (doctor) information
                                if resource.get('resourceType') == 'Practitioner':
                                    if 'name' in resource and len(resource['name']) > 0:
                                        name_parts = resource['name'][0]
                                        given_names = name_parts.get('given', [])
                                        family_name = name_parts.get('family', '')
                                        
                                        if given_names or family_name:
                                            full_name = f"{' '.join(given_names)} {family_name}".strip()
                                            
                                            # If the name looks encrypted (long base64), decrypt it
                                            if len(full_name) > 50:  # Likely encrypted
                                                try:
                                                    doctor_name = kms_manager.decrypt_sensitive_data(full_name)
                                                except Exception:
                                                    doctor_name = "Decryption Failed"
                                            else:
                                                doctor_name = full_name
                                
                                # Look for DiagnosticReport (reason)
                                elif resource.get('resourceType') == 'DiagnosticReport':
                                    if 'code' in resource and 'text' in resource['code']:
                                        reason = resource['code']['text']
                                    elif 'conclusion' in resource:
                                        reason = resource['conclusion']
                                
                                # Look for Media resource for additional info
                                elif resource.get('resourceType') == 'Media':
                                    if 'reasonCode' in resource and len(resource['reasonCode']) > 0:
                                        if 'text' in resource['reasonCode'][0]:
                                            reason = resource['reasonCode'][0]['text']
                    
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse FHIR resource for {row.resource_id}")
                
                record = {
                    'id': row.resource_id,
                    'file_name': row.file_name,
                    'patient_id': decrypted_patient_id,
                    'doctor': doctor_name,
                    'reason': reason,
                    'date': row.created_at.isoformat() if row.created_at else None,
                    'is_encrypted': len(row.patient_id or '') > 50  # Show if data was encrypted
                }
                
                decrypted_records.append(record)
                
            except Exception as decrypt_error:
                logger.warning(f"Failed to process record {row.resource_id}: {decrypt_error}")
                # Include record with error indication
                decrypted_records.append({
                    'id': row.resource_id or 'unknown',
                    'file_name': row.file_name or 'unknown',
                    'patient_id': "Processing Error",
                    'doctor': "Unknown",
                    'reason': "Data Error",
                    'date': row.created_at.isoformat() if row.created_at else None,
                    'error': True
                })
        
        # Log the access for audit trail
        audit_logger.log_data_access(
            event_type="DATA_ACCESS",
            user_id="flutter_app",
            resource_type="MEDICAL_RECORDS",
            resource_id="bulk_query",
            action="READ",
            additional_context={
                'records_count': len(decrypted_records),
                'query_type': 'medical_records_display'
            }
        )
        
        return jsonify({
            'success': True,
            'records': decrypted_records,
            'total_count': len(decrypted_records),
            'message': f'Retrieved {len(decrypted_records)} medical records'
        })
        
    except Exception as e:
        logger.error(f"Error retrieving medical records: {str(e)}")
        audit_logger.log_data_access(
            event_type="DATA_ACCESS",
            user_id="flutter_app",
            resource_type="MEDICAL_RECORDS",
            resource_id="bulk_query",
            action="READ",
            success=False,
            error_message=str(e)
        )
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve medical records'
        }), 500

@app.route('/fhir/Media', methods=['GET'])
def get_fhir_media_resources():
    """Retrieve FHIR Media resources"""
    try:
        patient_id = request.args.get('patient')
        file_name = request.args.get('file_name')
        
        resources = storage_handler.get_fhir_resources(
            patient_id=patient_id,
            resource_type='Media',
            file_name=file_name
        )
        
        return jsonify({
            'resourceType': 'Bundle',
            'type': 'searchset',
            'total': len(resources),
            'entry': [{'resource': res['fhir_resource']} for res in resources if res['fhir_resource']]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving FHIR Media resources: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/fhir/DocumentReference', methods=['GET'])
def get_fhir_document_references():
    """Retrieve FHIR DocumentReference resources"""
    try:
        patient_id = request.args.get('patient')
        file_name = request.args.get('file_name')
        
        resources = storage_handler.get_fhir_resources(
            patient_id=patient_id,
            resource_type='DocumentReference',
            file_name=file_name
        )
        
        return jsonify({
            'resourceType': 'Bundle',
            'type': 'searchset',
            'total': len(resources),
            'entry': [{'resource': res['fhir_resource']} for res in resources if res['fhir_resource']]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving FHIR DocumentReference resources: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/fhir/Bundle', methods=['GET'])
def get_fhir_bundles():
    """Retrieve FHIR Bundle resources"""
    try:
        patient_id = request.args.get('patient')
        file_name = request.args.get('file_name')
        
        resources = storage_handler.get_fhir_resources(
            patient_id=patient_id,
            resource_type='Bundle',
            file_name=file_name
        )
        
        return jsonify({
            'resourceType': 'Bundle',
            'type': 'searchset',
            'total': len(resources),
            'entry': [{'resource': res['fhir_resource']} for res in resources if res['fhir_resource']]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving FHIR Bundle resources: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/fhir/Media/<resource_id>', methods=['GET'])
def get_fhir_media_by_id(resource_id):
    """Retrieve a specific FHIR Media resource by ID"""
    try:
        query = f"""
        SELECT fhir_resource
        FROM `{storage_handler.dataset_id}.{storage_handler.fhir_table_id}`
        WHERE resource_type = 'Media' AND resource_id = @resource_id
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("resource_id", "STRING", resource_id)
            ]
        )
        
        query_job = storage_handler.bigquery_client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if not results:
            return jsonify({
                'error': 'Resource not found'
            }), 404
        
        fhir_resource = json.loads(results[0].fhir_resource)
        return jsonify(fhir_resource)
        
    except Exception as e:
        logger.error(f"Error retrieving FHIR Media resource by ID: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
else:
    # This is the variable that Gunicorn looks for
    server = app 