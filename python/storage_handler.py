from google.cloud import storage, bigquery
import logging
import json
import os
import base64
from datetime import datetime
from google.oauth2 import service_account
from fhir_converter import FHIRConverter

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class StorageHandler:
    def __init__(self, bucket_name="healthcare_audio_analyzer_fhir", credentials=None):
        self.bucket_name = bucket_name
        
        # Initialize credentials
        if credentials:
            self.credentials = credentials
        else:
            # Try to get credentials from environment variable
            service_account_key_base64 = os.environ.get('SERVICE_ACCOUNT_KEY')
            if service_account_key_base64:
                try:
                    # Decode base64 service account key
                    service_account_key = base64.b64decode(service_account_key_base64).decode('utf-8')
                    service_account_info = json.loads(service_account_key)
                    self.credentials = service_account.Credentials.from_service_account_info(service_account_info)
                    logger.info("Successfully loaded credentials from environment variable")
                except Exception as e:
                    logger.error(f"Error loading credentials from environment: {str(e)}")
                    self.credentials = None
            else:
                logger.warning("No SERVICE_ACCOUNT_KEY environment variable found, using default credentials")
                self.credentials = None
        
        # Initialize clients with credentials
        if self.credentials:
            self.storage_client = storage.Client(credentials=self.credentials)
            self.bigquery_client = bigquery.Client(credentials=self.credentials)
        else:
            self.storage_client = storage.Client()
            self.bigquery_client = bigquery.Client()
        
        # Use existing dataset and table
        self.dataset_id = "healthcare_audio_data"
        self.table_id = "audio_files"
        self.fhir_table_id = "fhir_resources"
        
        # Initialize FHIR converter
        self.fhir_converter = FHIRConverter()

    def generate_upload_url(self, file_name, content_type="audio/wav", expiration=3600):
        """Generate a signed URL for uploading a file to GCS"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(file_name)
            
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="PUT",
                content_type=content_type
            )
            
            logger.info(f"Generated upload URL for file: {file_name}")
            return url
        except Exception as e:
            logger.error(f"Error generating upload URL: {str(e)}")
            raise

    def store_audio_file_metadata(self, file_name, file_data, file_size, file_type, user_id=None, analysis_status="pending"):
        """Store audio file metadata in BigQuery using the existing schema"""
        try:
            # Prepare the row data to match the existing table schema
            row_data = {
                "file_name": file_name,
                "file_path": file_data,  # Store as file_path (URL or GCS path)
                "upload_timestamp": datetime.now().isoformat(),
                "file_size_bytes": file_size  # Store as file_size_bytes
            }

            # Insert the row into BigQuery
            table_ref = f"{self.dataset_id}.{self.table_id}"
            errors = self.bigquery_client.insert_rows_json(
                table_ref,
                [row_data]
            )

            if errors:
                logger.error(f"Errors inserting into BigQuery: {errors}")
                raise Exception(f"Failed to insert data into BigQuery: {errors}")

            logger.info(f"Successfully stored metadata for file: {file_name}")
            return True

        except Exception as e:
            logger.error(f"Error storing file metadata: {str(e)}")
            raise

    def store_fhir_resource(self, fhir_resource, patient_id=None, file_name=None):
        """Store FHIR resource in BigQuery"""
        try:
            # Prepare the row data for FHIR resources table
            row_data = {
                "resource_type": fhir_resource.get("resourceType"),
                "resource_id": fhir_resource.get("id"),
                "fhir_resource": json.dumps(fhir_resource),
                "created_at": datetime.now().isoformat(),
                "patient_id": patient_id,
                "file_name": file_name
            }

            # Insert the row into BigQuery FHIR table
            table_ref = f"{self.dataset_id}.{self.fhir_table_id}"
            errors = self.bigquery_client.insert_rows_json(
                table_ref,
                [row_data]
            )

            if errors:
                logger.error(f"Errors inserting FHIR resource into BigQuery: {errors}")
                raise Exception(f"Failed to insert FHIR resource into BigQuery: {errors}")

            logger.info(f"Successfully stored FHIR resource: {fhir_resource.get('resourceType')}/{fhir_resource.get('id')}")
            return True

        except Exception as e:
            logger.error(f"Error storing FHIR resource: {str(e)}")
            raise

    def store_audio_file_with_fhir(
        self, 
        file_name, 
        file_data, 
        file_size, 
        file_type, 
        patient_id=None, 
        operator_name=None,
        duration_seconds=None,
        reason=None
    ):
        """Store audio file metadata and create FHIR resources"""
        try:
            # Store traditional metadata
            self.store_audio_file_metadata(file_name, file_data, file_size, file_type)
            
            # Create FHIR bundle
            fhir_bundle = self.fhir_converter.convert_audio_metadata_to_fhir(
                file_name=file_name,
                file_path=file_data,
                file_size_bytes=file_size,
                content_type=file_type,
                patient_id=patient_id,
                operator_name=operator_name,
                duration_seconds=duration_seconds,
                reason=reason
            )
            
            # Store FHIR Bundle
            self.store_fhir_resource(fhir_bundle, patient_id, file_name)
            
            # Store individual resources from the bundle
            for entry in fhir_bundle.get("entry", []):
                resource = entry.get("resource")
                if resource:
                    self.store_fhir_resource(resource, patient_id, file_name)
            
            logger.info(f"Successfully stored audio file with FHIR resources: {file_name}")
            return {
                "success": True,
                "fhir_bundle": fhir_bundle,
                "message": "Audio file and FHIR resources stored successfully"
            }
            
        except Exception as e:
            logger.error(f"Error storing audio file with FHIR: {str(e)}")
            raise

    def get_fhir_resources(self, patient_id=None, resource_type=None, file_name=None):
        """Retrieve FHIR resources from BigQuery"""
        try:
            # Build query based on filters
            where_conditions = []
            query_parameters = []
            
            if patient_id:
                where_conditions.append("patient_id = @patient_id")
                query_parameters.append(bigquery.ScalarQueryParameter("patient_id", "STRING", patient_id))
            
            if resource_type:
                where_conditions.append("resource_type = @resource_type")
                query_parameters.append(bigquery.ScalarQueryParameter("resource_type", "STRING", resource_type))
            
            if file_name:
                where_conditions.append("file_name = @file_name")
                query_parameters.append(bigquery.ScalarQueryParameter("file_name", "STRING", file_name))
            
            where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
            
            query = f"""
            SELECT resource_type, resource_id, fhir_resource, created_at, patient_id, file_name
            FROM `{self.dataset_id}.{self.fhir_table_id}`
            {where_clause}
            ORDER BY created_at DESC
            """
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = query_job.result()
            
            fhir_resources = []
            for row in results:
                fhir_resources.append({
                    "resource_type": row.resource_type,
                    "resource_id": row.resource_id,
                    "fhir_resource": json.loads(row.fhir_resource) if row.fhir_resource else None,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "patient_id": row.patient_id,
                    "file_name": row.file_name
                })
            
            return fhir_resources
            
        except Exception as e:
            logger.error(f"Error retrieving FHIR resources: {str(e)}")
            raise

    def update_analysis_status(self, file_name, status, result=None):
        """Update the analysis status and result for a file"""
        try:
            query = f"""
            UPDATE `{self.dataset_id}.{self.table_id}`
            SET analysis_status = @status,
                analysis_result = @result
            WHERE file_name = @file_name
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("status", "STRING", status),
                    bigquery.ScalarQueryParameter("result", "STRING", result),
                    bigquery.ScalarQueryParameter("file_name", "STRING", file_name),
                ]
            )
            
            query_job = self.bigquery_client.query(query, job_config=job_config)
            query_job.result()  # Wait for the query to complete
            
            logger.info(f"Successfully updated analysis status for file: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating analysis status: {str(e)}")
            raise

    def get_file_metadata(self, file_name):
        """Retrieve metadata for a specific file"""
        try:
            query = f"""
            SELECT *
            FROM `{self.dataset_id}.{self.table_id}`
            WHERE file_name = @file_name
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("file_name", "STRING", file_name),
                ]
            )
            
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                return {
                    "file_name": row.file_name,
                    "file_data": row.file_data,
                    "file_size": row.file_size,
                    "file_type": row.file_type,
                    "user_id": row.user_id,
                    "upload_date": row.upload_date.isoformat() if row.upload_date else None,
                    "analysis_status": row.analysis_status,
                    "analysis_result": row.analysis_result
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving file metadata: {str(e)}")
            raise

    def get_signed_url(self, blob_name, expiration=3600):
        """Generate a signed URL for a file in the bucket"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
            
            return url
        except Exception as e:
            logger.error(f"Error generating signed URL: {str(e)}")
            raise

    def list_files(self, prefix=None):
        """List files in the bucket with optional prefix"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise

    def get_pending_analyses(self):
        """Get all files with pending analysis status"""
        try:
            query = f"""
            SELECT *
            FROM `{self.dataset_id}.{self.table_id}`
            WHERE analysis_status = 'pending'
            ORDER BY upload_date ASC
            """
            
            query_job = self.bigquery_client.query(query)
            results = query_job.result()
            
            pending_files = []
            for row in results:
                pending_files.append({
                    "file_name": row.file_name,
                    "file_data": row.file_data,
                    "file_size": row.file_size,
                    "file_type": row.file_type,
                    "user_id": row.user_id,
                    "upload_date": row.upload_date.isoformat() if row.upload_date else None
                })
            
            return pending_files
            
        except Exception as e:
            logger.error(f"Error retrieving pending analyses: {str(e)}")
            raise 