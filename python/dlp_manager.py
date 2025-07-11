from google.cloud import dlp_v2
import json
import logging
from typing import Dict, List, Any, Optional

class DLPManager:
    """Cloud DLP manager for protecting sensitive healthcare data"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = dlp_v2.DlpServiceClient()
        self.parent = f"projects/{project_id}/locations/global"
        
        # Healthcare-specific info types
        self.healthcare_info_types = [
            "PERSON_NAME",
            "PHONE_NUMBER", 
            "EMAIL_ADDRESS",
            "DATE_OF_BIRTH",
            "MEDICAL_RECORD_NUMBER",
            "US_SOCIAL_SECURITY_NUMBER",
            "US_HEALTHCARE_NPI",
            "US_DEA_NUMBER",
            "CREDIT_CARD_NUMBER",
            "US_DRIVERS_LICENSE_NUMBER"
        ]
        
        # Custom healthcare patterns
        self.custom_patterns = {
            "PATIENT_ID": r"PAT-\d{6,10}",
            "MEDICAL_DEVICE_ID": r"MD-[A-Z0-9]{8,12}",
            "FHIR_RESOURCE_ID": r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
        }
    
    def create_inspection_template(self):
        """Create DLP inspection template for healthcare data"""
        
        # Configure info types
        info_types = [{"name": info_type} for info_type in self.healthcare_info_types]
        
        # Add custom patterns
        custom_info_types = []
        for name, pattern in self.custom_patterns.items():
            custom_info_types.append({
                "info_type": {"name": name},
                "regex": {"pattern": pattern},
                "likelihood": dlp_v2.Likelihood.LIKELY
            })
        
        # Create inspection config
        inspect_config = {
            "info_types": info_types,
            "custom_info_types": custom_info_types,
            "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
            "include_quote": True,
            "limits": {
                "max_findings_per_info_type": 100,
                "max_findings_per_request": 1000
            }
        }
        
        # Template configuration
        template = {
            "display_name": "Healthcare Audio Metadata Scanner",
            "description": "DLP template for scanning healthcare audio metadata",
            "inspect_config": inspect_config
        }
        
        try:
            response = self.client.create_inspect_template(
                request={
                    "parent": self.parent,
                    "inspect_template": template
                }
            )
            logging.info(f"Created DLP inspection template: {response.name}")
            return response.name
        except Exception as e:
            logging.error(f"Error creating DLP template: {e}")
            raise
    
    def scan_text_for_phi(self, text_content: str) -> Dict[str, Any]:
        """Scan text content for Protected Health Information (PHI)"""
        
        # Configure inspection
        inspect_config = {
            "info_types": [{"name": info_type} for info_type in self.healthcare_info_types],
            "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
            "include_quote": True
        }
        
        # Item to inspect
        item = {"value": text_content}
        
        # Call DLP API
        try:
            response = self.client.inspect_content(
                request={
                    "parent": self.parent,
                    "inspect_config": inspect_config,
                    "item": item
                }
            )
            
            findings = []
            for finding in response.result.findings:
                findings.append({
                    "info_type": finding.info_type.name,
                    "likelihood": finding.likelihood.name,
                    "quote": finding.quote,
                    "location": {
                        "byte_range": {
                            "start": finding.location.byte_range.start,
                            "end": finding.location.byte_range.end
                        }
                    }
                })
            
            return {
                "has_phi": len(findings) > 0,
                "findings_count": len(findings),
                "findings": findings,
                "risk_level": self._calculate_risk_level(findings)
            }
            
        except Exception as e:
            logging.error(f"Error scanning text for PHI: {e}")
            raise
    
    def redact_sensitive_data(self, text_content: str, 
                            replacement_char: str = "*") -> Dict[str, Any]:
        """Redact sensitive data from text"""
        
        # Configure deidentification
        deidentify_config = {
            "info_type_transformations": {
                "transformations": [
                    {
                        "info_types": [{"name": info_type} for info_type in self.healthcare_info_types],
                        "primitive_transformation": {
                            "character_mask_config": {
                                "masking_character": replacement_char,
                                "number_to_mask": 0  # Mask all characters
                            }
                        }
                    }
                ]
            }
        }
        
        # Configure inspection
        inspect_config = {
            "info_types": [{"name": info_type} for info_type in self.healthcare_info_types],
            "min_likelihood": dlp_v2.Likelihood.POSSIBLE
        }
        
        # Item to deidentify
        item = {"value": text_content}
        
        try:
            response = self.client.deidentify_content(
                request={
                    "parent": self.parent,
                    "deidentify_config": deidentify_config,
                    "inspect_config": inspect_config,
                    "item": item
                }
            )
            
            return {
                "original_text": text_content,
                "redacted_text": response.item.value,
                "transformations_applied": len(response.overview.transformation_summaries)
            }
            
        except Exception as e:
            logging.error(f"Error redacting sensitive data: {e}")
            raise
    
    def scan_fhir_resource(self, fhir_resource: Dict[str, Any]) -> Dict[str, Any]:
        """Scan FHIR resource for sensitive data"""
        
        # Convert FHIR resource to text for scanning
        fhir_text = json.dumps(fhir_resource, indent=2)
        
        # Scan the JSON content
        scan_result = self.scan_text_for_phi(fhir_text)
        
        # Add FHIR-specific analysis
        fhir_analysis = {
            "resource_type": fhir_resource.get("resourceType", "Unknown"),
            "resource_id": fhir_resource.get("id", "Unknown"),
            "contains_patient_data": "subject" in fhir_resource or "patient" in fhir_resource,
            "phi_detected": scan_result["has_phi"],
            "compliance_risk": self._assess_fhir_compliance_risk(fhir_resource, scan_result)
        }
        
        return {
            **scan_result,
            "fhir_analysis": fhir_analysis
        }
    
    def create_data_classification(self, content: str) -> Dict[str, Any]:
        """Classify data sensitivity level"""
        
        scan_result = self.scan_text_for_phi(content)
        
        # Determine classification based on findings
        if scan_result["has_phi"]:
            if scan_result["findings_count"] > 5:
                classification = "HIGHLY_SENSITIVE"
            elif scan_result["findings_count"] > 2:
                classification = "SENSITIVE"
            else:
                classification = "POTENTIALLY_SENSITIVE"
        else:
            classification = "PUBLIC"
        
        return {
            "classification": classification,
            "confidence": self._calculate_confidence(scan_result),
            "handling_requirements": self._get_handling_requirements(classification),
            "retention_policy": self._get_retention_policy(classification)
        }
    
    def _calculate_risk_level(self, findings: List[Dict]) -> str:
        """Calculate risk level based on findings"""
        if not findings:
            return "LOW"
        
        high_risk_types = ["US_SOCIAL_SECURITY_NUMBER", "MEDICAL_RECORD_NUMBER", "DATE_OF_BIRTH"]
        
        high_risk_count = sum(1 for f in findings if f["info_type"] in high_risk_types)
        
        if high_risk_count > 0:
            return "HIGH"
        elif len(findings) > 3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _assess_fhir_compliance_risk(self, fhir_resource: Dict, scan_result: Dict) -> str:
        """Assess HIPAA compliance risk for FHIR resource"""
        
        risk_factors = 0
        
        # Check for patient identifiers
        if fhir_resource.get("resourceType") in ["Patient", "Media", "DocumentReference"]:
            risk_factors += 1
        
        # Check for PHI in the scan
        if scan_result["has_phi"]:
            risk_factors += 2
        
        # Check for high-risk findings
        if scan_result["risk_level"] == "HIGH":
            risk_factors += 3
        
        if risk_factors >= 4:
            return "HIGH_RISK"
        elif risk_factors >= 2:
            return "MEDIUM_RISK"
        else:
            return "LOW_RISK"
    
    def _calculate_confidence(self, scan_result: Dict) -> float:
        """Calculate confidence score for classification"""
        if not scan_result["has_phi"]:
            return 0.95
        
        # Base confidence on likelihood of findings
        high_likelihood_count = sum(1 for f in scan_result["findings"] 
                                  if f["likelihood"] in ["VERY_LIKELY", "LIKELY"])
        
        total_findings = scan_result["findings_count"]
        
        if total_findings == 0:
            return 0.95
        
        confidence = (high_likelihood_count / total_findings) * 0.9 + 0.1
        return min(confidence, 0.99)
    
    def _get_handling_requirements(self, classification: str) -> List[str]:
        """Get data handling requirements based on classification"""
        requirements = {
            "PUBLIC": ["Standard backup"],
            "POTENTIALLY_SENSITIVE": ["Encrypted storage", "Access logging"],
            "SENSITIVE": ["Encrypted storage", "Access logging", "Regular audits", "Role-based access"],
            "HIGHLY_SENSITIVE": ["Encrypted storage", "Access logging", "Regular audits", 
                               "Role-based access", "Data masking", "Secure deletion"]
        }
        return requirements.get(classification, [])
    
    def _get_retention_policy(self, classification: str) -> str:
        """Get data retention policy based on classification"""
        policies = {
            "PUBLIC": "Standard retention (7 years)",
            "POTENTIALLY_SENSITIVE": "Healthcare retention (10 years)",
            "SENSITIVE": "HIPAA retention (6 years minimum)",
            "HIGHLY_SENSITIVE": "HIPAA retention (6 years minimum) + secure deletion"
        }
        return policies.get(classification, "Standard retention") 