# Audio File Upload to Google Cloud

This application allows you to upload audio files to Google Cloud Storage and store metadata in BigQuery.

## Prerequisites

1. Google Cloud account
2. Service account key file (`service-account-key.json`) with permissions for:
   - Google Cloud Storage
   - BigQuery

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure your `service-account-key.json` is in the root directory of the project.

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. To upload an audio file, send a POST request to `/upload` endpoint:
```bash
curl -X POST -F "audio=@/path/to/your/audio.mp3" -F "user_id=your_user_id" http://localhost:5000/upload
```

The response will include:
- Message confirming successful upload
- File name in Google Cloud Storage
- GCS URL for the uploaded file

## Storage Structure

- **Google Cloud Storage Bucket**: `healthcare_audio_analyzer_fhir`
  - Files are stored in the `audio_files/` directory
  - File naming format: `{user_id}_{timestamp}_{original_filename}`

- **BigQuery Dataset**: `app-audio-analyzer`
  - Table: `audio_records`
  - Schema:
    - user_id (STRING)
    - file_name (STRING)
    - gcs_url (STRING)
    - upload_timestamp (TIMESTAMP) 