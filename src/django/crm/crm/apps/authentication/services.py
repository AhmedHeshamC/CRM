"""
Authentication Services - Business Logic Layer
Following SOLID principles and clean architecture
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.exceptions import ValidationError
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import NotFound, PermissionDenied
import structlog

from .models import UserProfile
from .audit_logging import audit_logger, AuditEventType
from shared.repositories.simple_cache import SimpleCache, CachedRepositoryMixin

User = get_user_model()
logger = structlog.get_logger(__name__)


class UserRegistrationService:
    """
    Service for user registration following Single Responsibility Principle
    Handles all user creation logic with proper validation and security
    """

    def __init__(self):
        self.audit_logger = audit_logger

    def register_user(self, user_data, request=None):
        """
        Register a new user with comprehensive validation

        Args:
            user_data: Validated user data
            request: HTTP request context

        Returns:
            Created user instance
        """
        try:
            user = User.objects.create_user(**user_data)

            # Log registration event
            self.audit_logger.log_authentication_event(
                event_type=AuditEventType.USER_CREATED,
                user=user,
                request=request,
                details={'registration_method': 'api'},
                success=True
            )

            logger.info(
                'user_registered',
                user_id=user.id,
                email=user.email,
                role=user.role
            )

            return user

        except Exception as e:
            logger.error(
                'user_registration_failed',
                error=str(e),
                email=user_data.get('email')
            )
            raise ValidationError(f"Registration failed: {str(e)}")


class UserAuthenticationService:
    """
    Service for user authentication following Single Responsibility Principle
    Handles login, logout, and token management
    """

    def __init__(self):
        self.audit_logger = audit_logger

    def authenticate_user(self, email, password, request=None):
        """
        Authenticate user with credentials

        Args:
            email: User email
            password: User password
            request: HTTP request context

        Returns:
            Authenticated user instance
        """
        from django.contrib.auth import authenticate

        user = authenticate(username=email, password=password)

        if user:
            # Log successful authentication
            self.audit_logger.log_authentication_event(
                event_type=AuditEventType.USER_LOGIN,
                user=user,
                request=request,
                details={'authentication_method': 'password'},
                success=True
            )

            logger.info(
                'user_authenticated',
                user_id=user.id,
                email=user.email,
                ip_address=self._get_client_ip(request) if request else None
            )

            return user
        else:
            # Log failed authentication attempt
            self.audit_logger.log_authentication_event(
                event_type=AuditEventType.USER_LOGIN_FAILED,
                user=None,
                request=request,
                details={'email_attempted': email},
                success=False
            )

            logger.warning(
                'authentication_failed',
                email=email,
                ip_address=self._get_client_ip(request) if request else None
            )

            return None

    def generate_tokens(self, user):
        """
        Generate JWT tokens for authenticated user

        Args:
            user: Authenticated user instance

        Returns:
            Dictionary with access and refresh tokens
        """
        refresh = RefreshToken.for_user(user)

        return {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh)
        }

    def logout_user(self, refresh_token, request=None):
        """
        Logout user by blacklisting refresh token

        Args:
            refresh_token: JWT refresh token
            request: HTTP request context

        Returns:
            Success status
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            # Log logout event
            if request and request.user.is_authenticated:
                self.audit_logger.log_authentication_event(
                    event_type=AuditEventType.USER_LOGOUT,
                    user=request.user,
                    request=request,
                    success=True
                )

                logger.info(
                    'user_logged_out',
                    user_id=request.user.id,
                    email=request.user.email
                )

            return True

        except Exception as e:
            logger.error(
                'logout_failed',
                error=str(e)
            )
            return False

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class UserManagementService:
    """
    Simple user management service following KISS and SOLID principles
    Handles user CRUD operations without complex caching dependencies
    """

    def __init__(self):
        self.audit_logger = audit_logger
        self.cache = SimpleCache(prefix="user_", timeout=300)

    def get_user_queryset(self, requesting_user):
        """
        Simple user queryset based on permissions - KISS principle

        Args:
            requesting_user: User making the request

        Returns:
            Filtered queryset
        """
        # Simple permission check without complex caching
        if hasattr(requesting_user, 'is_admin') and requesting_user.is_admin():
            return User.objects.all()

        return User.objects.filter(id=requesting_user.id)

    def _build_user_queryset(self, requesting_user):
        """
        Build user queryset based on permissions
        Separate method to follow Single Responsibility Principle
        """
        if requesting_user.is_admin():
            return User.objects.all()
        elif requesting_user.is_manager():
            return User.objects.all()
        else:
            return User.objects.filter(id=requesting_user.id)

    def can_access_user(self, requesting_user, target_user):
        """
        Check if requesting user can access target user

        Args:
            requesting_user: User making the request
            target_user: User being accessed

        Returns:
            Boolean indicating access permission
        """
        # Users can always access themselves
        if requesting_user.id == target_user.id:
            return True

        # Admin users can access all users
        if requesting_user.is_admin():
            return True

        # Managers can access users based on business rules
        if requesting_user.is_manager():
            return self._can_manager_access_user(requesting_user, target_user)

        return False

    def _can_manager_access_user(self, manager, user):
        """
        Check if manager can access a specific user
        Business logic for manager access control
        """
        # For now, managers can access all users
        # This can be refined based on business requirements
        return True

    def update_user(self, user, update_data, requesting_user, request=None):
        """
        Update user with proper authorization and audit logging

        Args:
            user: User to update
            update_data: Data to update
            requesting_user: User making the request
            request: HTTP request context

        Returns:
            Updated user instance
        """
        # Check permissions
        if not self.can_access_user(requesting_user, user):
            raise PermissionDenied("You don't have permission to update this user.")

        # Store old values for audit logging
        old_values = {}
        for field in update_data.keys():
            if hasattr(user, field):
                old_values[field] = getattr(user, field)

        try:
            # Update user fields
            for field, value in update_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)

            user.save()

            # Log update event
            self.audit_logger.log_data_modification(
                event_type=AuditEventType.USER_UPDATED,
                user=requesting_user,
                resource_type='user',
                resource_id=str(user.id),
                old_values=old_values,
                new_values=update_data,
                request=request
            )

            logger.info(
                'user_updated',
                user_id=user.id,
                updated_by=requesting_user.id,
                updated_fields=list(update_data.keys())
            )

            return user

        except Exception as e:
            logger.error(
                'user_update_failed',
                error=str(e),
                user_id=user.id,
                updated_by=requesting_user.id
            )
            raise ValidationError(f"Update failed: {str(e)}")

    def deactivate_user(self, user, requesting_user, request=None):
        """
        Deactivate user with proper authorization

        Args:
            user: User to deactivate
            requesting_user: User making the request
            request: HTTP request context

        Returns:
            Success status
        """
        # Prevent self-deactivation
        if user.id == requesting_user.id:
            raise ValidationError("You cannot deactivate your own account.")

        # Check permissions
        if not self.can_access_user(requesting_user, user):
            raise PermissionDenied("You don't have permission to deactivate this user.")

        try:
            user.is_active = False
            user.save()

            # Log deactivation event
            self.audit_logger.log_data_modification(
                event_type=AuditEventType.USER_DEACTIVATED,
                user=requesting_user,
                resource_type='user',
                resource_id=str(user.id),
                old_values={'is_active': True},
                new_values={'is_active': False},
                request=request
            )

            logger.info(
                'user_deactivated',
                user_id=user.id,
                deactivated_by=requesting_user.id
            )

            return True

        except Exception as e:
            logger.error(
                'user_deactivation_failed',
                error=str(e),
                user_id=user.id,
                deactivated_by=requesting_user.id
            )
            raise ValidationError(f"Deactivation failed: {str(e)}")

    def delete_user(self, user, requesting_user, request=None):
        """
        Delete user with proper authorization

        Args:
            user: User to delete
            requesting_user: User making the request
            request: HTTP request context

        Returns:
            Success status
        """
        # Prevent self-deletion
        if user.id == requesting_user.id:
            raise ValidationError("You cannot delete your own account.")

        # Check permissions
        if not self.can_access_user(requesting_user, user):
            raise PermissionDenied("You don't have permission to delete this user.")

        try:
            user_id = user.id
            user_email = user.email
            user.delete()

            # Log deletion event
            self.audit_logger.log_data_modification(
                event_type=AuditEventType.USER_DELETED,
                user=requesting_user,
                resource_type='user',
                resource_id=str(user_id),
                old_values={'email': user_email, 'is_active': user.is_active},
                new_values={},
                request=request
            )

            logger.info(
                'user_deleted',
                user_id=user_id,
                deleted_by=requesting_user.id,
                email=user_email
            )

            return True

        except Exception as e:
            logger.error(
                'user_deletion_failed',
                error=str(e),
                user_id=user.id,
                deleted_by=requesting_user.id
            )
            raise ValidationError(f"Deletion failed: {str(e)}")


