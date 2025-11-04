"""
Enterprise API Key Management System.

This module provides comprehensive API key management following security best practices:
- Secure key generation and storage
- Role-based key permissions
- Key rotation and expiration
- Usage tracking and monitoring
- Secure key distribution
- Compliance-ready audit logging
"""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from django.conf import settings
from django.db import models
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import structlog
import uuid

logger = structlog.get_logger(__name__)


class APIKeyManager:
    """
    Enterprise API key management service.

    Features:
    - Secure key generation
    - Key expiration and rotation
    - Usage tracking
    - Permission management
    - Audit logging
    """

    def __init__(self):
        self.key_length = 64  # Length of generated keys
        self.cache_timeout = 3600  # 1 hour cache for key validation
        self.usage_tracking_window = 86400  # 24 hours for usage stats

    def generate_api_key(self, prefix: str = "crm") -> str:
        """
        Generate a secure API key.

        Args:
            prefix: Key prefix for identification

        Returns:
            Generated API key
        """
        # Generate secure random bytes
        random_bytes = secrets.token_bytes(self.key_length)

        # Create prefix and timestamp
        timestamp = int(timezone.now().timestamp())

        # Combine all components
        key_data = f"{prefix}_{timestamp}_{random_bytes.hex()}"

        # Generate final key
        api_key = hashlib.sha256(key_data.encode()).hexdigest()

        # Add prefix back for readability
        final_key = f"{prefix}_{api_key[:32]}{api_key[32:]}"

        return final_key

    def create_api_key(
        self,
        user: User,
        name: str,
        permissions: List[str] = None,
        expires_at: Optional[datetime] = None,
        description: str = None,
        rate_limit_tier: str = "standard"
    ) -> 'APIKey':
        """
        Create a new API key.

        Args:
            user: User object
            name: Key name/identifier
            permissions: List of permissions
            expires_at: Expiration date
            description: Key description
            rate_limit_tier: Rate limiting tier

        Returns:
            Created APIKey object
        """
        from .models import APIKey

        # Generate secure key
        key_value = self.generate_api_key()
        key_hash = self._hash_api_key(key_value)

        # Set default expiration if not provided
        if not expires_at:
            expires_at = timezone.now() + timedelta(days=365)

        # Create API key object
        api_key = APIKey.objects.create(
            user=user,
            name=name,
            key_hash=key_hash,
            permissions=permissions or [],
            expires_at=expires_at,
            description=description,
            rate_limit_tier=rate_limit_tier,
            is_active=True,
            last_used_at=None,
            usage_count=0
        )

        # Log key creation
        from .audit_logging import audit_logger, AuditEventType
        audit_logger.log_event(
            event_type=AuditEventType.API_KEY_CREATED,
            user_id=user.id,
            user_email=user.email,
            resource_type='api_key',
            resource_id=str(api_key.id),
            details={
                'key_name': name,
                'permissions': permissions,
                'expires_at': expires_at.isoformat(),
                'rate_limit_tier': rate_limit_tier
            }
        )

        logger.info(
            'api_key_created',
            user_id=user.id,
            key_id=api_key.id,
            key_name=name
        )

        return api_key

    def validate_api_key(self, api_key: str) -> Optional['APIKey']:
        """
        Validate an API key.

        Args:
            api_key: API key to validate

        Returns:
            APIKey object if valid, None otherwise
        """
        try:
            # Check cache first
            cache_key = f"api_key:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
            cached_key = cache.get(cache_key)
            if cached_key:
                return cached_key

            # Hash the key for comparison
            key_hash = self._hash_api_key(api_key)

            # Find active key
            from .models import APIKey
            api_key_obj = APIKey.objects.filter(
                key_hash=key_hash,
                is_active=True
            ).first()

            if not api_key_obj:
                return None

            # Check expiration
            if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now():
                api_key_obj.is_active = False
                api_key_obj.save()
                return None

            # Update usage statistics
            api_key_obj.last_used_at = timezone.now()
            api_key_obj.usage_count += 1
            api_key_obj.save()

            # Cache the result
            cache.set(cache_key, api_key_obj, self.cache_timeout)

            # Log usage
            logger.info(
                'api_key_used',
                key_id=api_key_obj.id,
                user_id=api_key_obj.user.id,
                usage_count=api_key_obj.usage_count
            )

            return api_key_obj

        except Exception as e:
            logger.error(
                'api_key_validation_error',
                error=str(e),
                key_prefix=api_key[:10] if api_key else None
            )
            return None

    def revoke_api_key(self, api_key_id: uuid.UUID, user: User) -> bool:
        """
        Revoke an API key.

        Args:
            api_key_id: API key ID
            user: User performing the revocation

        Returns:
            True if successful, False otherwise
        """
        try:
            from .models import APIKey
            api_key = APIKey.objects.get(id=api_key_id, user=user)

            # Deactivate the key
            api_key.is_active = False
            api_key.revoked_at = timezone.now()
            api_key.save()

            # Clear from cache
            cache.delete(f"api_key:{api_key.key_hash[:16]}")

            # Log revocation
            from .audit_logging import audit_logger, AuditEventType
            audit_logger.log_event(
                event_type=AuditEventType.API_KEY_DELETED,
                user_id=user.id,
                user_email=user.email,
                resource_type='api_key',
                resource_id=str(api_key.id),
                details={
                    'key_name': api_key.name,
                    'revoked_at': api_key.revoked_at.isoformat()
                }
            )

            logger.info(
                'api_key_revoked',
                key_id=api_key.id,
                user_id=user.id,
                key_name=api_key.name
            )

            return True

        except APIKey.DoesNotExist:
            return False
        except Exception as e:
            logger.error(
                'api_key_revocation_error',
                error=str(e),
                key_id=str(api_key_id),
                user_id=user.id
            )
            return False

    def rotate_api_key(self, api_key_id: uuid.UUID, user: User) -> Optional[Tuple[str, 'APIKey']]:
        """
        Rotate an API key.

        Args:
            api_key_id: API key ID
            user: User performing rotation

        Returns:
            Tuple of (new_key_value, new_api_key_object) or None
        """
        try:
            from .models import APIKey
            old_key = APIKey.objects.get(id=api_key_id, user=user)

            # Generate new key
            new_key_value = self.generate_api_key()
            new_key_hash = self._hash_api_key(new_key_value)

            # Create new key with same properties
            new_key = APIKey.objects.create(
                user=user,
                name=old_key.name,
                key_hash=new_key_hash,
                permissions=old_key.permissions,
                expires_at=old_key.expires_at,
                description=f"Rotated from {old_key.name}",
                rate_limit_tier=old_key.rate_limit_tier,
                is_active=True,
                last_used_at=None,
                usage_count=0,
                rotated_from=old_key
            )

            # Deactivate old key
            old_key.is_active = False
            old_key.rotated_at = timezone.now()
            old_key.save()

            # Clear old key from cache
            cache.delete(f"api_key:{old_key.key_hash[:16]}")

            # Log rotation
            from .audit_logging import audit_logger, AuditEventType
            audit_logger.log_event(
                event_type=AuditEventType.API_KEY_CREATED,  # Using created type for rotation
                user_id=user.id,
                user_email=user.email,
                resource_type='api_key',
                resource_id=str(new_key.id),
                details={
                    'key_name': new_key.name,
                    'rotated_from': str(old_key.id),
                    'rotation': True
                }
            )

            logger.info(
                'api_key_rotated',
                old_key_id=old_key.id,
                new_key_id=new_key.id,
                user_id=user.id
            )

            return new_key_value, new_key

        except APIKey.DoesNotExist:
            return None
        except Exception as e:
            logger.error(
                'api_key_rotation_error',
                error=str(e),
                key_id=str(api_key_id),
                user_id=user.id
            )
            return None

    def get_api_key_stats(self, user: User) -> Dict[str, Any]:
        """
        Get API key usage statistics.

        Args:
            user: User object

        Returns:
            Statistics dictionary
        """
        try:
            from .models import APIKey
            from django.db.models import Sum, Count, Q

            keys = APIKey.objects.filter(user=user)

            # Basic counts
            total_keys = keys.count()
            active_keys = keys.filter(is_active=True).count()
            expired_keys = keys.filter(expires_at__lt=timezone.now()).count()

            # Usage statistics
            total_usage = keys.aggregate(total=Sum('usage_count'))['total'] or 0
            recently_used = keys.filter(
                last_used_at__gte=timezone.now() - timedelta(days=7)
            ).count()

            # Key types
            keys_by_tier = keys.values('rate_limit_tier').annotate(count=Count('id'))

            return {
                'total_keys': total_keys,
                'active_keys': active_keys,
                'expired_keys': expired_keys,
                'total_usage': total_usage,
                'recently_used': recently_used,
                'keys_by_tier': list(keys_by_tier),
                'usage_this_month': self._get_monthly_usage(user)
            }

        except Exception as e:
            logger.error(
                'api_key_stats_error',
                error=str(e),
                user_id=user.id
            )
            return {}

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _get_monthly_usage(self, user: User) -> int:
        """Get monthly usage statistics for user's API keys."""
        # This would typically query a usage log table
        # For now, return aggregated usage from keys
        from .models import APIKey

        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return APIKey.objects.filter(
            user=user,
            last_used_at__gte=month_start
        ).aggregate(total=models.Sum('usage_count'))['total'] or 0


