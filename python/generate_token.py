from google.oauth2 import service_account
from google.auth.transport import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_token():
    """Generate credentials for Google Cloud authentication."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            'service-account-key.json',
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        return credentials, 'app-audio-analyzer'  # Return both credentials and project_id
    except Exception as e:
        print(f"Error generating token: {str(e)}")
        return None, None

if __name__ == "__main__":
    generate_token()