class UserSearchService:
    """
    Service for user search operations following Single Responsibility Principle
    Handles complex search queries with proper filtering
    """

    def __init__(self):
        pass

    def search_users(self, query, requesting_user, role=None, is_active=None, limit=50):
        """
        Search users with comprehensive filtering

        Args:
            query: Search query string
            requesting_user: User making the request
            role: Optional role filter
            is_active: Optional active status filter
            limit: Maximum number of results

        Returns:
            QuerySet of matching users
        """
        # Get base queryset based on permissions
        user_service = UserManagementService()
        queryset = user_service.get_user_queryset(requesting_user)

        # Apply search filter
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query)
            )

        # Apply additional filters
        if role:
            queryset = queryset.filter(role=role)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        # Limit results for performance
        return queryset[:limit]

    def filter_users(self, requesting_user, **filters):
        """
        Filter users based on provided criteria

        Args:
            requesting_user: User making the request
            **filters: Filter criteria

        Returns:
            QuerySet of filtered users
        """
        user_service = UserManagementService()
        queryset = user_service.get_user_queryset(requesting_user)

        # Apply filters
        role = filters.get('role')
        if role:
            queryset = queryset.filter(role=role)

        is_active = filters.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        department = filters.get('department')
        if department:
            queryset = queryset.filter(department__icontains=department)

        search = filters.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(department__icontains=search)
            )

        return queryset


