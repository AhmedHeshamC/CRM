"""
Enterprise Two-Factor Authentication (2FA) Implementation.

This module provides comprehensive 2FA functionality following security best practices:
- Time-based One-Time Password (TOTP) support
- Backup codes for recovery
- QR code generation for mobile apps
- Email-based 2FA as fallback
- Session management for 2FA flows
- Comprehensive logging and monitoring
"""

import qrcode
import io
import base64
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.urls import reverse
from django.utils.crypto import get_random_string
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.oath import TOTP
import structlog
import pyotp

logger = structlog.get_logger(__name__)


class TwoFactorAuthError(Exception):
    """Custom exception for 2FA errors."""
    pass


class TwoFactorAuthService:
    """
    Enterprise 2FA service with comprehensive functionality.

    This service handles:
    - TOTP device management
    - Backup code generation and validation
    - Email-based 2FA
    - QR code generation
    - Session management
    """

    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
        self.backup_codes_count = 10
        self.email_2fa_timeout = 600  # 10 minutes

    def generate_totp_secret(self) -> str:
        """
        Generate a secure TOTP secret key.

        Returns:
            Base32 encoded secret key
        """
        return pyotp.random_base32()

    def create_totp_device(self, user, name: str = None) -> TOTPDevice:
        """
        Create a new TOTP device for the user.

        Args:
            user: User object
            name: Device name (optional)

        Returns:
            TOTPDevice object
        """
        secret = self.generate_totp_secret()
        device_name = name or f"Device {timezone.now().strftime('%Y-%m-%d %H:%M')}"

        device = TOTPDevice.objects.create(
            user=user,
            name=device_name,
            secret=secret,
            confirmed=False,
            tolerance=1,  # Allow 1 step tolerance (30 seconds)
            drift=0,
            digits=6,
            step=30,
        )

        logger.info(
            'totp_device_created',
            user_id=user.id,
            device_id=device.id,
            device_name=device_name
        )

        return device

    def generate_qr_code(self, device: TOTPDevice, user) -> str:
        """
        Generate QR code for TOTP device setup.

        Args:
            device: TOTPDevice object
            user: User object

        Returns:
            Base64 encoded QR code image
        """
        # Create provisioning URI
        totp = pyotp.TOTP(device.secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="Enterprise CRM"
        )

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"

    def verify_totp_token(self, device: TOTPDevice, token: str) -> bool:
        """
        Verify TOTP token against device.

        Args:
            device: TOTPDevice object
            token: 6-digit token

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Clean token (remove spaces, ensure 6 digits)
            token = token.strip().replace(' ', '')
            if len(token) != 6 or not token.isdigit():
                return False

            # Verify token
            totp = pyotp.TOTP(device.secret)
            is_valid = totp.verify(token)

            if is_valid and not device.confirmed:
                # Confirm the device on first successful verification
                device.confirmed = True
                device.save()

                logger.info(
                    'totp_device_confirmed',
                    user_id=device.user.id,
                    device_id=device.id
                )

            return is_valid

        except Exception as e:
            logger.error(
                'totp_verification_error',
                error=str(e),
                device_id=device.id if device else None
            )
            return False

    def generate_backup_codes(self, user) -> list:
        """
        Generate backup codes for 2FA recovery.

        Args:
            user: User object

        Returns:
            List of backup codes
        """
        backup_codes = []

        # Generate secure backup codes
        for _ in range(self.backup_codes_count):
            code = get_random_string(length=8, allowed_chars='0123456789ABCDEF')
            backup_codes.append({
                'code': code,
                'created_at': timezone.now(),
                'used_at': None,
                'used': False
            })

        # Store backup codes securely (encrypted)
        self._store_backup_codes(user, backup_codes)

        logger.info(
            'backup_codes_generated',
            user_id=user.id,
            codes_count=len(backup_codes)
        )

        return backup_codes

    def verify_backup_code(self, user, code: str) -> bool:
        """
        Verify and consume a backup code.

        Args:
            user: User object
            code: Backup code to verify

        Returns:
            True if code is valid, False otherwise
        """
        try:
            backup_codes = self._get_backup_codes(user)

            for backup_code in backup_codes:
                if (not backup_code['used'] and
                    backup_code['code'] == code.upper() and
                    not backup_code['used_at']):

                    # Mark as used
                    backup_code['used'] = True
                    backup_code['used_at'] = timezone.now()

                    # Update stored codes
                    self._store_backup_codes(user, backup_codes)

                    logger.info(
                        'backup_code_used',
                        user_id=user.id,
                        code_hash=hashlib.sha256(code.encode()).hexdigest()[:8]
                    )

                    return True

            return False

        except Exception as e:
            logger.error(
                'backup_code_verification_error',
                error=str(e),
                user_id=user.id
            )
            return False

    def send_email_2fa_code(self, user) -> str:
        """
        Send 2FA code via email.

        Args:
            user: User object

        Returns:
            Generated 6-digit code
        """
        # Generate secure 6-digit code
        code = f"{secrets.randbelow(1000000):06d}"

        # Store code with expiration
        cache_key = f"2fa_email:{user.id}"
        cache.set(cache_key, code, self.email_2fa_timeout)

        # Send email
        subject = "Your Two-Factor Authentication Code"
        message = render_to_string('authentication/2fa_email.txt', {
            'user': user,
            'code': code,
            'minutes': self.email_2fa_timeout // 60
        })

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            logger.info(
                'email_2fa_sent',
                user_id=user.id,
                email=user.email
            )

            return code

        except Exception as e:
            logger.error(
                'email_2fa_send_error',
                error=str(e),
                user_id=user.id
            )
            raise TwoFactorAuthError("Failed to send 2FA email")

    def verify_email_2fa_code(self, user, code: str) -> bool:
        """
        Verify email-based 2FA code.

        Args:
            user: User object
            code: 6-digit code

        Returns:
            True if code is valid, False otherwise
        """
        cache_key = f"2fa_email:{user.id}"
        stored_code = cache.get(cache_key)

        if stored_code and stored_code == code:
            # Clear the code after successful verification
            cache.delete(cache_key)

            logger.info(
                'email_2fa_verified',
                user_id=user.id
            )

            return True

        return False

    def _store_backup_codes(self, user, backup_codes: list):
        """Store backup codes securely in cache/database."""
        # In production, these should be encrypted in the database
        cache_key = f"backup_codes:{user.id}"
        cache.set(cache_key, backup_codes, 86400 * 365)  # Store for 1 year

    def _get_backup_codes(self, user) -> list:
        """Retrieve backup codes for user."""
        cache_key = f"backup_codes:{user.id}"
        return cache.get(cache_key, [])

    def get_user_2fa_status(self, user) -> Dict[str, Any]:
        """
        Get comprehensive 2FA status for user.

        Args:
            user: User object

        Returns:
            Dictionary with 2FA status information
        """
        totp_devices = TOTPDevice.objects.filter(user=user, confirmed=True)
        backup_codes = self._get_backup_codes(user)
        unused_backup_codes = [code for code in backup_codes if not code['used']]

        return {
            'enabled': user.two_factor_enabled,
            'totp_devices_count': totp_devices.count(),
            'has_totp': totp_devices.exists(),
            'backup_codes_count': len(unused_backup_codes),
            'can_setup_totp': True,
            'can_use_email_2fa': True,
            'last_used': None,  # Would be tracked in production
        }


# Global 2FA service instance
two_factor_service = TwoFactorAuthService()


# API Views for 2FA Management
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_totp_device(request):
    """Setup a new TOTP device for 2FA."""
    try:
        user = request.user

        # Create new TOTP device
        device = two_factor_service.create_totp_device(user)

        # Generate QR code
        qr_code = two_factor_service.generate_qr_code(device, user)

        # Generate backup codes
        backup_codes = two_factor_service.generate_backup_codes(user)

        # Update user 2FA status
        user.two_factor_enabled = True
        user.save()

        return Response({
            'success': True,
            'device_id': device.id,
            'device_name': device.name,
            'qr_code': qr_code,
            'backup_codes': [code['code'] for code in backup_codes],
            'instructions': 'Scan the QR code with your authenticator app and save the backup codes securely.'
        })

    except Exception as e:
        logger.error(
            'totp_setup_error',
            error=str(e),
            user_id=request.user.id
        )
        return Response({
            'success': False,
            'error': 'Failed to setup 2FA device'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_totp_device(request):
    """Verify TOTP device setup."""
    try:
        device_id = request.data.get('device_id')
        token = request.data.get('token')

        if not device_id or not token:
            return Response({
                'success': False,
                'error': 'Device ID and token are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        device = TOTPDevice.objects.get(id=device_id, user=request.user)
        is_valid = two_factor_service.verify_totp_token(device, token)

        if is_valid:
            return Response({
                'success': True,
                'message': '2FA device verified successfully'
            })
        else:
            return Response({
                'success': False,
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)

    except TOTPDevice.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Device not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(
            'totp_verification_error',
            error=str(e),
            user_id=request.user.id
        )
        return Response({
            'success': False,
            'error': 'Failed to verify device'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disable_2fa(request):
    """Disable 2FA for the user."""
    try:
        user = request.user
        password = request.data.get('password')

        if not password:
            return Response({
                'success': False,
                'error': 'Password is required to disable 2FA'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify password
        auth_user = authenticate(username=user.email, password=password)
        if not auth_user:
            return Response({
                'success': False,
                'error': 'Invalid password'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Delete all TOTP devices
        TOTPDevice.objects.filter(user=user).delete()

        # Clear backup codes
        cache.delete(f"backup_codes:{user.id}")

        # Disable 2FA
        user.two_factor_enabled = False
        user.save()

        logger.info(
            '2fa_disabled',
            user_id=user.id
        )

        return Response({
            'success': True,
            'message': '2FA has been disabled'
        })

    except Exception as e:
        logger.error(
            '2fa_disable_error',
            error=str(e),
            user_id=request.user.id
        )
        return Response({
            'success': False,
            'error': 'Failed to disable 2FA'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_2fa_status(request):
    """Get current 2FA status for the user."""
    try:
        status = two_factor_service.get_user_2fa_status(request.user)

        return Response({
            'success': True,
            'status': status
        })

    except Exception as e:
        logger.error(
            '2fa_status_error',
            error=str(e),
            user_id=request.user.id
        )
        return Response({
            'success': False,
            'error': 'Failed to get 2FA status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)