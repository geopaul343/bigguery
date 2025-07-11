from flask import request, jsonify, g
import functools
import logging
import time
from typing import Dict, List, Optional
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta

class SecurityMiddleware:
    """Security middleware for API protection and Cloud Armor integration"""
    
    def __init__(self, app=None):
        self.app = app
        self.rate_limit_storage = defaultdict(deque)
        self.blocked_ips = set()
        self.suspicious_patterns = [
            r'<script.*?>',  # XSS attempts
            r'union.*select',  # SQL injection
            r'\.\./',  # Path traversal
            r'<.*?>',  # HTML tags
            r'javascript:',  # JavaScript protocol
            r'vbscript:',  # VBScript protocol
        ]
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Register error handlers
        app.errorhandler(429)(self.rate_limit_exceeded)
        app.errorhandler(403)(self.access_forbidden)
    
    def before_request(self):
        """Execute before each request"""
        g.request_start_time = time.time()
        g.client_ip = self.get_client_ip()
        g.user_agent = request.headers.get('User-Agent', '')
        
        # Check IP blacklist
        if self.is_ip_blocked(g.client_ip):
            logging.warning(f"Blocked request from blacklisted IP: {g.client_ip}")
            return jsonify({'error': 'Access denied'}), 403
        
        # Rate limiting
        if not self.check_rate_limit(g.client_ip):
            logging.warning(f"Rate limit exceeded for IP: {g.client_ip}")
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        # Content validation
        if not self.validate_request_content():
            logging.warning(f"Malicious content detected from IP: {g.client_ip}")
            return jsonify({'error': 'Invalid request content'}), 400
        
        # Healthcare-specific validation
        if not self.validate_healthcare_request():
            logging.warning(f"Invalid healthcare request from IP: {g.client_ip}")
            return jsonify({'error': 'Invalid healthcare request'}), 400
    
    def after_request(self, response):
        """Execute after each request"""
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Healthcare-specific headers
        response.headers['X-HIPAA-Compliance'] = 'enabled'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        
        # Log response metrics
        if hasattr(g, 'request_start_time'):
            duration = time.time() - g.request_start_time
            self.log_request_metrics(response.status_code, duration)
        
        return response
    
    def get_client_ip(self) -> str:
        """Get real client IP considering Cloud Load Balancer headers"""
        # Check Cloud Load Balancer headers first
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # First IP in the chain is the original client
            return forwarded_for.split(',')[0].strip()
        
        # Check other proxy headers
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to remote address
        return request.environ.get('REMOTE_ADDR', '0.0.0.0')
    
    def check_rate_limit(self, ip_address: str, 
                        limit: int = 100, 
                        window_minutes: int = 15) -> bool:
        """Implement rate limiting per IP"""
        
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)
        
        # Clean old entries
        while (self.rate_limit_storage[ip_address] and 
               self.rate_limit_storage[ip_address][0] < window_start):
            self.rate_limit_storage[ip_address].popleft()
        
        # Check current count
        current_requests = len(self.rate_limit_storage[ip_address])
        
        if current_requests >= limit:
            # Add to blocked IPs if severely exceeding limits
            if current_requests > limit * 2:
                self.blocked_ips.add(ip_address)
                logging.error(f"IP {ip_address} added to blocklist for excessive requests")
            return False
        
        # Add current request
        self.rate_limit_storage[ip_address].append(now)
        return True
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is in blocklist"""
        return ip_address in self.blocked_ips
    
    def validate_request_content(self) -> bool:
        """Validate request content for malicious patterns"""
        
        # Check URL parameters
        for key, value in request.args.items():
            if self.contains_malicious_pattern(value):
                logging.warning(f"Malicious pattern in URL param {key}: {value}")
                return False
        
        # Check JSON body if present
        if request.is_json:
            try:
                json_data = request.get_json()
                if json_data:
                    json_str = str(json_data)
                    if self.contains_malicious_pattern(json_str):
                        logging.warning(f"Malicious pattern in JSON body")
                        return False
            except Exception:
                # Invalid JSON
                return False
        
        # Check form data
        if request.form:
            for key, value in request.form.items():
                if self.contains_malicious_pattern(value):
                    logging.warning(f"Malicious pattern in form field {key}: {value}")
                    return False
        
        return True
    
    def contains_malicious_pattern(self, content: str) -> bool:
        """Check if content contains malicious patterns"""
        content_lower = content.lower()
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        
        return False
    
    def validate_healthcare_request(self) -> bool:
        """Validate healthcare-specific request requirements"""
        
        # Check for required headers in healthcare endpoints
        if request.path.startswith('/fhir/'):
            # FHIR endpoints should have proper content type
            if request.method == 'POST':
                content_type = request.headers.get('Content-Type', '')
                if not content_type.startswith('application/json'):
                    return False
        
        # Check file upload restrictions
        if request.path.startswith('/upload'):
            # Validate file types for audio uploads
            if 'file' in request.files:
                file = request.files['file']
                if file.filename:
                    allowed_extensions = {'.mp3', '.wav', '.ogg', '.m4a'}
                    file_ext = '.' + file.filename.split('.')[-1].lower()
                    if file_ext not in allowed_extensions:
                        logging.warning(f"Invalid file type: {file.filename}")
                        return False
        
        return True
    
    def log_request_metrics(self, status_code: int, duration: float):
        """Log request metrics for monitoring"""
        
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'client_ip': g.client_ip,
            'method': request.method,
            'path': request.path,
            'status_code': status_code,
            'duration_ms': round(duration * 1000, 2),
            'user_agent': g.user_agent,
            'content_length': request.content_length or 0
        }
        
        # Log to structured logger for Cloud Logging
        logging.info(f"REQUEST_METRICS: {metrics}")
    
    def rate_limit_exceeded(self, error):
        """Handle rate limit exceeded errors"""
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'retry_after': 900  # 15 minutes
        }), 429
    
    def access_forbidden(self, error):
        """Handle access forbidden errors"""
        return jsonify({
            'error': 'Access forbidden',
            'message': 'Your request has been blocked.'
        }), 403

# Cloud Armor Integration Functions
class CloudArmorIntegration:
    """Integration with Google Cloud Armor for advanced protection"""
    
    @staticmethod
    def create_security_policy():
        """
        Cloud Armor security policy configuration
        Run this with gcloud CLI to create the policy
        """
        return {
            "gcloud_commands": [
                # Create security policy
                """
                gcloud compute security-policies create healthcare-api-protection \\
                    --description="Healthcare API protection policy"
                """,
                
                # Add rate limiting rule
                """
                gcloud compute security-policies rules create 1000 \\
                    --security-policy=healthcare-api-protection \\
                    --expression="true" \\
                    --action=rate-based-ban \\
                    --rate-limit-threshold-count=100 \\
                    --rate-limit-threshold-interval-sec=60 \\
                    --ban-duration-sec=600 \\
                    --conform-action=allow \\
                    --exceed-action=deny-429 \\
                    --enforce-on-key=IP
                """,
                
                # Block known bad IPs
                """
                gcloud compute security-policies rules create 2000 \\
                    --security-policy=healthcare-api-protection \\
                    --expression="origin.ip == '203.0.113.0/24'" \\
                    --action=deny-403
                """,
                
                # Geo-blocking (example: block certain countries)
                """
                gcloud compute security-policies rules create 3000 \\
                    --security-policy=healthcare-api-protection \\
                    --expression="origin.region_code == 'CN' || origin.region_code == 'RU'" \\
                    --action=deny-403 \\
                    --description="Block traffic from high-risk countries"
                """,
                
                # SQLi protection
                """
                gcloud compute security-policies rules create 4000 \\
                    --security-policy=healthcare-api-protection \\
                    --expression="has(request.headers['user-agent']) && request.headers['user-agent'].contains('sqlmap')" \\
                    --action=deny-403 \\
                    --description="Block SQL injection tools"
                """,
                
                # XSS protection
                """
                gcloud compute security-policies rules create 5000 \\
                    --security-policy=healthcare-api-protection \\
                    --expression="request.query.matches('.*<script.*>.*')" \\
                    --action=deny-403 \\
                    --description="Block XSS attempts"
                """
            ]
        }
    
    @staticmethod
    def attach_to_load_balancer():
        """Instructions to attach security policy to load balancer"""
        return {
            "gcloud_command": """
            gcloud compute backend-services update YOUR_BACKEND_SERVICE \\
                --security-policy=healthcare-api-protection \\
                --global
            """
        } 