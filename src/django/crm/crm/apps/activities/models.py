"""
Activity Models - Task and Event Management
Following SOLID principles and enterprise best practices
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
import uuid

from crm.apps.contacts.models import Contact
from crm.apps.deals.models import Deal

User = get_user_model()


class ActivityManager(models.Manager):
    """Custom Activity Manager implementing Repository Pattern"""

    def get_queryset(self):
        """Default queryset excluding cancelled activities"""
        return super().get_queryset().filter(is_cancelled=False)

    def all_objects(self):
        """Include cancelled activities"""
        return super().get_queryset()

    def by_owner(self, user):
        """Get activities by owner"""
        return self.filter(owner=user)

    def by_contact(self, contact):
        """Get activities for specific contact"""
        return self.filter(contact=contact)

    def by_deal(self, deal):
        """Get activities for specific deal"""
        return self.filter(deal=deal)

    def by_type(self, activity_type):
        """Get activities by type"""
        return self.filter(type=activity_type)

    def upcoming(self):
        """Get upcoming activities"""
        return self.filter(
            scheduled_at__gte=timezone.now(),
            is_completed=False
        ).order_by('scheduled_at')

    def overdue(self):
        """Get overdue activities"""
        return self.filter(
            scheduled_at__lt=timezone.now(),
            is_completed=False
        ).order_by('scheduled_at')

    def completed_today(self):
        """Get activities completed today"""
        today = timezone.now().date()
        return self.filter(
            completed_at__date=today,
            is_completed=True
        )

    def due_soon(self, hours=24):
        """Get activities due within specified hours"""
        cutoff_time = timezone.now() + timedelta(hours=hours)
        return self.filter(
            scheduled_at__lte=cutoff_time,
            scheduled_at__gte=timezone.now(),
            is_completed=False
        ).order_by('scheduled_at')

    def for_date_range(self, start_date, end_date):
        """Get activities within date range"""
        return self.filter(
            scheduled_at__range=[start_date, end_date]
        )


class Activity(models.Model):
    """Activity model for managing tasks and events"""

    ACTIVITY_TYPES = [
        ('call', _('Phone Call')),
        ('email', _('Email')),
        ('meeting', _('Meeting')),
        ('demo', _('Demo')),
        ('followup', _('Follow-up')),
        ('task', _('Task')),
        ('note', _('Note')),
        ('lunch', _('Lunch')),
        ('webinar', _('Webinar')),
    ]

    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]

    # Basic Information
    type = models.CharField(
        _('type'),
        max_length=20,
        choices=ACTIVITY_TYPES,
        help_text=_('Type of activity')
    )

    title = models.CharField(
        _('title'),
        max_length=200,
        help_text=_('Activity title or subject')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        null=True,
        help_text=_('Detailed description of the activity')
    )

    # Scheduling
    scheduled_at = models.DateTimeField(
        _('scheduled at'),
        help_text=_('When the activity is scheduled to occur')
    )

    duration_minutes = models.PositiveIntegerField(
        _('duration (minutes)'),
        blank=True,
        null=True,
        help_text=_('Expected duration in minutes')
    )

    # Priority and Status
    priority = models.CharField(
        _('priority'),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text=_('Activity priority level')
    )

    is_completed = models.BooleanField(
        _('completed'),
        default=False,
        help_text=_('Whether the activity has been completed')
    )

    is_cancelled = models.BooleanField(
        _('cancelled'),
        default=False,
        help_text=_('Whether the activity has been cancelled')
    )

    # Completion tracking
    completed_at = models.DateTimeField(
        _('completed at'),
        blank=True,
        null=True,
        help_text=_('When the activity was completed')
    )

    completion_notes = models.TextField(
        _('completion notes'),
        blank=True,
        null=True,
        help_text=_('Notes added when completing the activity')
    )

    # Relationships
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='activities',
        blank=True,
        null=True,
        verbose_name=_('contact'),
        help_text=_('Related contact for this activity')
    )

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='activities',
        blank=True,
        null=True,
        verbose_name=_('deal'),
        help_text=_('Related deal for this activity')
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name=_('owner'),
        help_text=_('User responsible for this activity')
    )

    # Reminder System
    reminder_minutes = models.PositiveIntegerField(
        _('reminder (minutes)'),
        blank=True,
        null=True,
        help_text=_('Minutes before scheduled time to send reminder')
    )

    reminder_sent = models.BooleanField(
        _('reminder sent'),
        default=False,
        help_text=_('Whether reminder has been sent')
    )

    reminder_at = models.DateTimeField(
        _('reminder at'),
        blank=True,
        null=True,
        help_text=_('When reminder should be sent')
    )

    # Location (for meetings)
    location = models.CharField(
        _('location'),
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Location for in-person meetings')
    )

    # Video conference details
    video_conference_url = models.URLField(
        _('video conference URL'),
        blank=True,
        null=True,
        help_text=_('URL for video conference meetings')
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

    objects = ActivityManager()

    class Meta:
        db_table = 'activities'
        verbose_name = _('Activity')
        verbose_name_plural = _('Activities')
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['type']),
            models.Index(fields=['scheduled_at']),
            models.Index(fields=['owner']),
            models.Index(fields=['contact']),
            models.Index(fields=['deal']),
            models.Index(fields=['is_completed']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        """String representation of activity"""
        return f"{self.get_type_display()} - {self.title}"

    def clean(self):
        """Custom validation for activity model"""
        super().clean()

        # Validate scheduled_at is not in the past for new activities (except notes)
        if (self.scheduled_at and
            self.scheduled_at < timezone.now() - timedelta(minutes=5) and
            self.type != 'note' and
            not self.is_completed and
            not self._state.adding):
            raise ValidationError(_('Scheduled time cannot be in the past for new activities.'))

        # Validate at least one of contact or deal is specified
        if not self.contact and not self.deal:
            raise ValidationError(_('Activity must be associated with either a contact or a deal.'))

        # Validate duration is positive if specified
        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValidationError(_('Duration must be positive if specified.'))

    def save(self, *args, **kwargs):
        """Override save to ensure data integrity"""
        self.full_clean()

        # Auto-calculate reminder_at based on reminder_minutes
        if self.reminder_minutes and self.scheduled_at:
            self.reminder_at = self.scheduled_at - timedelta(minutes=self.reminder_minutes)
        else:
            self.reminder_at = None

        # Auto-set completed_at when marking as completed
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()

        # Reset completion tracking when un-completing
        if not self.is_completed:
            self.completed_at = None
            self.completion_notes = None

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if activity is overdue"""
        return (
            not self.is_completed and
            not self.is_cancelled and
            self.scheduled_at < timezone.now()
        )

    @property
    def is_due_soon(self, hours=24):
        """Check if activity is due soon"""
        if self.is_completed or self.is_cancelled:
            return False

        cutoff_time = timezone.now() + timedelta(hours=hours)
        return timezone.now() <= self.scheduled_at <= cutoff_time

    @property
    def status(self):
        """Get current status of activity"""
        if self.is_cancelled:
            return 'cancelled'
        elif self.is_completed:
            return 'completed'
        elif self.is_overdue:
            return 'overdue'
        elif self.is_due_soon():
            return 'due_soon'
        else:
            return 'scheduled'

    def mark_completed(self, notes=None):
        """Mark activity as completed"""
        self.is_completed = True
        self.completed_at = timezone.now()
        if notes:
            self.completion_notes = notes
        self.save()

    def mark_cancelled(self):
        """Mark activity as cancelled"""
        self.is_cancelled = True
        self.save()

    def snooze(self, minutes):
        """Snooze activity by specified minutes"""
        if not self.is_completed and not self.is_cancelled:
            self.scheduled_at = self.scheduled_at + timedelta(minutes=minutes)
            self.save()

    def reschedule(self, new_time):
        """Reschedule activity to new time"""
        if not self.is_completed and not self.is_cancelled:
            self.scheduled_at = new_time
            self.save()

    def send_reminder(self):
        """Mark reminder as sent"""
        self.reminder_sent = True
        self.save()

    def get_priority_display_with_color(self):
        """Get priority display with bootstrap color class"""
        priority_colors = {
            'low': 'success',
            'medium': 'info',
            'high': 'warning',
            'urgent': 'danger',
        }
        color = priority_colors.get(self.priority, 'secondary')
        return {
            'label': self.get_priority_display(),
            'color': color
        }

    def get_duration_display(self):
        """Get formatted duration display"""
        if self.duration_minutes:
            if self.duration_minutes < 60:
                return f"{self.duration_minutes} min"
            else:
                hours = self.duration_minutes // 60
                minutes = self.duration_minutes % 60
                if minutes == 0:
                    return f"{hours} hr"
                else:
                    return f"{hours} hr {minutes} min"
        return None


class ActivityComment(models.Model):
    """Comments and updates on activities"""

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('activity')
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_comments',
        verbose_name=_('author')
    )

    comment = models.TextField(
        _('comment'),
        help_text=_('Comment or update about the activity')
    )

    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )

    class Meta:
        db_table = 'activity_comments'
        verbose_name = _('Activity Comment')
        verbose_name_plural = _('Activity Comments')
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author.get_full_name()} on {self.activity.title}"