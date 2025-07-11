from google.cloud import kms
from google.cloud import storage
import base64
import logging

class KMSManager:
    """Cloud KMS manager for encrypting sensitive healthcare data"""
    
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self.client = kms.KeyManagementServiceClient()
        self.key_ring_id = "healthcare-audio-keyring"
        self.crypto_key_id = "patient-data-key"
        
        # Create key ring and key if they don't exist
        self._ensure_key_setup()
    
    def _ensure_key_setup(self):
        """Ensure KMS key ring and crypto key exist"""
        try:
            # Create key ring path
            location_name = f"projects/{self.project_id}/locations/{self.location}"
            key_ring_name = f"{location_name}/keyRings/{self.key_ring_id}"
            crypto_key_name = f"{key_ring_name}/cryptoKeys/{self.crypto_key_id}"
            
            # Try to create key ring (will fail if exists, which is fine)
            try:
                request = {
                    "parent": location_name,
                    "key_ring_id": self.key_ring_id,
                    "key_ring": {}
                }
                self.client.create_key_ring(request=request)
                logging.info(f"Created key ring: {self.key_ring_id}")
            except Exception:
                logging.info(f"Key ring {self.key_ring_id} already exists")
            
            # Try to create crypto key (will fail if exists, which is fine)
            try:
                crypto_key = {
                    "purpose": kms.CryptoKey.CryptoKeyPurpose.ENCRYPT_DECRYPT,
                    "version_template": {
                        "algorithm": kms.CryptoKeyVersion.CryptoKeyVersionAlgorithm.GOOGLE_SYMMETRIC_ENCRYPTION
                    }
                }
                request = {
                    "parent": key_ring_name,
                    "crypto_key_id": self.crypto_key_id,
                    "crypto_key": crypto_key
                }
                self.client.create_crypto_key(request=request)
                logging.info(f"Created crypto key: {self.crypto_key_id}")
            except Exception:
                logging.info(f"Crypto key {self.crypto_key_id} already exists")
                
        except Exception as e:
            logging.error(f"Error setting up KMS keys: {e}")
            raise
    
    def encrypt_sensitive_data(self, plaintext: str) -> str:
        """Encrypt sensitive data like patient IDs, operator names"""
        try:
            key_name = f"projects/{self.project_id}/locations/{self.location}/keyRings/{self.key_ring_id}/cryptoKeys/{self.crypto_key_id}"
            
            # Convert string to bytes
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Encrypt
            encrypt_response = self.client.encrypt(
                request={"name": key_name, "plaintext": plaintext_bytes}
            )
            
            # Return base64 encoded ciphertext
            return base64.b64encode(encrypt_response.ciphertext).decode('utf-8')
            
        except Exception as e:
            logging.error(f"Error encrypting data: {e}")
            raise
    
    def decrypt_sensitive_data(self, ciphertext_b64: str) -> str:
        """Decrypt sensitive data"""
        try:
            key_name = f"projects/{self.project_id}/locations/{self.location}/keyRings/{self.key_ring_id}/cryptoKeys/{self.crypto_key_id}"
            
            # Decode base64 ciphertext
            ciphertext = base64.b64decode(ciphertext_b64.encode('utf-8'))
            
            # Decrypt
            decrypt_response = self.client.decrypt(
                request={"name": key_name, "ciphertext": ciphertext}
            )
            
            return decrypt_response.plaintext.decode('utf-8')
            
        except Exception as e:
            logging.error(f"Error decrypting data: {e}")
            raise
    
    def setup_storage_encryption(self, bucket_name: str):
        """Configure Cloud Storage bucket to use KMS encryption"""
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            
            kms_key_name = f"projects/{self.project_id}/locations/{self.location}/keyRings/{self.key_ring_id}/cryptoKeys/{self.crypto_key_id}"
            
            bucket.default_kms_key_name = kms_key_name
            bucket.patch()
            
            logging.info(f"Configured bucket {bucket_name} to use KMS encryption")
            
        except Exception as e:
            logging.error(f"Error configuring storage encryption: {e}")
            raise 