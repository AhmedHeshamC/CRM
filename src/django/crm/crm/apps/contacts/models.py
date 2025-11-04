"""
Contact Models - Customer Information Management
Following SOLID principles and enterprise best practices
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, validate_email
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import re

User = get_user_model()


class ContactManager(models.Manager):
    """Custom Contact Manager implementing Repository Pattern"""

    def get_queryset(self):
        """Default queryset excluding soft-deleted contacts"""
        return super().get_queryset().filter(is_deleted=False)

    def all_objects(self):
        """Include soft-deleted contacts"""
        return super().get_queryset()

    def active(self):
        """Get only active contacts"""
        return self.filter(is_active=True)

    def by_owner(self, user):
        """Get contacts by owner"""
        return self.filter(owner=user)

    def by_company(self, company):
        """Get contacts by company"""
        return self.filter(company__iexact=company)

    def tagged_with(self, tag):
        """Get contacts with specific tag"""
        return self.filter(tags__contains=[tag])

    def created_between(self, start_date, end_date):
        """Get contacts created within date range"""
        return self.filter(created_at__range=[start_date, end_date])

    def search(self, query):
        """Search contacts by name, email, company"""
        return self.filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(email__icontains=query) |
            models.Q(company__icontains=query)
        )


class Contact(models.Model):
    """Contact model with comprehensive customer information"""

    # Contact Information
    first_name = models.CharField(
        _('first name'),
        max_length=100,
        help_text=_('Contact\'s first name')
    )

    last_name = models.CharField(
        _('last name'),
        max_length=100,
        help_text=_('Contact\'s last name')
    )

    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _('A contact with this email already exists.'),
        },
        help_text=_('Primary email address')
    )

    phone = models.CharField(
        _('phone number'),
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\-?\s?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{4})$',
                message=_('Enter a valid phone number.'),
            )
        ],
        help_text=_('Phone number with country code')
    )

    # Professional Information
    company = models.CharField(
        _('company'),
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Company or organization name')
    )

    title = models.CharField(
        _('title'),
        max_length=100,
        blank=True,
        null=True,
        help_text=_('Job title or position')
    )

    website = models.URLField(
        _('website'),
        blank=True,
        null=True,
        help_text=_('Company or personal website')
    )

    # Address Information
    address = models.TextField(
        _('address'),
        blank=True,
        null=True,
        help_text=_('Street address')
    )

    city = models.CharField(
        _('city'),
        max_length=100,
        blank=True,
        null=True
    )

    state = models.CharField(
        _('state/province'),
        max_length=100,
        blank=True,
        null=True
    )

    country = models.CharField(
        _('country'),
        max_length=100,
        blank=True,
        null=True
    )

    postal_code = models.CharField(
        _('postal code'),
        max_length=20,
        blank=True,
        null=True
    )

    # Social Media
    linkedin_url = models.URLField(
        _('LinkedIn profile'),
        blank=True,
        null=True
    )

    twitter_url = models.URLField(
        _('Twitter profile'),
        blank=True,
        null=True
    )

    # Contact Classification
    tags = models.JSONField(
        _('tags'),
        default=list,
        blank=True,
        help_text=_('Tags for categorizing contacts')
    )

    lead_source = models.CharField(
        _('lead source'),
        max_length=100,
        blank=True,
        null=True,
        help_text=_('How this contact was acquired')
    )

    # Status and Ownership
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Whether this contact is actively engaged')
    )

    is_deleted = models.BooleanField(
        _('deleted'),
        default=False,
        help_text=_('Soft delete flag')
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contacts',
        verbose_name=_('owner'),
        help_text=_('User responsible for this contact')
    )

    # System fields
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_('Unique identifier for external systems')
    )

    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True
    )

    deleted_at = models.DateTimeField(
        _('deleted at'),
        blank=True,
        null=True
    )

    objects = ContactManager()

    class Meta:
        db_table = 'contacts'
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')
        ordering = ['last_name', 'first_name']
        unique_together = [['email', 'owner']]
        indexes = [
            models.Index(fields=['first_name']),
            models.Index(fields=['last_name']),
            models.Index(fields=['email']),
            models.Index(fields=['company']),
            models.Index(fields=['owner']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active']),
            models.Index(fields=['tags']),
        ]

    def __str__(self):
        """String representation of contact"""
        if self.company:
            return f"{self.first_name} {self.last_name} - {self.company}"
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        """Return contact's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self):
        """Custom validation for contact model"""
        super().clean()

        # Validate email format
        if self.email:
            validate_email(self.email)

        # Validate phone format if provided
        if self.phone:
            phone_validator = RegexValidator(
                regex=r'^\+?1?\-?\s?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{4})$',
                message=_('Enter a valid phone number.'),
            )
            phone_validator(self.phone)

    def save(self, *args, **kwargs):
        """Override save to ensure data integrity"""
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete implementation"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore soft-deleted contact"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def add_tag(self, tag):
        """Add a tag to the contact"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.save()

    def remove_tag(self, tag):
        """Remove a tag from the contact"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.save()

    def has_tag(self, tag):
        """Check if contact has specific tag"""
        return tag in self.tags

    def get_deals_count(self):
        """Get number of deals associated with this contact"""
        return self.deals.count()

    def get_total_deal_value(self):
        """Get total value of all deals for this contact"""
        return self.deals.aggregate(
            total=models.Sum('value')
        )['total'] or 0

    def get_latest_activity(self):
        """Get the most recent activity for this contact"""
        return self.activities.order_by('-created_at').first()


class ContactInteraction(models.Model):
    """Track all interactions with contacts"""

    INTERACTION_TYPES = [
        ('call', _('Phone Call')),
        ('email', _('Email')),
        ('meeting', _('Meeting')),
        ('note', _('Note')),
        ('task', _('Task')),
        ('demo', _('Demo')),
    ]

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='interactions',
        verbose_name=_('contact')
    )

    interaction_type = models.CharField(
        _('interaction type'),
        max_length=20,
        choices=INTERACTION_TYPES
    )

    title = models.CharField(
        _('title'),
        max_length=200
    )

    description = models.TextField(
        _('description'),
        blank=True,
        null=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contact_interactions',
        verbose_name=_('created by')
    )

    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )

    class Meta:
        db_table = 'contact_interactions'
        verbose_name = _('Contact Interaction')
        verbose_name_plural = _('Contact Interactions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.interaction_type}: {self.title} - {self.contact.full_name}"