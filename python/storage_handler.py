from google.cloud import storage, bigquery
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class StorageHandler:
    def __init__(self, bucket_name="healthcare_audio_analyzer_fhir"):
        self.bucket_name = bucket_name
        self.storage_client = storage.Client()
        self.bigquery_client = bigquery.Client()
        
        # Use existing dataset and table
        self.dataset_id = "app-audio-analyzer"
        self.table_id = "audio_files"

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
            # Prepare the row data
            row_data = {
                "file_name": file_name,
                "file_data": file_data,  # This could be the file URL or file content reference
                "file_size": file_size,
                "file_type": file_type,
                "user_id": user_id,
                "upload_date": datetime.now().isoformat(),
                "analysis_status": analysis_status,
                "analysis_result": None  # Initially null, to be updated after analysis
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