# API Key Authentication
class APIKeyAuthentication(BaseAuthentication):
    """
    Custom authentication for API keys.

    This authenticator validates API keys from the Authorization header
    or X-API-Key header and returns the associated user.
    """

    def authenticate(self, request):
        """
        Authenticate the request using API key.

        Args:
            request: Django REST framework request

        Returns:
            Tuple of (user, api_key) if successful, None otherwise
        """
        api_key = self._extract_api_key(request)
        if not api_key:
            return None

        # Validate the API key
        key_manager = APIKeyManager()
        api_key_obj = key_manager.validate_api_key(api_key)

        if not api_key_obj:
            raise AuthenticationFailed('Invalid or expired API key')

        # Return user and API key object
        return api_key_obj.user, api_key_obj

    def _extract_api_key(self, request) -> Optional[str]:
        """Extract API key from request headers."""
        # Check Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            # Check if it's an API key (longer than typical JWT)
            if len(token) > 100 and token.startswith('crm_'):
                return token

        # Check X-API-Key header
        return request.META.get('HTTP_X_API_KEY')


# Global API key manager instance
api_key_manager = APIKeyManager()


# API Views for API Key Management
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_api_keys(request):
    """List all API keys for the authenticated user."""
    try:
        from .models import APIKey
        keys = APIKey.objects.filter(user=request.user).order_by('-created_at')

        key_data = []
        for key in keys:
            key_data.append({
                'id': str(key.id),
                'name': key.name,
                'description': key.description,
                'permissions': key.permissions,
                'rate_limit_tier': key.rate_limit_tier,
                'is_active': key.is_active,
                'created_at': key.created_at.isoformat(),
                'expires_at': key.expires_at.isoformat() if key.expires_at else None,
                'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None,
                'usage_count': key.usage_count,
                'revoked_at': key.revoked_at.isoformat() if key.revoked_at else None,
                'rotated_at': key.rotated_at.isoformat() if key.rotated_at else None,
            })

        return Response({
            'success': True,
            'keys': key_data,
            'stats': api_key_manager.get_api_key_stats(request.user)
        })

    except Exception as e:
        logger.error(
            'list_api_keys_error',
            error=str(e),
            user_id=request.user.id
        )
        return Response({
            'success': False,
            'error': 'Failed to list API keys'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_api_key(request):
    """Create a new API key."""
    try:
        name = request.data.get('name')
        description = request.data.get('description', '')
        permissions = request.data.get('permissions', [])
        expires_days = request.data.get('expires_days', 365)
        rate_limit_tier = request.data.get('rate_limit_tier', 'standard')

        if not name:
            return Response({
                'success': False,
                'error': 'Name is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calculate expiration date
        expires_at = timezone.now() + timedelta(days=expires_days)

        # Create the API key
        api_key_obj = api_key_manager.create_api_key(
            user=request.user,
            name=name,
            permissions=permissions,
            expires_at=expires_at,
            description=description,
            rate_limit_tier=rate_limit_tier
        )

        # Generate the actual key value (only shown once)
        key_value = api_key_manager.generate_api_key()
        # Update the key with the actual hash
        api_key_obj.key_hash = api_key_manager._hash_api_key(key_value)
        api_key_obj.save()

        return Response({
            'success': True,
            'api_key': key_value,  # Only shown once
            'key_id': str(api_key_obj.id),
            'message': 'Save this API key securely. It will not be shown again.',
            'expires_at': api_key_obj.expires_at.isoformat()
        })

    except Exception as e:
        logger.error(
            'create_api_key_error',
            error=str(e),
            user_id=request.user.id
        )
        return Response({
            'success': False,
            'error': 'Failed to create API key'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_api_key(request, key_id):
    """Revoke an API key."""
    try:
        key_uuid = uuid.UUID(key_id)
        success = api_key_manager.revoke_api_key(key_uuid, request.user)

        if success:
            return Response({
                'success': True,
                'message': 'API key revoked successfully'
            })
        else:
            return Response({
                'success': False,
                'error': 'API key not found'
            }, status=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return Response({
            'success': False,
            'error': 'Invalid key ID'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(
            'revoke_api_key_error',
            error=str(e),
            user_id=request.user.id
        )
        return Response({
            'success': False,
            'error': 'Failed to revoke API key'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rotate_api_key(request, key_id):
    """Rotate an API key."""
    try:
        key_uuid = uuid.UUID(key_id)
        result = api_key_manager.rotate_api_key(key_uuid, request.user)

        if result:
            new_key_value, new_key_obj = result
            return Response({
                'success': True,
                'new_api_key': new_key_value,
                'key_id': str(new_key_obj.id),
                'message': 'Save this new API key securely. The old key has been revoked.'
            })
        else:
            return Response({
                'success': False,
                'error': 'API key not found'
            }, status=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return Response({
            'success': False,
            'error': 'Invalid key ID'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(
            'rotate_api_key_error',
            error=str(e),
            user_id=request.user.id
        )
        return Response({
            'success': False,
            'error': 'Failed to rotate API key'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)