class UserProfileService:
    """
    Service for user profile management following Single Responsibility Principle
    Handles profile CRUD operations
    """

    def __init__(self):
        self.audit_logger = audit_logger

    def get_or_create_profile(self, user):
        """
        Get or create user profile

        Args:
            user: User instance

        Returns:
            UserProfile instance
        """
        try:
            return user.profile
        except UserProfile.DoesNotExist:
            return UserProfile.objects.create(user=user)

    def update_profile(self, user, profile_data, requesting_user, request=None):
        """
        Update user profile with proper authorization

        Args:
            user: User whose profile is being updated
            profile_data: Profile update data
            requesting_user: User making the request
            request: HTTP request context

        Returns:
            Updated profile instance
        """
        # Check permissions
        if user.id != requesting_user.id and not requesting_user.is_admin():
            raise PermissionDenied("You can only update your own profile.")

        profile = self.get_or_create_profile(user)

        try:
            # Update profile fields
            for field, value in profile_data.items():
                if hasattr(profile, field):
                    setattr(profile, field, value)

            profile.save()

            # Log profile update
            self.audit_logger.log_data_modification(
                event_type=AuditEventType.USER_UPDATED,
                user=requesting_user,
                resource_type='user_profile',
                resource_id=str(profile.id),
                new_values=profile_data,
                request=request
            )

            logger.info(
                'user_profile_updated',
                user_id=user.id,
                updated_by=requesting_user.id,
                updated_fields=list(profile_data.keys())
            )

            return profile

        except Exception as e:
            logger.error(
                'profile_update_failed',
                error=str(e),
                user_id=user.id,
                updated_by=requesting_user.id
            )
            raise ValidationError(f"Profile update failed: {str(e)}")


class PasswordManagementService:
    """
    Service for password management following Single Responsibility Principle
    Handles password changes, resets, and security validation
    """

    def __init__(self):
        self.audit_logger = audit_logger

    def change_password(self, user, old_password, new_password, request=None):
        """
        Change user password with proper validation

        Args:
            user: User changing password
            old_password: Current password
            new_password: New password
            request: HTTP request context

        Returns:
            Success status
        """
        # Verify old password
        if not user.check_password(old_password):
            # Log failed password change attempt
            self.audit_logger.log_authentication_event(
                event_type=AuditEventType.PASSWORD_CHANGED,
                user=user,
                request=request,
                details={'success': False, 'reason': 'invalid_old_password'},
                success=False
            )
            raise ValidationError("Current password is incorrect.")

        try:
            user.set_password(new_password)
            user.save()

            # Log successful password change
            self.audit_logger.log_authentication_event(
                event_type=AuditEventType.PASSWORD_CHANGED,
                user=user,
                request=request,
                details={'success': True},
                success=True
            )

            logger.info(
                'password_changed',
                user_id=user.id,
                email=user.email
            )

            return True

        except Exception as e:
            logger.error(
                'password_change_failed',
                error=str(e),
                user_id=user.id
            )
            raise ValidationError(f"Password change failed: {str(e)}")

    def initiate_password_reset(self, email, request=None):
        """
        Initiate password reset process

        Args:
            email: User email
            request: HTTP request context

        Returns:
            Success message (don't reveal if user exists)
        """
        try:
            user = User.objects.get(email=email)
            # Generate password reset token and send email
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Log password reset request
            self.audit_logger.log_authentication_event(
                event_type=AuditEventType.PASSWORD_RESET_REQUESTED,
                user=user,
                request=request,
                details={'token_generated': True},
                success=True
            )

            logger.info(
                'password_reset_requested',
                user_id=user.id,
                email=email
            )

            # TODO: Send actual password reset email
            # For now, we'll just log it

        except User.DoesNotExist:
            # Don't reveal that the user doesn't exist
            logger.info(
                'password_reset_requested_for_nonexistent_user',
                email=email
            )

        return {
            'message': 'Password reset link sent to your email if account exists.'
        }

    def confirm_password_reset(self, uidb64, token, new_password, request=None):
        """
        Confirm password reset with token validation

        Args:
            uidb64: Base64 encoded user ID
            token: Password reset token
            new_password: New password
            request: HTTP request context

        Returns:
            Success status
        """
        try:
            # Decode user ID
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)

            # Validate token
            if not default_token_generator.check_token(user, token):
                raise ValidationError("Invalid or expired reset token.")

            # Set new password
            user.set_password(new_password)
            user.save()

            # Log successful password reset
            self.audit_logger.log_authentication_event(
                event_type=AuditEventType.PASSWORD_RESET_COMPLETED,
                user=user,
                request=request,
                details={'success': True},
                success=True
            )

            logger.info(
                'password_reset_completed',
                user_id=user.id,
                email=user.email
            )

            return True

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise ValidationError("Invalid reset link.")
        except Exception as e:
            logger.error(
                'password_reset_failed',
                error=str(e),
                uidb64=uidb64
            )
            raise ValidationError(f"Password reset failed: {str(e)}")


