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

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Initialize the connector
connector = Connector()

# Initialize StorageHandler
storage_handler = StorageHandler()

# Initialize Google Cloud clients with credentials
credentials, project_id = generate_token()
if not credentials or not project_id:
    raise Exception("Failed to initialize Google Cloud credentials")

storage_client = storage.Client(credentials=credentials, project=project_id)
bigquery_client = bigquery.Client(credentials=credentials, project=project_id)

# Constants
BUCKET_NAME = 'healthcare_audio_analyzer_fhir'
DATASET_ID = 'app-audio-analyzer'
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
else:
    # This is the variable that Gunicorn looks for
    server = app 