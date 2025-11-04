"""
Deal Serializers - API Data Transformation Layer
Following SOLID principles and enterprise best practices
"""

from decimal import Decimal
from datetime import date, datetime
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _

from .models import Deal, DealStageHistory
from crm.apps.contacts.serializers import ContactSummarySerializer

User = get_user_model()


class BaseDealSerializer(serializers.ModelSerializer):
    """
    Base Deal Serializer with common validation logic
    Following Single Responsibility Principle
    """

    # Computed fields
    formatted_value = serializers.SerializerMethodField()
    pipeline_position = serializers.SerializerMethodField()
    is_won = serializers.BooleanField(read_only=True)
    is_lost = serializers.BooleanField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    days_in_pipeline = serializers.IntegerField(read_only=True)
    days_to_close = serializers.IntegerField(read_only=True)

    # Custom field validation
    value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        error_messages={
            'min_value': _('Deal value must be positive.'),
            'invalid': _('Enter a valid number.'),
            'max_digits': _('Ensure this value has at most 15 digits.'),
            'max_decimal_places': _('Ensure this value has at most 2 decimal places.')
        }
    )

    probability = serializers.IntegerField(
        min_value=0,
        max_value=100,
        error_messages={
            'min_value': _('Probability cannot be negative.'),
            'max_value': _('Probability cannot exceed 100%.')
        }
    )

    expected_close_date = serializers.DateField(
        error_messages={
            'invalid': _('Enter a valid date.'),
            'null': _('Expected close date is required.')
        }
    )

    # Relationship serializers
    contact_details = ContactSummarySerializer(source='contact', read_only=True)
    owner_details = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            'id', 'uuid', 'title', 'description', 'value', 'currency',
            'probability', 'stage', 'expected_close_date', 'contact',
            'contact_details', 'owner', 'owner_details', 'loss_reason',
            'closed_value', 'formatted_value', 'pipeline_position',
            'is_won', 'is_lost', 'is_open', 'days_in_pipeline',
            'days_to_close', 'created_at', 'updated_at', 'closed_date'
        ]
        read_only_fields = [
            'id', 'uuid', 'created_at', 'updated_at', 'closed_date',
            'closed_value', 'loss_reason'
        ]

    def get_formatted_value(self, obj):
        """Get formatted deal value with currency"""
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'CAD': 'C$',
            'AUD': 'A$',
        }
        symbol = currency_symbols.get(obj.currency, obj.currency)
        return f"{symbol}{obj.value:,.2f}"

    def get_pipeline_position(self, obj):
        """Get position in sales pipeline"""
        return obj.get_pipeline_position()

    def get_owner_details(self, obj):
        """Get simplified owner information"""
        return {
            'id': obj.owner.id,
            'name': obj.owner.get_full_name(),
            'email': obj.owner.email,
            'role': obj.owner.role
        }

    def validate_value(self, value):
        """Validate deal value is positive"""
        if value is not None and value <= 0:
            raise serializers.ValidationError(_('Deal value must be positive.'))
        return value

    def validate_probability(self, value):
        """Validate probability is within valid range"""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError(_('Probability must be between 0 and 100.'))
        return value

    def validate_expected_close_date(self, value):
        """Validate expected close date"""
        if value and value < date.today():
            stage = self.initial_data.get('stage', '')
            if stage not in ['closed_won', 'closed_lost']:
                raise serializers.ValidationError(
                    _('Expected close date cannot be in the past for open deals.')
                )
        return value

    def validate_stage(self, value):
        """Validate stage is a valid choice"""
        valid_stages = [choice[0] for choice in Deal.STAGE_CHOICES]
        if value not in valid_stages:
            raise serializers.ValidationError(
                _('Invalid stage. Must be one of: {}').format(', '.join(valid_stages))
            )
        return value

    def validate_currency(self, value):
        """Validate currency is a valid choice"""
        valid_currencies = [choice[0] for choice in Deal.CURRENCY_CHOICES]
        if value not in valid_currencies:
            raise serializers.ValidationError(
                _('Invalid currency. Must be one of: {}').format(', '.join(valid_currencies))
            )
        return value

    def validate(self, attrs):
        """
        Cross-field validation
        Following SOLID principles for comprehensive validation
        """
        stage = attrs.get('stage')
        probability = attrs.get('probability')

        # Auto-set probability based on stage if not provided
        if stage and probability is None:
            stage_probabilities = {
                'prospect': 10,
                'qualified': 25,
                'proposal': 50,
                'negotiation': 75,
                'closed_won': 100,
                'closed_lost': 0,
            }
            attrs['probability'] = stage_probabilities.get(stage, 0)

        # Validate stage-probability consistency
        if stage == 'closed_won' and probability != 100:
            attrs['probability'] = 100
        elif stage == 'closed_lost' and probability != 0:
            attrs['probability'] = 0

        return attrs

    def validate_title(self, value):
        """Validate and sanitize title"""
        if not value or not value.strip():
            raise serializers.ValidationError(_('Deal title is required.'))
        return value.strip()

    def validate_description(self, value):
        """Validate and sanitize description"""
        if value:
            return value.strip()
        return ''


