"""
User Repository Implementation
Following SOLID principles and enterprise best practices
"""

from typing import List, Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.cache import cache
from django.utils import timezone
import logging

from .base import BaseRepository

logger = logging.getLogger(__name__)
User = get_user_model()


class UserRepository(BaseRepository[User]):
    """
    Repository for User model operations
    Following Repository Pattern and SOLID principles
    """

    def __init__(self, cache_timeout: int = 300):
        """Initialize user repository"""
        super().__init__(User, cache_timeout)

    def get_by_email(self, email: str, use_cache: bool = True) -> Optional[User]:
        """
        Get user by email (case-insensitive)

        Args:
            email: User email
            use_cache: Whether to use cache

        Returns:
            User instance or None
        """
        cache_key = self.get_cache_key(f"email_{email.lower()}")

        if use_cache:
            cached_user = cache.get(cache_key)
            if cached_user:
                logger.debug(f"Cache hit for user email {email}")
                return cached_user

        try:
            user = User.objects.get(email__iexact=email)
            if use_cache:
                cache.set(cache_key, user, self.cache_timeout)
            return user
        except User.DoesNotExist:
            logger.debug(f"User with email {email} not found")
            return None

    def get_active_users(self, use_cache: bool = False) -> List[User]:
        """
        Get all active users

        Args:
            use_cache: Whether to use cache

        Returns:
            List of active users
        """
        cache_key = self.get_cache_key("active_users")

        if use_cache:
            cached_users = cache.get(cache_key)
            if cached_users:
                return cached_users

        users = list(User.objects.filter(is_active=True))
        if use_cache:
            cache.set(cache_key, users, self.cache_timeout)
        return users

    def get_users_by_role(self, role: str) -> List[User]:
        """
        Get users by specific role

        Args:
            role: User role

        Returns:
            List of users with specified role
        """
        cache_key = self.get_cache_key(f"role_{role}")
        cached_users = cache.get(cache_key)
        if cached_users:
            return cached_users

        users = list(User.objects.filter(role=role, is_active=True))
        cache.set(cache_key, users, self.cache_timeout)
        return users

    def search_users(self, query: str) -> List[User]:
        """
        Search users by name, email

        Args:
            query: Search query

        Returns:
            List of matching users
        """
        cache_key = self.get_cache_key(f"search_{query.lower()}")

        cached_users = cache.get(cache_key)
        if cached_users:
            return cached_users

        users = list(User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(company__icontains=query)
        ).filter(is_active=True))

        cache.set(cache_key, users, self.cache_timeout // 2)  # Shorter cache for search
        return users

    def create_user(self, email: str, password: str, **kwargs) -> User:
        """
        Create new user with password

        Args:
            email: User email
            password: User password
            **kwargs: Additional user data

        Returns:
            Created user
        """
        user = User.objects.create_user(
            email=email,
            password=password,
            **kwargs
        )

        # Invalidate cache
        self._invalidate_cache_pattern("active_users")
        self._invalidate_cache_pattern(f"role_{user.role}")
        self._invalidate_cache_pattern(f"email_{email.lower()}")

        logger.info(f"Created user with email {email}")
        return user

    def create_superuser(self, email: str, password: str, **kwargs) -> User:
        """
        Create superuser

        Args:
            email: Superuser email
            password: Superuser password
            **kwargs: Additional user data

        Returns:
            Created superuser
        """
        superuser = User.objects.create_superuser(
            email=email,
            password=password,
            **kwargs
        )

        # Invalidate cache
        self._invalidate_cache_pattern("active_users")
        self._invalidate_cache_pattern("role_admin")
        self._invalidate_cache_pattern(f"email_{email.lower()}")

        logger.info(f"Created superuser with email {email}")
        return superuser

    def update_password(self, user_id: int, new_password: str) -> bool:
        """
        Update user password

        Args:
            user_id: User ID
            new_password: New password

        Returns:
            True if updated, False otherwise
        """
        try:
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{user_id}")
            if hasattr(user, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{user.uuid}")
            self._invalidate_cache_pattern(f"email_{user.email.lower()}")

            logger.info(f"Updated password for user ID {user_id}")
            return True
        except User.DoesNotExist:
            logger.warning(f"Failed to update password for user ID {user_id}: Not found")
            return False

    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate user account

        Args:
            user_id: User ID

        Returns:
            True if deactivated, False otherwise
        """
        try:
            user = User.objects.get(id=user_id)
            user.is_active = False
            user.save()

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{user_id}")
            if hasattr(user, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{user.uuid}")
            self._invalidate_cache_pattern(f"email_{user.email.lower()}")
            self._invalidate_cache_pattern("active_users")
            self._invalidate_cache_pattern(f"role_{user.role}")

            logger.info(f"Deactivated user ID {user_id}")
            return True
        except User.DoesNotExist:
            logger.warning(f"Failed to deactivate user ID {user_id}: Not found")
            return False

    def activate_user(self, user_id: int) -> bool:
        """
        Activate user account

        Args:
            user_id: User ID

        Returns:
            True if activated, False otherwise
        """
        try:
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{user_id}")
            if hasattr(user, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{user.uuid}")
            self._invalidate_cache_pattern(f"email_{user.email.lower()}")
            self._invalidate_cache_pattern("active_users")
            self._invalidate_cache_pattern(f"role_{user.role}")

            logger.info(f"Activated user ID {user_id}")
            return True
        except User.DoesNotExist:
            logger.warning(f"Failed to activate user ID {user_id}: Not found")
            return False

    def update_last_login(self, user_id: int) -> bool:
        """
        Update user's last login timestamp

        Args:
            user_id: User ID

        Returns:
            True if updated, False otherwise
        """
        try:
            user = User.objects.get(id=user_id)
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{user_id}")
            if hasattr(user, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{user.uuid}")

            logger.debug(f"Updated last login for user ID {user_id}")
            return True
        except User.DoesNotExist:
            logger.warning(f"Failed to update last login for user ID {user_id}: Not found")
            return False

    def get_users_created_between(self, start_date, end_date) -> List[User]:
        """
        Get users created within date range

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of users created in date range
        """
        cache_key = self.get_cache_key(f"created_{start_date}_{end_date}")

        cached_users = cache.get(cache_key)
        if cached_users:
            return cached_users

        users = list(User.objects.filter(
            date_joined__range=[start_date, end_date]
        ).order_by('-date_joined'))

        cache.set(cache_key, users, self.cache_timeout)
        return users

    def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get user statistics

        Returns:
            Dictionary with user statistics
        """
        cache_key = self.get_cache_key("statistics")

        cached_stats = cache.get(cache_key)
        if cached_stats:
            return cached_stats

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        admin_users = User.objects.filter(role='admin', is_active=True).count()
        sales_users = User.objects.filter(role='sales', is_active=True).count()
        manager_users = User.objects.filter(role='manager', is_active=True).count()
        support_users = User.objects.filter(role='support', is_active=True).count()

        # Users created in last 30 days
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        recent_users = User.objects.filter(
            date_joined__gte=thirty_days_ago
        ).count()

        statistics = {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': total_users - active_users,
            'users_by_role': {
                'admin': admin_users,
                'sales': sales_users,
                'manager': manager_users,
                'support': support_users,
            },
            'recent_users': recent_users,
            'last_updated': timezone.now(),
        }

        cache.set(cache_key, statistics, self.cache_timeout)
        return statistics

    def bulk_create_users(self, users_data: List[Dict[str, Any]]) -> List[User]:
        """
        Bulk create users (for admin operations)

        Args:
            users_data: List of user data dictionaries

        Returns:
            List of created users
        """
        users = []
        for user_data in users_data:
            password = user_data.pop('password', 'temp_password123')
            user = User.objects.create_user(password=password, **user_data)
            users.append(user)

        # Invalidate cache
        self._invalidate_cache_pattern("active_users")
        self._invalidate_cache_pattern("statistics")

        logger.info(f"Bulk created {len(users)} users")
        return users

    def clear_user_cache(self, user: User):
        """
        Clear all cache related to a specific user

        Args:
            user: User instance
        """
        cache_keys_to_clear = [
            f"id_{user.id}",
            f"email_{user.email.lower()}",
            "active_users",
            f"role_{user.role}",
            "statistics",
        ]

        if hasattr(user, 'uuid'):
            cache_keys_to_clear.append(f"uuid_{user.uuid}")

        for key_suffix in cache_keys_to_clear:
            cache_key = self.get_cache_key(key_suffix)
            cache.delete(cache_key)

        logger.debug(f"Cleared cache for user {user.email}")