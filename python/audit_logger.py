from google.cloud import logging as cloud_logging
from datetime import datetime
import json
import logging
from typing import Dict, Any, Optional

class AuditLogger:
    """Centralized audit logging for healthcare data access compliance"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = cloud_logging.Client(project=project_id)
        self.client.setup_logging()
        
        # Create structured logger for audit events
        self.audit_logger = self.client.logger("healthcare-audit-log")
        
    def log_data_access(self, 
                       event_type: str,
                       user_id: str,
                       resource_type: str,
                       resource_id: str,
                       action: str,
                       patient_id: Optional[str] = None,
                       success: bool = True,
                       error_message: Optional[str] = None,
                       additional_context: Optional[Dict] = None):
        """Log healthcare data access events"""
        
        audit_event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,  # "DATA_ACCESS", "ADMIN_ACTION", "AUTH_EVENT"
            "user_id": user_id,
            "resource_type": resource_type,  # "AUDIO_FILE", "PATIENT_DATA", "FHIR_RESOURCE"
            "resource_id": resource_id,
            "action": action,  # "READ", "WRITE", "DELETE", "DOWNLOAD"
            "success": success,
            "patient_id": patient_id,
            "source_ip": self._get_request_ip(),
            "user_agent": self._get_user_agent(),
            "session_id": self._get_session_id(),
            "compliance_category": "HIPAA_PHI_ACCESS" if patient_id else "SYSTEM_ACCESS"
        }
        
        if error_message:
            audit_event["error_message"] = error_message
            
        if additional_context:
            audit_event["additional_context"] = additional_context
            
        # Log to Cloud Logging with appropriate severity
        severity = "ERROR" if not success else "INFO"
        
        self.audit_logger.log_struct(
            audit_event,
            severity=severity,
            labels={
                "compliance": "hipaa",
                "data_type": "phi" if patient_id else "system",
                "audit_category": event_type.lower()
            }
        )
        
        # Also log locally for debugging
        logging.info(f"AUDIT: {event_type} - {action} on {resource_type} by {user_id}")
    
    def log_admin_action(self,
                        admin_user: str,
                        action: str,
                        target_resource: str,
                        success: bool = True,
                        changes_made: Optional[Dict] = None):
        """Log administrative actions"""
        
        admin_event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "ADMIN_ACTION",
            "admin_user": admin_user,
            "action": action,
            "target_resource": target_resource,
            "success": success,
            "source_ip": self._get_request_ip(),
            "changes_made": changes_made or {}
        }
        
        self.audit_logger.log_struct(
            admin_event,
            severity="NOTICE",
            labels={
                "compliance": "hipaa",
                "audit_category": "admin",
                "action_type": action
            }
        )
    
    def log_authentication_event(self,
                                user_id: str,
                                event_type: str,  # "LOGIN", "LOGOUT", "FAILED_LOGIN"
                                success: bool,
                                auth_method: str = "token"):
        """Log authentication events"""
        
        auth_event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "AUTH_EVENT",
            "user_id": user_id,
            "auth_event_type": event_type,
            "success": success,
            "auth_method": auth_method,
            "source_ip": self._get_request_ip(),
            "user_agent": self._get_user_agent()
        }
        
        severity = "WARNING" if not success else "INFO"
        
        self.audit_logger.log_struct(
            auth_event,
            severity=severity,
            labels={
                "compliance": "hipaa",
                "audit_category": "authentication",
                "auth_result": "success" if success else "failure"
            }
        )
    
    def log_fhir_access(self,
                       user_id: str,
                       fhir_resource_type: str,
                       fhir_resource_id: str,
                       operation: str,  # "CREATE", "READ", "UPDATE", "DELETE"
                       patient_id: Optional[str] = None):
        """Log FHIR resource access for healthcare compliance"""
        
        self.log_data_access(
            event_type="FHIR_ACCESS",
            user_id=user_id,
            resource_type=fhir_resource_type,
            resource_id=fhir_resource_id,
            action=operation,
            patient_id=patient_id,
            additional_context={
                "fhir_standard": "R4",
                "compliance_requirement": "HIPAA_HITECH"
            }
        )
    
    def _get_request_ip(self) -> Optional[str]:
        """Get client IP from Flask request context"""
        try:
            from flask import request
            return request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        except:
            return None
    
    def _get_user_agent(self) -> Optional[str]:
        """Get user agent from Flask request context"""
        try:
            from flask import request
            return request.headers.get('User-Agent')
        except:
            return None
    
    def _get_session_id(self) -> Optional[str]:
        """Get session ID from Flask request context"""
        try:
            from flask import session
            return session.get('session_id')
        except:
            return None
    
    def query_audit_logs(self, 
                        start_time: str,
                        end_time: str,
                        user_id: Optional[str] = None,
                        patient_id: Optional[str] = None) -> list:
        """Query audit logs for compliance reporting"""
        
        filter_conditions = [
            f'timestamp>="{start_time}"',
            f'timestamp<"{end_time}"',
            'jsonPayload.event_type!=null'
        ]
        
        if user_id:
            filter_conditions.append(f'jsonPayload.user_id="{user_id}"')
            
        if patient_id:
            filter_conditions.append(f'jsonPayload.patient_id="{patient_id}"')
        
        filter_str = " AND ".join(filter_conditions)
        
        entries = self.client.list_entries(
            filter_=filter_str,
            order_by=cloud_logging.DESCENDING
        )
        
        return [entry.to_api_repr() for entry in entries] 