class BulkUserOperationService:
    """
    Service for bulk user operations following Single Responsibility Principle
    Handles bulk operations with proper authorization and logging
    """

    def __init__(self):
        self.audit_logger = audit_logger
        self.user_management_service = UserManagementService()

    def bulk_activate_users(self, user_ids, requesting_user, request=None):
        """
        Bulk activate users

        Args:
            user_ids: List of user IDs to activate
            requesting_user: User making the request
            request: HTTP request context

        Returns:
            Count of activated users
        """
        return self._bulk_operation('activate', user_ids, requesting_user, request)

    def bulk_deactivate_users(self, user_ids, requesting_user, request=None):
        """
        Bulk deactivate users

        Args:
            user_ids: List of user IDs to deactivate
            requesting_user: User making the request
            request: HTTP request context

        Returns:
            Count of deactivated users
        """
        return self._bulk_operation('deactivate', user_ids, requesting_user, request)

    def bulk_delete_users(self, user_ids, requesting_user, request=None):
        """
        Bulk delete users

        Args:
            user_ids: List of user IDs to delete
            requesting_user: User making the request
            request: HTTP request context

        Returns:
            Count of deleted users
        """
        return self._bulk_operation('delete', user_ids, requesting_user, request)

    def _bulk_operation(self, operation, user_ids, requesting_user, request=None):
        """
        Perform bulk operation with proper authorization and logging

        Args:
            operation: Operation type ('activate', 'deactivate', 'delete')
            user_ids: List of user IDs
            requesting_user: User making the request
            request: HTTP request context

        Returns:
            Count of affected users
        """
        updated_count = 0
        failed_users = []

        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)

                # Check permissions
                if not self.user_management_service.can_access_user(requesting_user, user):
                    failed_users.append({'user_id': user_id, 'reason': 'Permission denied'})
                    continue

                # Prevent self-operations
                if user.id == requesting_user.id:
                    failed_users.append({'user_id': user_id, 'reason': 'Cannot perform operation on self'})
                    continue

                # Perform operation
                if operation == 'activate':
                    user.is_active = True
                    user.save()
                    updated_count += 1
                elif operation == 'deactivate':
                    user.is_active = False
                    user.save()
                    updated_count += 1
                elif operation == 'delete':
                    user.delete()
                    updated_count += 1

            except User.DoesNotExist:
                failed_users.append({'user_id': user_id, 'reason': 'User not found'})
            except Exception as e:
                failed_users.append({'user_id': user_id, 'reason': str(e)})

        # Log bulk operation
        self.audit_logger.log_event(
            event_type=f'bulk_{operation}',
            user_id=requesting_user.id,
            user_email=requesting_user.email,
            request=request,
            resource_type='user',
            details={
                'operation': operation,
                'total_ids': len(user_ids),
                'successful_count': updated_count,
                'failed_count': len(failed_users),
                'failed_users': failed_users
            }
        )

        logger.info(
            f'bulk_{operation}_completed',
            requesting_user_id=requesting_user.id,
            operation=operation,
            total_ids=len(user_ids),
            successful_count=updated_count,
            failed_count=len(failed_users)
        )

        return {
            'updated_count': updated_count,
            'failed_count': len(failed_users),
            'failed_users': failed_users
        }