class DealSerializer(BaseDealSerializer):
    """
    Standard Deal Serializer for general use
    Following Open/Closed Principle for extensibility
    """

    class Meta(BaseDealSerializer.Meta):
        pass


class DealCreateSerializer(BaseDealSerializer):
    """
    Deal Create Serializer with creation-specific validation
    Following Single Responsibility Principle
    """

    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True
    )

    class Meta(BaseDealSerializer.Meta):
        fields = [
            'title', 'description', 'value', 'currency', 'probability',
            'stage', 'expected_close_date', 'contact', 'owner'
        ]

    def create(self, validated_data):
        """
        Create deal with business logic
        Following KISS principle for clean, readable creation logic
        """
        # Set default values
        validated_data.setdefault('is_archived', False)

        # Auto-set probability based on stage if not provided
        stage = validated_data.get('stage')
        if stage and not validated_data.get('probability'):
            stage_probabilities = {
                'prospect': 10,
                'qualified': 25,
                'proposal': 50,
                'negotiation': 75,
                'closed_won': 100,
                'closed_lost': 0,
            }
            validated_data['probability'] = stage_probabilities.get(stage, 0)

        return super().create(validated_data)


class DealUpdateSerializer(BaseDealSerializer):
    """
    Deal Update Serializer with update-specific validation
    Following Single Responsibility Principle
    """

    class Meta(BaseDealSerializer.Meta):
        fields = [
            'title', 'description', 'value', 'currency', 'probability',
            'stage', 'expected_close_date', 'contact', 'loss_reason',
            'closed_value'
        ]

    def update(self, instance, validated_data):
        """
        Update deal with business logic and stage tracking
        Following SOLID principles for clean business logic
        """
        old_stage = instance.stage
        new_stage = validated_data.get('stage', old_stage)

        # Track stage change
        if old_stage != new_stage:
            DealStageHistory.objects.create(
                deal=instance,
                old_stage=old_stage,
                new_stage=new_stage,
                changed_by=self.context['request'].user
            )

        # Auto-set probability based on stage change
        if 'stage' in validated_data and 'probability' not in validated_data:
            stage_probabilities = {
                'prospect': 10,
                'qualified': 25,
                'proposal': 50,
                'negotiation': 75,
                'closed_won': 100,
                'closed_lost': 0,
            }
            validated_data['probability'] = stage_probabilities.get(new_stage, 0)

        # Set closed date for closed deals
        if new_stage in ['closed_won', 'closed_lost'] and not instance.closed_date:
            validated_data['closed_date'] = datetime.now()

            # Set closed value for won deals
            if new_stage == 'closed_won' and not validated_data.get('closed_value'):
                validated_data['closed_value'] = instance.value

        return super().update(instance, validated_data)


class DealDetailSerializer(BaseDealSerializer):
    """
    Detailed Deal Serializer with comprehensive information
    Following Single Responsibility Principle for detailed views
    """

    stage_history = serializers.SerializerMethodField()

    class Meta(BaseDealSerializer.Meta):
        fields = BaseDealSerializer.Meta.fields + ['stage_history']

    def get_stage_history(self, obj):
        """Get stage change history"""
        history = obj.stage_history.order_by('-changed_at')
        return DealStageHistorySerializer(history, many=True).data


class DealSummarySerializer(serializers.ModelSerializer):
    """
    Summary Deal Serializer for list views and dropdowns
    Following KISS principle for lightweight data transfer
    """

    formatted_value = serializers.SerializerMethodField()
    pipeline_position = serializers.SerializerMethodField()
    contact = ContactSummarySerializer(read_only=True)

    class Meta:
        model = Deal
        fields = [
            'id', 'uuid', 'title', 'value', 'formatted_value',
            'currency', 'probability', 'stage', 'pipeline_position',
            'expected_close_date', 'contact'
        ]

    def get_formatted_value(self, obj):
        """Get formatted deal value with currency"""
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'CAD': 'C$',
            'AUD': 'A$',
        }
        symbol = currency_symbols.get(obj.currency, obj.currency)
        return f"{symbol}{obj.value:,.2f}"

    def get_pipeline_position(self, obj):
        """Get position in sales pipeline"""
        return obj.get_pipeline_position()


