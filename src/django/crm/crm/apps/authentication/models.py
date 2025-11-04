"""
Authentication Models - User Management and RBAC
Following SOLID principles and enterprise best practices
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import uuid


class UserManager(BaseUserManager):
    """Custom User Manager following Repository Pattern"""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        if not email:
            raise ValueError(_('Users must have an email address'))

        # Set default values for required fields if not provided
        if not extra_fields.get('first_name'):
            extra_fields['first_name'] = 'Test'
        if not extra_fields.get('last_name'):
            extra_fields['last_name'] = 'User'

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)

    def get_by_email(self, email):
        """Get user by email (case-insensitive)"""
        return self.get(email__iexact=email)

    def active_users(self):
        """Get all active users"""
        return self.filter(is_active=True)

    def users_by_role(self, role):
        """Get users by specific role"""
        return self.filter(role=role)


class User(AbstractUser):
    """Custom User Model with email-based authentication and role-based access"""

    ROLE_CHOICES = [
        ('admin', _('Administrator')),
        ('sales', _('Sales Representative')),
        ('manager', _('Sales Manager')),
        ('support', _('Support Agent')),
    ]

    # Primary authentication field
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _('A user with that email already exists.'),
        }
    )

    # Remove username field
    username = None

    # User Information
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)

    # Role-based access control
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=ROLE_CHOICES,
        default='sales',
        help_text=_('User role determines permissions and access level')
    )

    # UUID for external integrations
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_('Unique identifier for external systems')
    )

    # Profile photo
    profile_photo = models.ImageField(
        _('profile photo'),
        upload_to='profile_photos/',
        blank=True,
        null=True
    )

    # Contact information
    phone = models.CharField(
        _('phone number'),
        max_length=20,
        blank=True,
        null=True
    )

    # Department and organization info
    department = models.CharField(
        _('department'),
        max_length=100,
        blank=True,
        null=True
    )

    # Timestamps
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    last_login = models.DateTimeField(_('last login'), blank=True, null=True)

    # Email verification
    email_verified = models.BooleanField(
        _('email verified'),
        default=False,
        help_text=_('Whether the user has verified their email address')
    )

    # Two-factor authentication
    two_factor_enabled = models.BooleanField(
        _('two-factor enabled'),
        default=False,
        help_text=_('Whether two-factor authentication is enabled')
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'auth_users'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['date_joined']),
        ]

    def __str__(self):
        """String representation of user"""
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self):
        """Custom validation for user model"""
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def save(self, *args, **kwargs):
        """Override save to ensure proper data integrity"""
        self.full_clean()
        super().save(*args, **kwargs)

    def has_role(self, role):
        """Check if user has specific role"""
        return self.role == role

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'

    def is_sales_user(self):
        """Check if user is sales representative"""
        return self.role == 'sales'

    def is_manager(self):
        """Check if user is manager"""
        return self.role == 'manager'

    def get_role_display(self):
        """Get human-readable role name"""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)


class UserProfile(models.Model):
    """Extended user profile information following SOLID principles"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('user')
    )

    # Professional information
    bio = models.TextField(
        _('biography'),
        blank=True,
        help_text=_('Professional background and expertise')
    )

    linkedin_url = models.URLField(
        _('LinkedIn profile'),
        blank=True,
        null=True
    )

    # Timezone and locale preferences
    timezone = models.CharField(
        _('timezone'),
        max_length=50,
        default='UTC',
        help_text=_('User timezone for scheduling')
    )

    language = models.CharField(
        _('language'),
        max_length=10,
        default='en',
        help_text=_('Preferred language for interface')
    )

    # Notification preferences
    email_notifications = models.BooleanField(
        _('email notifications'),
        default=True,
        help_text=_('Receive email notifications')
    )

    push_notifications = models.BooleanField(
        _('push notifications'),
        default=True,
        help_text=_('Receive push notifications')
    )

    # Dashboard preferences
    dashboard_layout = models.JSONField(
        _('dashboard layout'),
        default=dict,
        blank=True,
        help_text=_('User-specific dashboard layout configuration')
    )

    # Last activity tracking
    last_activity = models.DateTimeField(
        _('last activity'),
        auto_now=True,
        help_text=_('Last time user was active')
    )

    # Session information
    current_session_key = models.CharField(
        _('current session key'),
        max_length=40,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'user_profiles'
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')

    def __str__(self):
        return f"{self.user.full_name}'s Profile"

    def get_active_sessions(self):
        """Get all active sessions for the user"""
        # Implementation would use Django's session framework
        pass


# Signal to create UserProfile when User is created
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile automatically when User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    instance.profile.save()