"""
Refactored Authentication ViewSets - Following SOLID Principles
Clean Architecture with Single Responsibility for each ViewSet
"""

from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse
import structlog

from .models import UserProfile
from .serializers import (
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, UserRegistrationSerializer,
    UserProfileSerializer, PasswordChangeSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer,
    LoginSerializer, UserBulkOperationSerializer, UserSearchSerializer
)
from .services import (
    UserRegistrationService, UserAuthenticationService, UserManagementService,
    UserSearchService, UserProfileService, PasswordManagementService,
    BulkUserOperationService
)
from ...shared.authentication.permissions import (
    IsAdminUser, IsManagerOrAdminUser, IsSelfOrAdmin,
    DynamicRolePermission
)

User = get_user_model()
logger = structlog.get_logger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """
    Refactored User ViewSet following SOLID principles

    This ViewSet is now much cleaner and focuses solely on:
    - HTTP request/response handling
    - Input validation
    - Permission checking
    - Response formatting

    All business logic is delegated to services.
    """

    permission_classes = [DynamicRolePermission]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize services (Dependency Injection)
        self.registration_service = UserRegistrationService()
        self.auth_service = UserAuthenticationService()
        self.management_service = UserManagementService()
        self.search_service = UserSearchService()
        self.profile_service = UserProfileService()
        self.password_service = PasswordManagementService()
        self.bulk_service = BulkUserOperationService()

    def get_queryset(self):
        """Delegate to UserManagementService for permission-based filtering"""
        return self.management_service.get_user_queryset(self.request.user)

    def get_serializer_class(self):
        """Select appropriate serializer based on action"""
        serializer_map = {
            'create': UserCreateSerializer,
            'update': UserUpdateSerializer,
            'partial_update': UserUpdateSerializer,
            'retrieve': UserDetailSerializer,
            'list': UserSerializer,
            'register': UserRegistrationSerializer,
            'login': LoginSerializer,
            'search': UserSearchSerializer,
            'bulk_operations': UserBulkOperationSerializer,
            'change_password': PasswordChangeSerializer,
            'password_reset': PasswordResetSerializer,
            'password_reset_confirm': PasswordResetConfirmSerializer,
        }
        return serializer_map.get(self.action, UserSerializer)

    def get_permissions(self):
        """Get permissions based on action"""
        if self.action == 'create':
            # Only admin and manager can create users
            user = self.request.user
            if not (user.is_admin() or user.is_manager()):
                raise PermissionDenied("You don't have permission to create users.")
            return [permissions.IsAuthenticated()]
        elif self.action in ['login', 'register', 'password_reset', 'password_reset_confirm']:
            return [AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        """Get user with permission checking"""
        pk = self.kwargs.get('pk')
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise NotFound('User not found.')

        # Check permissions
        if not self.management_service.can_access_user(self.request.user, user):
            raise NotFound('User not found.')

        return user

    def list(self, request, *args, **kwargs):
        """List users with filtering - use KISS principle with builder pattern"""
        from .viewset_filters import UserQuerysetBuilder

        # Get base queryset following SOLID principles
        base_queryset = self.search_service.filter_users(
            requesting_user=request.user,
            **request.query_params.dict()
        )

        # Use builder pattern for clean, readable filtering (KISS principle)
        builder = UserQuerysetBuilder(base_queryset)

        # Apply filters based on query parameters
        role = request.query_params.get('role')
        if role:
            builder = builder.filter_by_role(role)

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            builder = builder.filter_by_status(is_active)

        department = request.query_params.get('department')
        if department:
            builder = builder.filter_by_department(department)

        search = request.query_params.get('search')
        if search:
            builder = builder.search(search)

        # Build final queryset
        queryset = builder.build()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create user - delegate to registration service"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = self.registration_service.register_user(
                user_data=serializer.validated_data,
                request=request
            )
            response_serializer = UserDetailSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError:
            raise
        except Exception as e:
            logger.error('user_creation_error', error=str(e))
            raise ValidationError(f"User creation failed: {str(e)}")

    def update(self, request, *args, **kwargs):
        """Update user - delegate to management service"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            user = self.management_service.update_user(
                user=instance,
                update_data=serializer.validated_data,
                requesting_user=request.user,
                request=request
            )
            response_serializer = UserDetailSerializer(user)
            return Response(response_serializer.data)
        except ValidationError:
            raise
        except Exception as e:
            logger.error('user_update_error', error=str(e))
            raise ValidationError(f"User update failed: {str(e)}")

    def destroy(self, request, *args, **kwargs):
        """Delete user - delegate to management service"""
        instance = self.get_object()

        try:
            self.management_service.delete_user(
                user=instance,
                requesting_user=request.user,
                request=request
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError:
            raise
        except Exception as e:
            logger.error('user_deletion_error', error=str(e))
            raise ValidationError(f"User deletion failed: {str(e)}")

    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register new user - delegate to registration service"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = self.registration_service.register_user(
                user_data=serializer.validated_data,
                request=request
            )
            response_serializer = UserDetailSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError:
            raise
        except Exception as e:
            logger.error('registration_error', error=str(e))
            raise ValidationError(f"Registration failed: {str(e)}")

    @action(detail=False, methods=['post'])
    def login(self, request):
        """Login user and return JWT tokens - delegate to auth service"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Authenticate user
        user = self.auth_service.authenticate_user(email, password, request)
        if not user:
            raise ValidationError("Invalid email or password.")

        # Generate tokens
        tokens = self.auth_service.generate_tokens(user)

        return Response({
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'user': UserDetailSerializer(user).data
        })

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Logout user and blacklist refresh token - delegate to auth service"""
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            raise ValidationError('Refresh token is required.')

        if self.auth_service.logout_user(refresh_token, request):
            return Response({'message': 'Successfully logged out.'})
        else:
            raise ValidationError('Invalid refresh token.')

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Change user password - delegate to password service"""
        user = self.get_object()

        # Users can only change their own password
        if user.id != request.user.id:
            raise PermissionDenied("You can only change your own password.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.password_service.change_password(
                user=user,
                old_password=serializer.validated_data['old_password'],
                new_password=serializer.validated_data['new_password'],
                request=request
            )
            return Response({'message': 'Password changed successfully.'})
        except ValidationError:
            raise
        except Exception as e:
            logger.error('password_change_error', error=str(e))
            raise ValidationError(f"Password change failed: {str(e)}")

    @action(detail=True, methods=['post'])
    def update_profile(self, request, pk=None):
        """Update user profile - delegate to profile service"""
        user = self.get_object()

        # Users can only update their own profile
        if user.id != request.user.id:
            raise PermissionDenied("You can only update your own profile.")

        try:
            profile = self.profile_service.update_profile(
                user=user,
                profile_data=request.data,
                requesting_user=request.user,
                request=request
            )
            return Response({
                'message': 'Profile updated successfully.',
                'profile': UserProfileSerializer(profile).data
            })
        except ValidationError:
            raise
        except Exception as e:
            logger.error('profile_update_error', error=str(e))
            raise ValidationError(f"Profile update failed: {str(e)}")

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate user - delegate to management service"""
        user = self.get_object()

        try:
            self.management_service.deactivate_user(
                user=user,
                requesting_user=request.user,
                request=request
            )
            return Response({'message': 'User deactivated successfully.'})
        except ValidationError:
            raise
        except Exception as e:
            logger.error('user_deactivation_error', error=str(e))
            raise ValidationError(f"User deactivation failed: {str(e)}")

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate user - delegate to management service"""
        user = self.get_object()

        try:
            # Reactivation is just updating the is_active field
            self.management_service.update_user(
                user=user,
                update_data={'is_active': True},
                requesting_user=request.user,
                request=request
            )
            return Response({'message': 'User activated successfully.'})
        except ValidationError:
            raise
        except Exception as e:
            logger.error('user_activation_error', error=str(e))
            raise ValidationError(f"User activation failed: {str(e)}")

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search users - delegate to search service"""
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        users = self.search_service.search_users(
            query=serializer.validated_data['query'],
            requesting_user=request.user,
            role=serializer.validated_data.get('role'),
            is_active=serializer.validated_data.get('is_active'),
            limit=50
        )

        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """Perform bulk operations - delegate to bulk service"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_ids = serializer.validated_data['user_ids']
        operation = serializer.validated_data['operation']

        try:
            if operation == 'activate':
                result = self.bulk_service.bulk_activate_users(
                    user_ids=user_ids,
                    requesting_user=request.user,
                    request=request
                )
            elif operation == 'deactivate':
                result = self.bulk_service.bulk_deactivate_users(
                    user_ids=user_ids,
                    requesting_user=request.user,
                    request=request
                )
            elif operation == 'delete':
                result = self.bulk_service.bulk_delete_users(
                    user_ids=user_ids,
                    requesting_user=request.user,
                    request=request
                )
            else:
                raise ValidationError(f"Invalid operation: {operation}")

            return Response({
                'message': f'Bulk {operation} completed',
                'updated_count': result['updated_count'],
                'failed_count': result['failed_count'],
                'failed_users': result['failed_users']
            })
        except ValidationError:
            raise
        except Exception as e:
            logger.error('bulk_operation_error', error=str(e), operation=operation)
            raise ValidationError(f"Bulk operation failed: {str(e)}")

    @action(detail=False, methods=['post'])
    def password_reset(self, request):
        """Initiate password reset - delegate to password service"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.password_service.initiate_password_reset(
                email=serializer.validated_data['email'],
                request=request
            )
            return Response(result)
        except Exception as e:
            logger.error('password_reset_request_error', error=str(e))
            raise ValidationError(f"Password reset request failed: {str(e)}")

    @action(detail=False, methods=['post'])
    def password_reset_confirm(self, request):
        """Confirm password reset - delegate to password service"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.password_service.confirm_password_reset(
                uidb64=serializer.validated_data['uidb64'],
                token=serializer.validated_data['token'],
                new_password=serializer.validated_data['new_password'],
                request=request
            )
            return Response({'message': 'Password reset successfully.'})
        except ValidationError:
            raise
        except Exception as e:
            logger.error('password_reset_confirm_error', error=str(e))
            raise ValidationError(f"Password reset confirmation failed: {str(e)}")


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    Simplified User Profile ViewSet following SOLID principles

    Focused solely on profile management with clean separation of concerns.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsSelfOrAdmin]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile_service = UserProfileService()
        self.management_service = UserManagementService()

    def get_queryset(self):
        """Get profiles based on user permissions"""
        user = self.request.user
        if user.is_admin():
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=user)

    def get_object(self):
        """Get profile with permission checking"""
        pk = self.kwargs.get('pk')
        try:
            profile = UserProfile.objects.get(pk=pk)
        except UserProfile.DoesNotExist:
            raise NotFound('Profile not found.')

        # Check permissions
        if not self.management_service.can_access_user(self.request.user, profile.user):
            raise NotFound('Profile not found.')

        return profile

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """Get or update current user's profile"""
        profile = self.profile_service.get_or_create_profile(request.user)

        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            try:
                updated_profile = self.profile_service.update_profile(
                    user=request.user,
                    profile_data=serializer.validated_data,
                    requesting_user=request.user,
                    request=request
                )
                return Response(serializer.data)
            except ValidationError:
                raise
            except Exception as e:
                logger.error('profile_me_update_error', error=str(e))
                raise ValidationError(f"Profile update failed: {str(e)}")


# Simple API views for token management
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework.decorators import api_view, permission_classes


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_token_refresh(request):
    """
    Custom token refresh endpoint with enhanced error handling
    Following Single Responsibility Principle for token management
    """
    serializer = TokenRefreshSerializer(data=request.data)

    if not serializer.is_valid():
        logger.warning('token_refresh_validation_failed', errors=serializer.errors)
        raise ValidationError(serializer.errors)

    try:
        logger.info('token_refresh_successful')
        return Response(serializer.validated_data)
    except Exception as e:
        logger.error('token_refresh_failed', error=str(e))
        raise ValidationError(f"Token refresh failed: {str(e)}")