class DealStageHistorySerializer(serializers.ModelSerializer):
    """
    Deal Stage History Serializer for tracking deal progression
    Following SOLID principles for clean data transformation
    """

    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    stage_change_display = serializers.SerializerMethodField()

    class Meta:
        model = DealStageHistory
        fields = [
            'id', 'deal', 'old_stage', 'new_stage', 'stage_change_display',
            'changed_by', 'changed_by_name', 'changed_at'
        ]
        read_only_fields = ['id', 'changed_by', 'changed_at']

    def get_stage_change_display(self, obj):
        """Get human-readable stage change description"""
        stage_names = dict(Deal.STAGE_CHOICES)
        old_name = stage_names.get(obj.old_stage, obj.old_stage)
        new_name = stage_names.get(obj.new_stage, obj.new_stage)
        return f"{old_name} → {new_name}"

    def validate(self, attrs):
        """Validate stage transition"""
        old_stage = attrs.get('old_stage')
        new_stage = attrs.get('new_stage')

        if old_stage == new_stage:
            raise serializers.ValidationError(_('Old stage and new stage cannot be the same.'))

        return attrs


class DealBulkOperationSerializer(serializers.Serializer):
    """
    Bulk operation serializer for deal management
    Following KISS principle for simple bulk operations
    """

    deal_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        error_messages={
            'min_length': _('At least one deal ID must be provided.')
        }
    )

    operation = serializers.ChoiceField(
        choices=[
            ('archive', _('Archive')),
            ('unarchive', _('Unarchive')),
            ('stage_change', _('Change Stage')),
            ('delete', _('Delete')),
        ]
    )

    new_stage = serializers.ChoiceField(
        choices=[(choice[0], choice[1]) for choice in Deal.STAGE_CHOICES],
        required=False,
        allow_null=True
    )

    def validate_deal_ids(self, value):
        """Validate deal IDs exist"""
        existing_ids = Deal.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)

        if missing_ids:
            raise serializers.ValidationError(
                _('The following deal IDs do not exist: {}').format(list(missing_ids))
            )

        return value

    def validate(self, attrs):
        """Cross-field validation"""
        operation = attrs.get('operation')
        new_stage = attrs.get('new_stage')

        if operation == 'stage_change' and not new_stage:
            raise serializers.ValidationError(
                _('New stage is required for stage change operation.')
            )

        return attrs


class DealPipelineStatisticsSerializer(serializers.Serializer):
    """
    Deal Pipeline Statistics Serializer
    Following Single Responsibility Principle for analytics
    """

    total_deals = serializers.IntegerField(read_only=True)
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    average_deal_size = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    average_sales_cycle = serializers.IntegerField(read_only=True)
    deals_by_stage = serializers.DictField(read_only=True)
    deals_by_month = serializers.DictField(read_only=True)
    top_performing_stages = serializers.ListField(read_only=True)


class DealForecastSerializer(serializers.Serializer):
    """
    Deal Forecast Serializer for sales forecasting
    Following Single Responsibility Principle for predictive analytics
    """

    period = serializers.ChoiceField(
        choices=[
            ('current_month', _('Current Month')),
            ('current_quarter', _('Current Quarter')),
            ('current_year', _('Current Year')),
            ('next_month', _('Next Month')),
            ('next_quarter', _('Next Quarter')),
            ('next_year', _('Next Year')),
        ]
    )

    forecast_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    confidence_level = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    deals_count = serializers.IntegerField(read_only=True)
    weighted_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)


# Simple TDD Serializers - Following KISS principle
class SimpleDealSerializer(serializers.ModelSerializer):
    """
    Simple Deal Serializer for TDD API development
    Following KISS principle - minimal functionality
    """
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault()  # KISS: Use current user as default
    )
    contact_name = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            'id', 'title', 'description', 'value', 'currency', 'stage',
            'probability', 'expected_close_date', 'contact', 'contact_name',
            'owner', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']  # KISS: Allow owner to be set during creation

    def get_contact_name(self, obj):
        """Get contact name for display"""
        return str(obj.contact)

    def create(self, validated_data):
        """KISS principle: Use provided owner or fallback to request user"""
        request = self.context.get('request')
        if request and request.user and 'owner' not in validated_data:
            validated_data['owner'] = request.user
        return super().create(validated_data)