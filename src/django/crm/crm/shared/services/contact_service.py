"""
Contact Service - KISS Implementation
Simple business logic following SOLID principles
"""

from ..repositories.contact_repository import ContactRepository
from django.core.exceptions import ValidationError
from django.db import models


class ContactService:
    """
    Simple Contact Service - Following KISS principle
    Focused only on contact business logic
    """

    def __init__(self, repository=None):
        """Initialize with repository"""
        self.repository = repository or ContactRepository()

    def create_contact(self, data, user_id):
        """Create new contact with simple validation"""
        # Check for duplicate email
        if 'email' in data:
            existing = self.repository.get_by_email(data['email'], user_id)
            if existing:
                raise ValidationError('A contact with this email already exists.')

        # Set owner
        data['owner_id'] = user_id
        return self.repository.create(**data)

    def update_contact(self, contact_id, data, user_id):
        """Update contact with simple validation"""
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise ValidationError('Contact not found.')

        # Check permission
        if contact.owner_id != user_id:
            raise ValidationError('Permission denied.')

        # Check email uniqueness if email is being changed
        if 'email' in data and data['email'] != contact.email:
            existing = self.repository.get_by_email(data['email'], user_id)
            if existing and existing.id != contact_id:
                raise ValidationError('A contact with this email already exists.')

        return self.repository.update(contact, **data)

    def soft_delete_contact(self, contact_id, user_id):
        """Soft delete contact with permission check"""
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise ValidationError('Contact not found.')

        if contact.owner_id != user_id:
            raise ValidationError('Permission denied.')

        self.repository.soft_delete(contact)

    def restore_contact(self, contact_id, user_id):
        """Restore soft-deleted contact"""
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise ValidationError('Contact not found.')

        if contact.owner_id != user_id:
            raise ValidationError('Permission denied.')

        if hasattr(contact, 'is_deleted'):
            contact.is_deleted = False
            contact.save()
        else:
            raise ValidationError('Contact does not support soft delete.')

    def update_contact_tags(self, contact_id, tags, user_id):
        """Update contact tags"""
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise ValidationError('Contact not found.')

        if contact.owner_id != user_id:
            raise ValidationError('Permission denied.')

        contact.tags = tags
        contact.save()
        return True

    def get_contact_deals(self, contact_id, user_id):
        """Get deals for contact"""
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise ValidationError('Contact not found.')

        if contact.owner_id != user_id:
            raise ValidationError('Permission denied.')

        from ..repositories.deal_repository import DealRepository
        deal_repo = DealRepository()
        return deal_repo.get_contact_deals(contact_id, user_id)

    def get_contact_statistics(self, user_id=None):
        """Get contact statistics"""
        stats = self.repository.get_statistics(user_id)

        # Add deals information
        from ..repositories.deal_repository import DealRepository
        deal_repo = DealRepository()
        if user_id:
            contact_ids = self.repository.filter(owner_id=user_id).values_list('id', flat=True)
            deals_stats = deal_repo.filter(contact_id__in=contact_ids).aggregate(
                total_value=models.Sum('value'),
                deals_count=models.Count('id')
            )
        else:
            deals_stats = deal_repo.filter().aggregate(
                total_value=models.Sum('value'),
                deals_count=models.Count('id')
            )

        stats.update({
            'total_deal_value': deals_stats['total_value'] or 0,
            'total_deals_count': deals_stats['deals_count'] or 0,
        })

        return stats

    def get_recent_contacts(self, user_id, days=30):
        """Get recent contacts"""
        return self.repository.get_recent_contacts(user_id, days)

    def get_contacts_by_company(self, user_id, company):
        """Get contacts by company"""
        return self.repository.get_by_company(user_id, company)

    def search_user_contacts(self, user_id, query):
        """Search contacts for user"""
        return self.repository.search_contacts(user_id, query)