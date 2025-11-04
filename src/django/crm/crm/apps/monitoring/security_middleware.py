"""
Security Middleware - KISS Principle Implementation
Simple, focused security functionality
"""

import uuid
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class SecurityMiddleware(MiddlewareMixin):
    """
    Simple security middleware following KISS principles.

    Provides basic security features without over-engineering.
    Focuses on essential security headers only.
    """

    def __init__(self, get_response):
        """Initialize security middleware."""
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """
        Process incoming request for security checks.

        Args:
            request: Django request object
        """
        # Simple request ID for tracking
        request.security_id = str(uuid.uuid4())[:8]

        # Simple security risk assessment
        risk_score = 0
        security_flags = []

        # Basic risk assessment
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'script' in user_agent or 'bot' in user_agent or 'sqlmap' in user_agent:
            risk_score += 1
            security_flags.append('suspicious_user_agent')

        # Check for suspicious patterns in request
        path = getattr(request, 'path', '').lower()
        if 'drop table' in path or 'script' in path:
            risk_score += 1
            security_flags.append('suspicious_request_path')

        # Store security information
        request.security_risk_score = risk_score
        request.security_flags = security_flags

    def process_response(self, request, response):
        """
        Add security headers to response.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            HttpResponse: Response with security headers
        """
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['X-Security-ID'] = getattr(request, 'security_id', 'unknown')

        return response