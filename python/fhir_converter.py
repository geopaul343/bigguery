import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

class FHIRConverter:
    """Convert audio file metadata to FHIR Media resource format"""
    
    def __init__(self):
        self.base_url = "https://data-api-887192895309.us-central1.run.app"
    
    def create_media_resource(
        self,
        file_name: str,
        file_path: str,
        file_size_bytes: int,
        content_type: str = "audio/mpeg",
        duration_seconds: Optional[float] = None,
        subject_reference: Optional[str] = None,
        operator_name: Optional[str] = None,
        device_name: Optional[str] = "Mobile Audio Recorder",
        reason_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a FHIR Media resource for an audio file
        
        Args:
            file_name: Name of the audio file
            file_path: URL or path to the audio file
            file_size_bytes: Size of the file in bytes
            content_type: MIME type of the audio file
            duration_seconds: Duration of audio in seconds
            subject_reference: Reference to patient (e.g., "Patient/123")
            operator_name: Name of person who recorded
            device_name: Recording device name
            reason_code: Why was this audio recorded
            
        Returns:
            FHIR Media resource as dictionary
        """
        
        # Generate unique resource ID
        resource_id = str(uuid.uuid4())
        
        # Current timestamp
        now = datetime.now().isoformat() + "Z"
        
        # Base Media resource structure
        media_resource = {
            "resourceType": "Media",
            "id": resource_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": now,
                "profile": ["http://hl7.org/fhir/StructureDefinition/Media"]
            },
            "identifier": [
                {
                    "use": "usual",
                    "system": f"{self.base_url}/media-id",
                    "value": file_name
                }
            ],
            "status": "completed",
            "type": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/media-type",
                        "code": "audio",
                        "display": "Audio"
                    }
                ]
            },
            "modality": {
                "coding": [
                    {
                        "system": "http://dicom.nema.org/resources/ontology/DCM",
                        "code": "AU",
                        "display": "Audio"
                    }
                ]
            },
            "createdDateTime": now,
            "issued": now,
            "content": {
                "contentType": content_type,
                "size": file_size_bytes,
                "url": file_path,
                "title": file_name
            }
        }
        
        # Add optional duration if provided
        if duration_seconds:
            media_resource["duration"] = duration_seconds
            
        # Add subject (patient) reference if provided
        if subject_reference:
            media_resource["subject"] = {
                "reference": subject_reference,
                "display": "Patient"
            }
            
        # Add operator information if provided
        if operator_name:
            media_resource["operator"] = {
                "display": operator_name
            }
            
        # Add device information
        if device_name:
            media_resource["deviceName"] = device_name
            
        # Add reason code if provided
        if reason_code:
            media_resource["reasonCode"] = [
                {
                    "text": reason_code
                }
            ]
            
        return media_resource
    
    def create_document_reference(
        self,
        media_resource: Dict[str, Any],
        file_name: str,
        file_path: str,
        subject_reference: Optional[str] = None,
        category_code: str = "audio-recording"
    ) -> Dict[str, Any]:
        """
        Create a FHIR DocumentReference resource that references the Media resource
        
        Args:
            media_resource: The FHIR Media resource
            file_name: Name of the file
            file_path: URL to the file
            subject_reference: Reference to patient
            category_code: Category of the document
            
        Returns:
            FHIR DocumentReference resource as dictionary
        """
        
        resource_id = str(uuid.uuid4())
        now = datetime.now().isoformat() + "Z"
        
        doc_ref = {
            "resourceType": "DocumentReference",
            "id": resource_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": now,
                "profile": ["http://hl7.org/fhir/StructureDefinition/DocumentReference"]
            },
            "identifier": [
                {
                    "use": "usual",
                    "system": f"{self.base_url}/document-id",
                    "value": f"doc-{file_name}"
                }
            ],
            "status": "current",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "18842-5",
                        "display": "Discharge summary"
                    }
                ]
            },
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                            "code": category_code,
                            "display": "Audio Recording"
                        }
                    ]
                }
            ],
            "date": now,
            "content": [
                {
                    "attachment": {
                        "contentType": media_resource["content"]["contentType"],
                        "url": file_path,
                        "size": media_resource["content"]["size"],
                        "title": file_name
                    },
                    "format": {
                        "system": "http://ihe.net/fhir/ihe.formatcode.fhir/CodeSystem/formatcode",
                        "code": "urn:ihe:iti:xds:2017:mimeTypeSufficient",
                        "display": "mimeType Sufficient"
                    }
                }
            ]
        }
        
        # Add subject reference if provided
        if subject_reference:
            doc_ref["subject"] = {
                "reference": subject_reference,
                "display": "Patient"
            }
            
        return doc_ref
    
    def validate_fhir_resource(self, resource: Dict[str, Any]) -> bool:
        """
        Basic validation of FHIR resource structure
        
        Args:
            resource: FHIR resource dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["resourceType", "id", "meta"]
        
        for field in required_fields:
            if field not in resource:
                return False
                
        # Validate resourceType
        if resource["resourceType"] not in ["Media", "DocumentReference"]:
            return False
            
        return True
    
    def convert_audio_metadata_to_fhir(
        self,
        file_name: str,
        file_path: str,
        file_size_bytes: int,
        content_type: str = "audio/mpeg",
        patient_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert audio file metadata to complete FHIR bundle
        
        Returns:
            FHIR Bundle containing Media and DocumentReference resources
        """
        
        # Create Media resource
        media_resource = self.create_media_resource(
            file_name=file_name,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            content_type=content_type,
            duration_seconds=duration_seconds,
            subject_reference=f"Patient/{patient_id}" if patient_id else None,
            operator_name=operator_name,
            reason_code=reason
        )
        
        # Create DocumentReference
        doc_reference = self.create_document_reference(
            media_resource=media_resource,
            file_name=file_name,
            file_path=file_path,
            subject_reference=f"Patient/{patient_id}" if patient_id else None
        )
        
        # Create FHIR Bundle
        bundle = {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "meta": {
                "lastUpdated": datetime.now().isoformat() + "Z"
            },
            "type": "collection",
            "entry": [
                {
                    "resource": media_resource,
                    "fullUrl": f"{self.base_url}/Media/{media_resource['id']}"
                },
                {
                    "resource": doc_reference,
                    "fullUrl": f"{self.base_url}/DocumentReference/{doc_reference['id']}"
                }
            ]
        }
        
        return bundle 