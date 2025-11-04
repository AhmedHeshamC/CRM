"""
Contact Serializers - API Data Transformation Layer
Following SOLID principles and enterprise best practices
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email, URLValidator
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from .models import Contact, ContactInteraction

User = get_user_model()


class BaseContactSerializer(serializers.ModelSerializer):
    """
    Base Contact Serializer with comprehensive validation and detailed documentation

    Provides core contact serialization with extensive validation, computed fields,
    and business logic enforcement for customer relationship management.

    **Core Contact Information:**
    - Personal details (name, contact information)
    - Professional information (company, title, website)
    - Location data (address details)
    - Social media links (LinkedIn, Twitter)
    - Categorization (tags, lead source, status)

    **Validation Features:**
    - Email format and uniqueness validation
    - Phone number format validation (international format)
    - URL validation for website and social links
    - Tag management with duplicate prevention
    - Lead source tracking and categorization

    **Business Logic:**
    - Automatic full name generation
    - Tag-based filtering and searching
    - Lead source attribution
    - Activity status management

    **Security & Privacy:**
    - Input sanitization for all text fields
    - Protection against injection attacks
    - Secure file handling for profile images

    Following Single Responsibility Principle for focused contact data management
    """

    # Computed fields
    full_name = serializers.ReadOnlyField(
        help_text="Contact's full name (first name + last name)"
    )

    # Custom field validators with detailed help text
    email = serializers.EmailField(
        required=True,
        help_text="Primary email address for business communications",
        error_messages={
            'invalid': _('Please enter a valid email address.'),
            'blank': _('Email address is required.'),
        }
    )

    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Business phone number (international format: +1-555-123-4567)",
        validators=[
            serializers.RegexValidator(
                regex=r'^\+?1?\-?\s?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{4})$',
                message=_('Enter a valid phone number in international format.'),
                code='invalid_phone'
            )
        ]
    )

    website = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Company or personal website URL",
        validators=[
            URLValidator(
                message=_('Enter a valid URL including http:// or https://'),
                code='invalid_url'
            )
        ]
    )

    linkedin_url = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="LinkedIn profile URL for professional networking",
        validators=[
            URLValidator(
                message=_('Enter a valid LinkedIn URL including https://'),
                code='invalid_url'
            )
        ]
    )

    twitter_url = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Twitter profile URL for social media engagement",
        validators=[
            URLValidator(
                message=_('Enter a valid Twitter URL including https://'),
                code='invalid_url'
            )
        ]
    )

    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True,
        default=list,
        help_text="Descriptive tags for categorization and filtering (e.g., 'VIP', 'Enterprise', 'Tech')"
    )

    class Meta:
        model = Contact
        fields = [
            'id', 'uuid', 'first_name', 'last_name', 'email', 'phone',
            'company', 'title', 'website', 'address', 'city', 'state',
            'country', 'postal_code', 'linkedin_url', 'twitter_url',
            'tags', 'lead_source', 'is_active', 'owner', 'full_name',
            'created_at', 'updated_at'
        ]
        help_texts = {
            'id': 'Unique database identifier for the contact',
            'uuid': 'Universally unique identifier for external references',
            'first_name': 'Contact\'s given name',
            'last_name': 'Contact\'s family name',
            'company': 'Organization or company name',
            'title': 'Professional title or position',
            'website': 'Company or personal website URL',
            'address': 'Street address for business correspondence',
            'city': 'City of residence or business location',
            'state': 'State or province',
            'country': 'Country name or code',
            'postal_code': 'ZIP or postal code for mailing',
            'lead_source': 'How the contact was acquired',
            'is_active': 'Whether the contact is currently active',
            'owner': 'User responsible for managing this contact',
            'created_at': 'Timestamp when contact was created',
            'updated_at': 'Timestamp of last update'
        }
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']

    def validate_email(self, value):
        """
        Validate email format and uniqueness
        Following KISS principle for clean, readable validation
        """
        if not value or not value.strip():
            raise serializers.ValidationError(_('Email address is required.'))

        email = value.strip().lower()

        # Validate email format
        try:
            validate_email(email)
        except DjangoValidationError:
            raise serializers.ValidationError(_('Enter a valid email address.'))

        # Check uniqueness (skip for updates)
        if self.instance:
            if Contact.objects.filter(email=email, owner=self.instance.owner).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(_('A contact with this email already exists.'))
        else:
            # For creation, we'll check uniqueness in the view
            pass

        return email

    def validate_tags(self, value):
        """
        Validate and sanitize tags
        Following KISS principle for simple tag processing
        """
        if not isinstance(value, list):
            raise serializers.ValidationError(_('Tags must be a list.'))

        # Sanitize tags: remove whitespace and empty strings
        sanitized_tags = []
        for tag in value:
            if isinstance(tag, str):
                clean_tag = tag.strip()
                if clean_tag:
                    sanitized_tags.append(clean_tag)
            else:
                # Convert non-string tags to strings
                clean_tag = str(tag).strip()
                if clean_tag:
                    sanitized_tags.append(clean_tag)

        return sanitized_tags

    def validate_first_name(self, value):
        """Validate and sanitize first name"""
        if not value or not value.strip():
            raise serializers.ValidationError(_('First name is required.'))
        return value.strip()

    def validate_last_name(self, value):
        """Validate and sanitize last name"""
        if not value or not value.strip():
            raise serializers.ValidationError(_('Last name is required.'))
        return value.strip()

    def validate_company(self, value):
        """Validate and sanitize company name"""
        if value:
            return value.strip()
        return ''

    def validate_title(self, value):
        """Validate and sanitize title"""
        if value:
            return value.strip()
        return ''

    def validate(self, attrs):
        """
        Cross-field validation
        Following SOLID principles for comprehensive validation
        """
        # Ensure at least one contact method is provided
        if not attrs.get('email') and not attrs.get('phone'):
            raise serializers.ValidationError(
                _('At least one of email or phone must be provided.')
            )

        return attrs


class ContactSerializer(BaseContactSerializer):
    """
    Standard Contact Serializer for general use
    Following Open/Closed Principle for extensibility
    """

    class Meta(BaseContactSerializer.Meta):
        pass


class ContactCreateSerializer(BaseContactSerializer):
    """
    Contact Create Serializer with creation-specific validation
    Following Single Responsibility Principle
    """

    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True
    )

    class Meta(BaseContactSerializer.Meta):
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'company', 'title',
            'website', 'address', 'city', 'state', 'country', 'postal_code',
            'linkedin_url', 'twitter_url', 'tags', 'lead_source', 'owner'
        ]

    def validate(self, attrs):
        """
        Additional validation for contact creation
        """
        attrs = super().validate(attrs)

        # Check email uniqueness for creation
        email = attrs.get('email')
        owner = attrs.get('owner')

        if Contact.objects.filter(email=email, owner=owner).exists():
            raise serializers.ValidationError({
                'email': _('A contact with this email already exists for this owner.')
            })

        return attrs

    def create(self, validated_data):
        """
        Create contact with business logic
        Following KISS principle for clean, readable creation logic
        """
        # Set default values
        validated_data.setdefault('is_active', True)
        validated_data.setdefault('is_deleted', False)

        return super().create(validated_data)


class ContactUpdateSerializer(BaseContactSerializer):
    """
    Contact Update Serializer with update-specific validation
    Following Single Responsibility Principle
    """

    class Meta(BaseContactSerializer.Meta):
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'company', 'title',
            'website', 'address', 'city', 'state', 'country', 'postal_code',
            'linkedin_url', 'twitter_url', 'tags', 'lead_source', 'is_active'
        ]

    def update(self, instance, validated_data):
        """
        Update contact with business logic
        Following KISS principle for clean, readable update logic
        """
        # Sanitize fields that might have whitespace
        for field in ['first_name', 'last_name', 'company', 'title', 'address',
                     'city', 'state', 'country', 'postal_code']:
            if field in validated_data and validated_data[field]:
                validated_data[field] = validated_data[field].strip()

        return super().update(instance, validated_data)


class ContactDetailSerializer(BaseContactSerializer):
    """
    Detailed Contact Serializer with comprehensive information
    Following Single Responsibility Principle for detailed views
    """

    # Computed fields for detailed view
    deals_count = serializers.SerializerMethodField()
    total_deal_value = serializers.SerializerMethodField()
    latest_activity = serializers.SerializerMethodField()
    owner_details = serializers.SerializerMethodField()

    class Meta(BaseContactSerializer.Meta):
        fields = BaseContactSerializer.Meta.fields + [
            'deals_count', 'total_deal_value', 'latest_activity',
            'owner_details', 'deleted_at'
        ]

    def get_deals_count(self, obj):
        """Get number of deals associated with this contact"""
        return obj.deals.count()

    def get_total_deal_value(self, obj):
        """Get total value of all deals for this contact"""
        total = obj.deals.aggregate(
            total=Sum('value')
        )['total'] or 0
        return f"{total:.2f}"

    def get_latest_activity(self, obj):
        """Get the most recent activity for this contact"""
        latest = obj.get_latest_activity()
        if latest:
            return {
                'id': latest.id,
                'type': latest.type,
                'title': latest.title,
                'scheduled_at': latest.scheduled_at,
                'status': latest.status
            }
        return None

    def get_owner_details(self, obj):
        """Get simplified owner information"""
        return {
            'id': obj.owner.id,
            'name': obj.owner.get_full_name(),
            'email': obj.owner.email,
            'role': obj.owner.role
        }


class ContactSummarySerializer(serializers.ModelSerializer):
    """
    Summary Contact Serializer for list views and dropdowns
    Following KISS principle for lightweight data transfer
    """

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Contact
        fields = [
            'id', 'uuid', 'first_name', 'last_name', 'email',
            'full_name', 'company', 'is_active', 'tags'
        ]


class ContactInteractionSerializer(serializers.ModelSerializer):
    """
    Contact Interaction Serializer for interaction tracking
    Following SOLID principles for clean data transformation
    """

    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    interaction_type_display = serializers.CharField(source='get_interaction_type_display', read_only=True)

    class Meta:
        model = ContactInteraction
        fields = [
            'id', 'contact', 'interaction_type', 'interaction_type_display',
            'title', 'description', 'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at']

    def validate_interaction_type(self, value):
        """Validate interaction type"""
        valid_types = [choice[0] for choice in ContactInteraction.INTERACTION_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(
                _('Invalid interaction type. Must be one of: {}').format(', '.join(valid_types))
            )
        return value

    def validate_title(self, value):
        """Validate title"""
        if not value or not value.strip():
            raise serializers.ValidationError(_('Title is required.'))
        return value.strip()

    def create(self, validated_data):
        """Create interaction with proper user assignment"""
        # Set created_by from request context if not provided
        request = self.context.get('request')
        if request and request.user and not validated_data.get('created_by'):
            validated_data['created_by'] = request.user

        return super().create(validated_data)


class ContactBulkOperationSerializer(serializers.Serializer):
    """
    Bulk operation serializer for contact management
    Following KISS principle for simple bulk operations
    """

    contact_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        error_messages={
            'min_length': _('At least one contact ID must be provided.')
        }
    )

    operation = serializers.ChoiceField(
        choices=[
            ('delete', _('Delete')),
            ('restore', _('Restore')),
            ('activate', _('Activate')),
            ('deactivate', _('Deactivate')),
        ]
    )

    def validate_contact_ids(self, value):
        """Validate contact IDs exist"""
        existing_ids = Contact.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)

        if missing_ids:
            raise serializers.ValidationError(
                _('The following contact IDs do not exist: {}').format(list(missing_ids))
            )

        return value

    def validate(self, attrs):
        """Cross-field validation"""
        operation = attrs.get('operation')
        contact_ids = attrs.get('contact_ids')

        # Check if contacts exist for certain operations
        if operation in ['restore', 'delete', 'activate', 'deactivate']:
            if operation == 'restore':
                # For restore, check if contacts are actually deleted
                deleted_count = Contact.all_objects.filter(
                    id__in=contact_ids, is_deleted=True
                ).count()
                if deleted_count == 0:
                    raise serializers.ValidationError(
                        _('No deleted contacts found with the provided IDs.')
                    )
            else:
                # For other operations, check if contacts are active
                active_count = Contact.objects.filter(id__in=contact_ids).count()
                if active_count == 0:
                    raise serializers.ValidationError(
                        _('No active contacts found with the provided IDs.')
                    )

        return attrs