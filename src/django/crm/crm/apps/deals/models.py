"""
Deal Models - Sales Pipeline Management
Following SOLID principles and enterprise best practices
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import uuid

from crm.apps.contacts.models import Contact

User = get_user_model()


class DealManager(models.Manager):
    """Custom Deal Manager implementing Repository Pattern"""

    def get_queryset(self):
        """Default queryset excluding archived deals"""
        return super().get_queryset().filter(is_archived=False)

    def all_objects(self):
        """Include archived deals"""
        return super().get_queryset()

    def by_owner(self, user):
        """Get deals by owner"""
        return self.filter(owner=user)

    def by_stage(self, stage):
        """Get deals by specific stage"""
        return self.filter(stage=stage)

    def by_contact(self, contact):
        """Get deals for specific contact"""
        return self.filter(contact=contact)

    def open_deals(self):
        """Get all open deals (not won or lost)"""
        return self.exclude(stage__in=['closed_won', 'closed_lost'])

    def won_deals(self):
        """Get all won deals"""
        return self.filter(stage='closed_won')

    def lost_deals(self):
        """Get all lost deals"""
        return self.filter(stage='closed_lost')

    def created_between(self, start_date, end_date):
        """Get deals created within date range"""
        return self.filter(created_at__range=[start_date, end_date])

    def closing_soon(self, days=30):
        """Get deals expected to close within specified days"""
        cutoff_date = timezone.now() + timezone.timedelta(days=days)
        return self.filter(
            expected_close_date__lte=cutoff_date,
            stage__in=['qualified', 'proposal', 'negotiation']
        )


class Deal(models.Model):
    """Deal model for managing sales pipeline opportunities"""

    # Deal Stages - Following sales methodology
    STAGE_CHOICES = [
        ('prospect', _('Prospect')),
        ('qualified', _('Qualified')),
        ('proposal', _('Proposal')),
        ('negotiation', _('Negotiation')),
        ('closed_won', _('Closed Won')),
        ('closed_lost', _('Closed Lost')),
    ]

    CURRENCY_CHOICES = [
        ('USD', _('US Dollar')),
        ('EUR', _('Euro')),
        ('GBP', _('British Pound')),
        ('CAD', _('Canadian Dollar')),
        ('AUD', _('Australian Dollar')),
    ]

    # Basic Information
    title = models.CharField(
        _('title'),
        max_length=200,
        help_text=_('Deal name or description')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        null=True,
        help_text=_('Detailed description of the deal')
    )

    # Financial Information
    value = models.DecimalField(
        _('value'),
        max_digits=15,
        decimal_places=2,
        help_text=_('Expected value of the deal')
    )

    currency = models.CharField(
        _('currency'),
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        help_text=_('Currency for the deal value')
    )

    # Probability and Stages
    probability = models.PositiveIntegerField(
        _('probability'),
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        help_text=_('Probability of closing the deal (0-100%)')
    )

    stage = models.CharField(
        _('stage'),
        max_length=20,
        choices=STAGE_CHOICES,
        default='prospect',
        help_text=_('Current stage in the sales pipeline')
    )

    expected_close_date = models.DateField(
        _('expected close date'),
        help_text=_('Expected date when the deal will close')
    )

    # Relationship to Contact
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='deals',
        verbose_name=_('contact'),
        help_text=_('Primary contact for this deal')
    )

    # Ownership
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='deals',
        verbose_name=_('owner'),
        help_text=_('User responsible for this deal')
    )

    # Loss Reason (for closed lost deals)
    loss_reason = models.TextField(
        _('loss reason'),
        blank=True,
        null=True,
        help_text=_('Reason why the deal was lost')
    )

    # Win Details (for closed won deals)
    closed_value = models.DecimalField(
        _('closed value'),
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_('Actual value when deal was won')
    )

    # System fields
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_('Unique identifier for external systems')
    )

    is_archived = models.BooleanField(
        _('archived'),
        default=False,
        help_text=_('Whether this deal is archived')
    )

    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True
    )

    closed_date = models.DateTimeField(
        _('closed date'),
        blank=True,
        null=True,
        help_text=_('Date when deal was won or lost')
    )

    objects = DealManager()

    class Meta:
        db_table = 'deals'
        verbose_name = _('Deal')
        verbose_name_plural = _('Deals')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['stage']),
            models.Index(fields=['probability']),
            models.Index(fields=['expected_close_date']),
            models.Index(fields=['contact']),
            models.Index(fields=['owner']),
            models.Index(fields=['created_at']),
            models.Index(fields=['value']),
        ]

    def __str__(self):
        """String representation of deal"""
        return f"{self.title} - {self.get_formatted_value()}"

    def clean(self):
        """Custom validation for deal model"""
        super().clean()

        # Validate deal value is positive
        if self.value is not None and self.value <= 0:
            raise ValidationError(_('Deal value must be positive.'))

        # Validate probability range
        if self.probability < 0 or self.probability > 100:
            raise ValidationError(_('Probability must be between 0 and 100.'))

        # Validate expected close date is not in the past for new deals
        if (self.expected_close_date and
            self.expected_close_date < timezone.now().date() and
            self.stage not in ['closed_won', 'closed_lost']):
            raise ValidationError(_('Expected close date cannot be in the past for open deals.'))

    def save(self, *args, **kwargs):
        """Override save to ensure data integrity and track changes"""
        self.full_clean()

        # Auto-set probability based on stage if not manually set
        if not self._state.adding:  # Only for existing records
            old_stage = Deal.objects.get(pk=self.pk).stage
            if old_stage != self.stage:
                self._update_probability_for_stage()
                self._track_stage_change(old_stage)

        # Set closed date when deal is won or lost
        if self.stage in ['closed_won', 'closed_lost'] and not self.closed_date:
            self.closed_date = timezone.now()

        super().save(*args, **kwargs)

    def _update_probability_for_stage(self):
        """Update probability based on stage changes"""
        stage_probabilities = {
            'prospect': 10,
            'qualified': 25,
            'proposal': 50,
            'negotiation': 75,
            'closed_won': 100,
            'closed_lost': 0,
        }
        if self.stage in stage_probabilities:
            self.probability = stage_probabilities[self.stage]

    def _track_stage_change(self, old_stage):
        """Track stage changes for pipeline analytics"""
        DealStageHistory.objects.create(
            deal=self,
            old_stage=old_stage,
            new_stage=self.stage,
            changed_by=getattr(self, '_changed_by_user', None)
        )

    @property
    def is_won(self):
        """Check if deal is won"""
        return self.stage == 'closed_won'

    @property
    def is_lost(self):
        """Check if deal is lost"""
        return self.stage == 'closed_lost'

    @property
    def is_open(self):
        """Check if deal is still open"""
        return self.stage not in ['closed_won', 'closed_lost']

    @property
    def days_in_pipeline(self):
        """Calculate how long deal has been in pipeline"""
        return (timezone.now() - self.created_at).days

    @property
    def days_to_close(self):
        """Calculate days until expected close"""
        if self.expected_close_date:
            return (self.expected_close_date - timezone.now().date()).days
        return None

    def get_formatted_value(self, include_currency=True):
        """Get formatted deal value"""
        if include_currency:
            return f"{self.currency} {self.value:,.2f}"
        return f"{self.value:,.2f}"

    def get_pipeline_position(self):
        """Get position in sales pipeline"""
        stage_order = ['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost']
        try:
            return stage_order.index(self.stage) + 1
        except ValueError:
            return 0

    def can_transition_to(self, new_stage):
        """Check if deal can transition to new stage"""
        valid_transitions = {
            'prospect': ['qualified', 'closed_lost'],
            'qualified': ['proposal', 'prospect', 'closed_lost'],
            'proposal': ['negotiation', 'qualified', 'closed_lost'],
            'negotiation': ['closed_won', 'proposal', 'closed_lost'],
            'closed_won': [],  # Final state
            'closed_lost': [],  # Final state
        }
        return new_stage in valid_transitions.get(self.stage, [])

    def close_as_won(self, final_value=None):
        """Close deal as won"""
        self.stage = 'closed_won'
        self.probability = 100
        if final_value:
            self.closed_value = final_value
        else:
            self.closed_value = self.value
        self.closed_date = timezone.now()
        self.save()

    def close_as_lost(self, reason):
        """Close deal as lost"""
        self.stage = 'closed_lost'
        self.probability = 0
        self.loss_reason = reason
        self.closed_date = timezone.now()
        self.save()


class DealStageHistory(models.Model):
    """Track deal stage changes for analytics"""

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='stage_history',
        verbose_name=_('deal')
    )

    old_stage = models.CharField(
        _('old stage'),
        max_length=20
    )

    new_stage = models.CharField(
        _('new stage'),
        max_length=20
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stage_changes',
        verbose_name=_('changed by')
    )

    changed_at = models.DateTimeField(
        _('changed at'),
        auto_now_add=True
    )

    class Meta:
        db_table = 'deal_stage_history'
        verbose_name = _('Deal Stage History')
        verbose_name_plural = _('Deal Stage Histories')
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['deal']),
            models.Index(fields=['changed_at']),
        ]

    def __str__(self):
        return f"{self.deal.title}: {self.old_stage} → {self.new_stage}"


