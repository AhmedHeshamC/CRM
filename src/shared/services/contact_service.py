"""
Contact Service Implementation
Following SOLID principles and enterprise best practices
"""

from typing import List, Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.core.exceptions import DjangoValidationError
from django.core.validators import validate_email, ValidationError as DjangoCoreValidationError
from django.utils import timezone
from datetime import timedelta

from .base_service import BaseService, ValidationError, NotFoundError, PermissionError, ConflictError
from ..repositories.contact_repository import ContactRepository
from crm.apps.contacts.models import Contact

User = get_user_model()


class ContactService(BaseService[Contact]):
    """
    Service for Contact business operations
    Following SOLID principles and clean architecture
    """

    def __init__(self, repository: Optional[ContactRepository] = None):
        """Initialize contact service"""
        super().__init__(repository or ContactRepository())

    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate contact data for creation

        Args:
            data: Contact data

        Returns:
            Validated data

        Raises:
            ValidationError: If data is invalid
        """
        validated_data = {}

        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'owner']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"{field} is required")

        validated_data.update({
            'first_name': data['first_name'].strip(),
            'last_name': data['last_name'].strip(),
            'email': data['email'].strip().lower(),
            'owner': data['owner']
        })

        # Validate email format
        try:
            validate_email(validated_data['email'])
        except DjangoCoreValidationError:
            raise ValidationError("Invalid email format")

        # Check email uniqueness for the owner
        if self.repository.exists(email=validated_data['email'], owner=validated_data['owner']):
            raise ConflictError(f"Contact with email {validated_data['email']} already exists for this owner")

        # Validate optional fields
        if 'phone' in data and data['phone']:
            validated_data['phone'] = data['phone'].strip()
            if len(validated_data['phone']) < 10:
                raise ValidationError("Phone number must be at least 10 digits")

        if 'company' in data and data['company']:
            validated_data['company'] = data['company'].strip()

        if 'title' in data and data['title']:
            validated_data['title'] = data['title'].strip()

        # Validate tags if provided
        if 'tags' in data:
            tags = data['tags']
            if not isinstance(tags, list):
                raise ValidationError("Tags must be a list")
            validated_data['tags'] = [tag.strip() for tag in tags if tag.strip()]

        # Validate other optional fields
        for field in ['website', 'address', 'city', 'state', 'country', 'postal_code',
                      'linkedin_url', 'twitter_url', 'lead_source']:
            if field in data and data[field]:
                validated_data[field] = data[field].strip()

        # Set defaults
        validated_data.setdefault('is_active', True)
        validated_data.setdefault('is_deleted', False)

        return validated_data

    def validate_update_data(self, entity_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate contact data for update

        Args:
            entity_id: Contact ID
            data: Update data

        Returns:
            Validated data

        Raises:
            ValidationError: If data is invalid
            NotFoundError: If contact doesn't exist
        """
        # Check if contact exists
        contact = self.repository.get_by_id(entity_id)
        if not contact:
            raise NotFoundError(f"Contact with ID {entity_id} not found")

        validated_data = {}

        # Validate and clean fields
        if 'first_name' in data:
            if not data['first_name'].strip():
                raise ValidationError("First name cannot be empty")
            validated_data['first_name'] = data['first_name'].strip()

        if 'last_name' in data:
            if not data['last_name'].strip():
                raise ValidationError("Last name cannot be empty")
            validated_data['last_name'] = data['last_name'].strip()

        if 'email' in data:
            email = data['email'].strip().lower()
            if not email:
                raise ValidationError("Email cannot be empty")

            try:
                validate_email(email)
            except DjangoCoreValidationError:
                raise ValidationError("Invalid email format")

            # Check email uniqueness (excluding current contact)
            if self.repository.exists(email=email, owner=contact.owner) and contact.email != email:
                raise ConflictError(f"Contact with email {email} already exists for this owner")

            validated_data['email'] = email

        # Validate other fields
        if 'phone' in data:
            if data['phone'] and len(data['phone'].strip()) < 10:
                raise ValidationError("Phone number must be at least 10 digits")
            validated_data['phone'] = data['phone'].strip() if data['phone'] else None

        for field in ['company', 'title', 'website', 'address', 'city', 'state',
                      'country', 'postal_code', 'linkedin_url', 'twitter_url', 'lead_source']:
            if field in data:
                validated_data[field] = data[field].strip() if data[field] else None

        if 'tags' in data:
            tags = data['tags']
            if not isinstance(tags, list):
                raise ValidationError("Tags must be a list")
            validated_data['tags'] = [tag.strip() for tag in tags if tag.strip()]

        if 'is_active' in data:
            validated_data['is_active'] = bool(data['is_active'])

        return validated_data

    def create_contact(self, data: Dict[str, Any], user_id: int) -> Contact:
        """
        Create a new contact with business logic

        Args:
            data: Contact data
            user_id: ID of user creating the contact

        Returns:
            Created contact

        Raises:
            ValidationError: If data is invalid
            PermissionError: If user doesn't have permission
        """
        # Validate owner
        if 'owner' in data:
            owner_id = data['owner'].id if hasattr(data['owner'], 'id') else data['owner']
            if owner_id != user_id:
                # Check if user has permission to create contacts for others
                user = User.objects.get(id=user_id)
                if not user.is_admin() and not user.is_manager():
                    raise PermissionError("You can only create contacts for yourself")

        return self.create(data)

    def update_contact(self, contact_id: int, data: Dict[str, Any], user_id: int) -> Contact:
        """
        Update a contact with business logic

        Args:
            contact_id: Contact ID
            data: Update data
            user_id: ID of user updating the contact

        Returns:
            Updated contact

        Raises:
            ValidationError: If data is invalid
            NotFoundError: If contact doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get contact to check permissions
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise NotFoundError(f"Contact with ID {contact_id} not found")

        # Check permissions
        user = User.objects.get(id=user_id)
        if contact.owner_id != user_id and not user.is_admin():
            raise PermissionError("You can only update your own contacts")

        return self.update(contact_id, data)

    def soft_delete_contact(self, contact_id: int, user_id: int) -> bool:
        """
        Soft delete a contact

        Args:
            contact_id: Contact ID
            user_id: ID of user deleting the contact

        Returns:
            True if deleted

        Raises:
            NotFoundError: If contact doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get contact to check permissions
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise NotFoundError(f"Contact with ID {contact_id} not found")

        # Check permissions
        user = User.objects.get(id=user_id)
        if contact.owner_id != user_id and not user.is_admin():
            raise PermissionError("You can only delete your own contacts")

        return self.repository.soft_delete(contact_id)

    def restore_contact(self, contact_id: int, user_id: int) -> bool:
        """
        Restore a soft-deleted contact

        Args:
            contact_id: Contact ID
            user_id: ID of user restoring the contact

        Returns:
            True if restored

        Raises:
            NotFoundError: If contact doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get contact to check permissions
        contact = self.repository.all_objects().filter(id=contact_id).first()
        if not contact:
            raise NotFoundError(f"Contact with ID {contact_id} not found")

        # Check permissions
        user = User.objects.get(id=user_id)
        if contact.owner_id != user_id and not user.is_admin():
            raise PermissionError("You can only restore your own contacts")

        return self.repository.restore(contact_id)

    def get_contact_deals(self, contact_id: int, user_id: int) -> List:
        """
        Get all deals for a contact

        Args:
            contact_id: Contact ID
            user_id: ID of user requesting the deals

        Returns:
            List of deals

        Raises:
            NotFoundError: If contact doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get contact to check permissions
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise NotFoundError(f"Contact with ID {contact_id} not found")

        # Check permissions
        user = User.objects.get(id=user_id)
        if contact.owner_id != user_id and not user.is_admin():
            raise PermissionError("You can only view deals for your own contacts")

        # Import here to avoid circular imports
        from ..repositories.deal_repository import DealRepository
        deal_repo = DealRepository()
        return deal_repo.get_by_contact(contact_id)

    def update_contact_tags(self, contact_id: int, tags: List[str], user_id: int) -> bool:
        """
        Update contact tags

        Args:
            contact_id: Contact ID
            tags: New list of tags
            user_id: ID of user updating the contact

        Returns:
            True if updated

        Raises:
            NotFoundError: If contact doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get contact to check permissions
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise NotFoundError(f"Contact with ID {contact_id} not found")

        # Check permissions
        user = User.objects.get(id=user_id)
        if contact.owner_id != user_id and not user.is_admin():
            raise PermissionError("You can only update tags for your own contacts")

        # Validate tags
        if not isinstance(tags, list):
            raise ValidationError("Tags must be a list")

        cleaned_tags = [tag.strip() for tag in tags if tag.strip()]
        return self.repository.update_contact_tags(contact_id, cleaned_tags)

    def get_user_contacts(self, user_id: int, **filters) -> List[Contact]:
        """
        Get all contacts for a user

        Args:
            user_id: User ID
            **filters: Additional filters

        Returns:
            List of contacts
        """
        filters['owner_id'] = user_id
        return self.repository.filter(**filters)

    def search_user_contacts(self, user_id: int, query: str) -> List[Contact]:
        """
        Search contacts for a specific user

        Args:
            user_id: User ID
            query: Search query

        Returns:
            List of matching contacts
        """
        return self.repository.search_contacts(query, user_id)

    def get_contact_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get contact statistics

        Args:
            user_id: Optional user ID to filter by

        Returns:
            Statistics dictionary
        """
        return self.repository.get_contact_statistics(user_id)

    def get_recent_contacts(self, user_id: int, days: int = 30) -> List[Contact]:
        """
        Get recent contacts for a user

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            List of recent contacts
        """
        return self.repository.get_recent_contacts(days, user_id)

    def get_contacts_by_company(self, user_id: int, company: str) -> List[Contact]:
        """
        Get contacts by company for a user

        Args:
            user_id: User ID
            company: Company name

        Returns:
            List of contacts
        """
        contacts = self.repository.get_contacts_by_company(company)
        return [contact for contact in contacts if contact.owner_id == user_id]

    def bulk_create_contacts(self, contacts_data: List[Dict[str, Any]], user_id: int) -> List[Contact]:
        """
        Bulk create contacts for a user

        Args:
            contacts_data: List of contact data
            user_id: User ID

        Returns:
            List of created contacts

        Raises:
            PermissionError: If user doesn't have permission
            ValidationError: If any contact data is invalid
        """
        # Check permissions
        user = User.objects.get(id=user_id)
        if not user.is_admin() and not user.is_manager():
            raise PermissionError("Only admins and managers can bulk create contacts")

        # Validate all contacts
        validated_contacts = []
        for contact_data in contacts_data:
            validated_data = self.validate_create_data(contact_data)
            validated_contacts.append(validated_data)

        return self.repository.bulk_create_contacts(validated_contacts)