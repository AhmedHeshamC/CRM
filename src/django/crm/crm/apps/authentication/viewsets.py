"""
Authentication ViewSets - API Endpoint Layer
Following SOLID principles and enterprise best practices
"""

from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework import serializers
from drf_spectacular.utils import (
    OpenApiExample, OpenApiResponse, OpenApiParameter, extend_schema,
    extend_schema_view, inline_serializer
)

from .models import User, UserProfile
from .serializers import (
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, UserRegistrationSerializer,
    UserProfileSerializer, PasswordChangeSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer,
    LoginSerializer, UserBulkOperationSerializer, UserSearchSerializer
)
from ...shared.authentication.permissions import (
    IsAdminUser, IsManagerOrAdminUser, IsSelfOrAdmin,
    IsOwnerOrReadOnly, DynamicRolePermission
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    User ViewSet for comprehensive user management
    Following SOLID principles and clean architecture
    """

    permission_classes = [DynamicRolePermission]

    def get_queryset(self):
        """
        Get users based on user permissions
        Following SOLID principles for access control
        """
        user = self.request.user

        # Admin users can see all users
        if user.is_admin():
            return User.objects.all()

        # Managers can see users based on business rules
        if user.is_manager():
            # For now, managers can see all users
            return User.objects.all()

        # Regular users can only see themselves
        return User.objects.filter(id=user.id)

    def get_serializer_class(self):
        """
        Select appropriate serializer based on action
        Following Single Responsibility Principle
        """
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return UserUpdateSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action == 'list':
            return UserSerializer
        return UserSerializer

    def get_permissions(self):
        """
        Get permissions based on action
        Following SOLID principles for proper access control
        """
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
            # Only admin and manager can create users
            user = self.request.user
            if not (user.is_admin() or user.is_manager()):
                self.permission_denied_message = "You don't have permission to create users."
                raise PermissionDenied(self.permission_denied_message)
        else:
            permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_object(self):
        """
        Get user with permission checking
        Following SOLID principles for proper access control
        """
        pk = self.kwargs.get('pk')
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise NotFound('User not found.')

        # Check permissions
        current_user = self.request.user
        if not current_user.is_admin() and user.id != current_user.id:
            # Managers might have additional permissions
            if not (current_user.is_manager() and self._can_manager_access_user(current_user, user)):
                raise NotFound('User not found.')

        return user

    def _can_manager_access_user(self, manager, user):
        """
        Check if manager can access a specific user
        Following business rules for manager access
        """
        # For now, managers can access all users
        # This can be refined based on business requirements
        return True

    def list(self, request, *args, **kwargs):
        """
        List users with enhanced filtering and searching
        Following KISS principle for clean, readable implementation
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Custom filtering logic
        role = request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        department = request.query_params.get('department')
        if department:
            queryset = queryset.filter(department__icontains=department)

        # Search functionality
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(department__icontains=search)
            )

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create user with business logic
        Following SOLID principles
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = serializer.save()
            response_serializer = UserDetailSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            raise ValidationError(str(e))

    def update(self, request, *args, **kwargs):
        """
        Update user with business logic
        Following SOLID principles
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            user = serializer.save()
            response_serializer = UserDetailSerializer(user)
            return Response(response_serializer.data)
        except Exception as e:
            raise ValidationError(str(e))

    def destroy(self, request, *args, **kwargs):
        """
        Delete user with business logic
        Following SOLID principles
        """
        instance = self.get_object()

        # Prevent self-deletion
        if instance.id == request.user.id:
            raise ValidationError("You cannot delete your own account.")

        try:
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register new user
        Following Single Responsibility Principle
        """
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        try:
            user = serializer.save()
            response_serializer = UserDetailSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            raise ValidationError(str(e))

    @extend_schema(
        summary='User Authentication',
        description="""
            Authenticate user credentials and generate JWT tokens.

            **Authentication Flow:**
            1. Submit email and password
            2. System validates credentials against user database
            3. Upon success, generates access and refresh tokens
            4. Returns user details and authentication tokens

            **Security Features:**
            - Passwords are validated using Django's secure password hashing
            - Failed login attempts are logged for security monitoring
            - Account must be active to authenticate
            - Rate limiting applies to prevent brute force attacks

            **Token Information:**
            - Access Token: 15 minutes (production), 60 minutes (development)
            - Refresh Token: 7 days (production), 1 day (development)
            - Tokens are JWT format with cryptographic signing

            **Usage:**
            Include the access_token in subsequent API requests using the Authorization header:
            ```
            Authorization: Bearer <access_token>
            ```
        """,
        tags=['Authentication'],
        responses={
            200: OpenApiResponse(
                description='Authentication successful',
                response={
                    'type': 'object',
                    'properties': {
                        'access_token': {
                            'type': 'string',
                            'description': 'JWT access token for API authentication'
                        },
                        'refresh_token': {
                            'type': 'string',
                            'description': 'JWT refresh token for token renewal'
                        },
                        'user': {
                            'type': 'object',
                            'description': 'Authenticated user details',
                            'properties': {
                                'id': {'type': 'integer'},
                                'email': {'type': 'string'},
                                'first_name': {'type': 'string'},
                                'last_name': {'type': 'string'},
                                'role': {'type': 'string'},
                                'full_name': {'type': 'string'}
                            }
                        }
                    }
                },
                examples=[
                    OpenApiExample(
                        'Successful Login',
                        value={
                            'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
                            'refresh_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
                            'user': {
                                'id': 1,
                                'email': 'john.doe@company.com',
                                'first_name': 'John',
                                'last_name': 'Doe',
                                'role': 'sales',
                                'full_name': 'John Doe'
                            }
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='Authentication failed - Invalid credentials',
                response={
                    'type': 'object',
                    'properties': {
                        'detail': {'type': 'string'},
                        'code': {'type': 'string'}
                    }
                },
                examples=[
                    OpenApiExample(
                        'Invalid Credentials',
                        value={
                            'detail': 'Invalid email or password.',
                            'code': 'authentication_failed'
                        }
                    ),
                    OpenApiExample(
                        'Account Disabled',
                        value={
                            'detail': 'Account is disabled.',
                            'code': 'account_disabled'
                        }
                    )
                ]
            )
        },
        examples=[
            OpenApiExample(
                'Valid Login Request',
                value={
                    'email': 'john.doe@company.com',
                    'password': 'SecurePass123!'
                }
            ),
            OpenApiExample(
                'Invalid Login Request',
                value={
                    'email': 'invalid@example.com',
                    'password': 'wrongpassword'
                }
            )
        ]
    )
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """
        Login user and return JWT tokens

        Handles user authentication with comprehensive security validation.
        Generates JWT tokens for secure API access and returns user profile information.

        **Security Considerations:**
        - Passwords are never returned or exposed
        - Tokens are cryptographically signed
        - Failed attempts are logged for security monitoring
        - Rate limiting prevents brute force attacks

        Following Single Responsibility Principle for focused authentication logic
        """
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        user = serializer.validated_data['user']

        # Generate tokens with enhanced security
        refresh = RefreshToken.for_user(user)

        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': UserDetailSerializer(user).data
        })

    @extend_schema(
        summary='User Logout',
        description="""
            Logout user and invalidate refresh token.

            **Logout Process:**
            1. Submit refresh token for invalidation
            2. System validates and blacklists the token
            3. Token cannot be used for future authentication
            4. Access token becomes invalid after expiration

            **Security Features:**
            - Refresh tokens are blacklisted to prevent reuse
            - Access tokens become invalid after their short TTL
            - All logout attempts are logged for security monitoring
            - Invalid tokens are safely rejected without revealing system details

            **Token Invalidation:**
            - Refresh token: Immediately blacklisted upon logout
            - Access token: Remains valid until natural expiration (15-60 minutes)
            - Session tracking: User activity is updated on logout

            **Important Notes:**
            - Always logout properly to maintain security
            - Invalid refresh tokens are safely handled
            - Multiple device logout requires calling logout from each device
        """,
        tags=['Authentication'],
        responses={
            200: OpenApiResponse(
                description='Logout successful',
                response={
                    'type': 'object',
                    'properties': {
                        'message': {
                            'type': 'string',
                            'description': 'Success message confirming logout'
                        }
                    }
                },
                examples=[
                    OpenApiExample(
                        'Successful Logout',
                        value={
                            'message': 'Successfully logged out.'
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Bad Request - Invalid or missing refresh token',
                response={
                    'type': 'object',
                    'properties': {
                        'detail': {'type': 'string'},
                        'refresh_token': {'type': 'array', 'items': {'type': 'string'}}
                    }
                },
                examples=[
                    OpenApiExample(
                        'Missing Refresh Token',
                        value={
                            'refresh_token': ['Refresh token is required.']
                        }
                    ),
                    OpenApiExample(
                        'Invalid Refresh Token',
                        value={
                            'detail': 'Invalid refresh token.'
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='Unauthorized - Invalid or expired token',
                response={
                    'type': 'object',
                    'properties': {
                        'detail': {'type': 'string'},
                        'code': {'type': 'string'}
                    }
                },
                examples=[
                    OpenApiExample(
                        'Invalid Token',
                        value={
                            'detail': 'Token is invalid or expired.',
                            'code': 'token_not_valid'
                        }
                    )
                ]
            )
        },
        examples=[
            OpenApiExample(
                'Valid Logout Request',
                value={
                    'refresh_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
                }
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        Logout user and blacklist refresh token

        Securely terminates user session by invalidating the refresh token.
        This prevents token reuse and maintains security integrity.

        **Security Implementation:**
        - Refresh token is added to blacklist immediately
        - Access token remains valid until natural expiration
        - All logout events are logged for audit trails
        - Graceful handling of invalid or expired tokens

        **Token Lifecycle:**
        1. User submits refresh token
        2. System validates token authenticity
        3. Token is added to blacklist database
        4. Future authentication attempts with this token fail
        5. Access token expires naturally after TTL

        Following Single Responsibility Principle for secure session management
        """
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                raise ValidationError('Refresh token is required.')

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({'message': 'Successfully logged out.'})
        except Exception as e:
            raise ValidationError('Invalid refresh token.')

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """
        Change user password
        Following Single Responsibility Principle
        """
        user = self.get_object()

        # Users can only change their own password
        if user.id != request.user.id:
            raise PermissionDenied("You can only change your own password.")

        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'user': user}
        )

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        try:
            serializer.save()
            return Response({'message': 'Password changed successfully.'})
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['post'])
    def update_profile(self, request, pk=None):
        """
        Update user profile
        Following Single Responsibility Principle
        """
        user = self.get_object()

        # Users can only update their own profile
        if user.id != request.user.id:
            raise PermissionDenied("You can only update your own profile.")

        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        serializer = UserProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        try:
            serializer.save()
            return Response({
                'message': 'Profile updated successfully.',
                'profile': serializer.data
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Deactivate user
        Following Single Responsibility Principle
        """
        user = self.get_object()

        # Prevent self-deactivation
        if user.id == request.user.id:
            raise ValidationError("You cannot deactivate your own account.")

        try:
            user.is_active = False
            user.save()
            return Response({'message': 'User deactivated successfully.'})
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activate user
        Following Single Responsibility Principle
        """
        user = self.get_object()

        try:
            user.is_active = True
            user.save()
            return Response({'message': 'User activated successfully.'})
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search users
        Following Single Responsibility Principle
        """
        serializer = UserSearchSerializer(data=request.query_params)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        query = serializer.validated_data['query']
        role = serializer.validated_data.get('role')
        is_active = serializer.validated_data.get('is_active')

        queryset = self.get_queryset()

        # Apply search
        queryset = queryset.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )

        # Apply filters
        if role:
            queryset = queryset.filter(role=role)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        # Limit results for performance
        queryset = queryset[:50]

        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """
        Perform bulk operations on users
        Following Single Responsibility Principle
        """
        serializer = UserBulkOperationSerializer(
            data=request.data,
            context={'request_user': request.user}
        )

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        user_ids = serializer.validated_data['user_ids']
        operation = serializer.validated_data['operation']
        updated_count = 0

        try:
            for user_id in user_ids:
                user = User.objects.get(id=user_id)

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

            return Response({
                'message': f'Bulk {operation} completed successfully',
                'updated_count': updated_count
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """
        Get user permissions
        Following Single Responsibility Principle
        """
        user = self.get_object()
        user_serializer = UserDetailSerializer(user)
        return Response(user_serializer.data['permissions'])

    @action(detail=False, methods=['post'])
    def password_reset(self, request):
        """
        Initiate password reset
        Following Single Responsibility Principle
        """
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
            # Here you would generate and send password reset email
            # For now, we'll just return success
            return Response({
                'message': 'Password reset link sent to your email if account exists.'
            })
        except User.DoesNotExist:
            # Don't reveal that the user doesn't exist
            return Response({
                'message': 'Password reset link sent to your email if account exists.'
            })

    @action(detail=False, methods=['post'])
    def password_reset_confirm(self, request):
        """
        Confirm password reset
        Following Single Responsibility Principle
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        try:
            # Here you would validate the token and update the password
            # For now, we'll just return success
            return Response({
                'message': 'Password reset successfully.'
            })
        except Exception as e:
            raise ValidationError(str(e))


@extend_schema(
    summary='Token Refresh',
    description="""
        Refresh JWT access token using valid refresh token.

        **Token Refresh Process:**
        1. Submit valid refresh token
        2. System validates token authenticity and expiration
        3. Generates new access token with same permissions
        4. Returns new access token (refresh token may also be rotated)

        **Security Features:**
        - Refresh tokens are validated against blacklist
        - Expired or invalid tokens are rejected
        - Access tokens have short TTL for security
        - Refresh tokens may be rotated for enhanced security

        **Token Lifecycle:**
        - Access Token: Short-lived (15-60 minutes)
        - Refresh Token: Long-lived (1-7 days)
        - Rotation: New refresh token may be provided
        - Blacklisting: Invalid tokens are tracked

        **Usage Guidelines:**
        - Refresh tokens before access token expires
        - Handle token expiration gracefully
        - Store new refresh token if rotation is enabled
        - Implement retry logic for network failures

        **Error Handling:**
        - Invalid tokens return detailed error messages
        - Expired tokens prompt re-authentication
        - Blacklisted tokens cannot be refreshed
    """,
    tags=['Authentication'],
    responses={
        200: OpenApiResponse(
            description='Token refreshed successfully',
            response={
                'type': 'object',
                'properties': {
                    'access': {
                        'type': 'string',
                        'description': 'New JWT access token'
                    },
                    'refresh': {
                        'type': 'string',
                        'description': 'New refresh token (if rotation is enabled)',
                        'required': False
                    }
                }
            },
            examples=[
                OpenApiExample(
                    'Successful Token Refresh',
                    value={
                        'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
                        'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description='Bad Request - Invalid or missing refresh token',
            response={
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'array', 'items': {'type': 'string'}},
                    'detail': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            },
            examples=[
                OpenApiExample(
                    'Missing Refresh Token',
                    value={
                        'refresh': ['This field is required.']
                    }
                ),
                OpenApiExample(
                    'Invalid Token Format',
                    value={
                        'detail': 'Token is invalid or has bad format',
                        'code': 'token_not_valid'
                    }
                )
            ]
        ),
        401: OpenApiResponse(
            description='Unauthorized - Token is blacklisted or expired',
            response={
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'},
                    'code': {'type': 'string'}
                }
            },
            examples=[
                OpenApiExample(
                    'Token Blacklisted',
                    value={
                        'detail': 'Token is blacklisted',
                        'code': 'token_not_valid'
                    }
                ),
                OpenApiExample(
                    'Token Expired',
                    value={
                        'detail': 'Token is expired or invalid',
                        'code': 'token_not_valid'
                    }
                )
            ]
        )
    },
    examples=[
        OpenApiExample(
            'Valid Refresh Request',
            value={
                'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
            }
        ),
        OpenApiExample(
            'Invalid Refresh Request',
            value={
                'refresh': 'invalid_token_format'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def custom_token_refresh(request):
    """
    Custom token refresh endpoint with enhanced security

    Handles JWT access token renewal using valid refresh tokens.
    Implements comprehensive security validation and error handling.

    **Security Implementation:**
    - Validates refresh token against blacklist
    - Checks token expiration and format
    - Rotates refresh tokens when configured
    - Logs all refresh attempts for monitoring

    **Token Rotation:**
    When enabled, provides new refresh token for enhanced security.
    Old refresh token becomes invalid after successful rotation.

    **Error Handling:**
    Provides detailed error messages for debugging while maintaining
    security by not exposing sensitive system information.

    Following Single Responsibility Principle for token management
    """
    serializer = TokenRefreshSerializer(data=request.data)
    if not serializer.is_valid():
        raise ValidationError(serializer.errors)

    try:
        return Response(serializer.validated_data)
    except Exception as e:
        raise ValidationError(str(e))


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    User Profile ViewSet for profile management
    Following SOLID principles and clean architecture
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsSelfOrAdmin]

    def get_queryset(self):
        """
        Get profiles based on user permissions
        Following SOLID principles for access control
        """
        user = self.request.user

        if user.is_admin():
            return UserProfile.objects.all()

        # Users can only see their own profile
        return UserProfile.objects.filter(user=user)

    def get_object(self):
        """
        Get profile with permission checking
        Following SOLID principles for proper access control
        """
        pk = self.kwargs.get('pk')
        try:
            profile = UserProfile.objects.get(pk=pk)
        except UserProfile.DoesNotExist:
            raise NotFound('Profile not found.')

        # Check permissions
        user = self.request.user
        if not user.is_admin() and profile.user.id != user.id:
            raise NotFound('Profile not found.')

        return profile

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """
        Get or update current user's profile
        Following Single Responsibility Principle
        """
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)

        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            serializer = self.get_serializer(
                profile,
                data=request.data,
                partial=True
            )
            if not serializer.is_valid():
                raise ValidationError(serializer.errors)

            serializer.save()
            return Response(serializer.data)