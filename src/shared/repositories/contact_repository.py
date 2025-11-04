"""
Contact Repository Implementation
Following SOLID principles and enterprise best practices
"""

from typing import List, Optional, Dict, Any
from django.db.models import Q, Count, Sum
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

from .base import SoftDeleteRepository
from crm.apps.contacts.models import Contact

logger = logging.getLogger(__name__)


class ContactRepository(SoftDeleteRepository[Contact]):
    """
    Repository for Contact model operations
    Following Repository Pattern and SOLID principles
    """

    def __init__(self, cache_timeout: int = 300):
        """Initialize contact repository"""
        super().__init__(Contact, cache_timeout)

    def get_by_email(self, email: str, use_cache: bool = True) -> Optional[Contact]:
        """
        Get contact by email (case-insensitive)

        Args:
            email: Contact email
            use_cache: Whether to use cache

        Returns:
            Contact instance or None
        """
        cache_key = self.get_cache_key(f"email_{email.lower()}")

        if use_cache:
            cached_contact = cache.get(cache_key)
            if cached_contact:
                logger.debug(f"Cache hit for contact email {email}")
                return cached_contact

        try:
            contact = Contact.objects.get(email__iexact=email)
            if use_cache:
                cache.set(cache_key, contact, self.cache_timeout)
            return contact
        except Contact.DoesNotExist:
            logger.debug(f"Contact with email {email} not found")
            return None

    def get_by_owner(self, owner_id: int, **kwargs) -> List[Contact]:
        """
        Get contacts by owner

        Args:
            owner_id: Owner user ID
            **kwargs: Additional filter criteria

        Returns:
            List of contacts owned by specified user
        """
        cache_key = self.get_cache_key(f"owner_{owner_id}_{hash(str(kwargs))}")

        cached_contacts = cache.get(cache_key)
        if cached_contacts:
            return cached_contacts

        contacts = list(Contact.objects.filter(owner_id=owner_id, **kwargs))
        cache.set(cache_key, contacts, self.cache_timeout)
        return contacts

    def search_contacts(self, query: str, owner_id: Optional[int] = None) -> List[Contact]:
        """
        Search contacts by name, email, company

        Args:
            query: Search query
            owner_id: Optional owner ID to filter by

        Returns:
            List of matching contacts
        """
        cache_key = self.get_cache_key(f"search_{query.lower()}_{owner_id}")

        cached_contacts = cache.get(cache_key)
        if cached_contacts:
            return cached_contacts

        filters = Q(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(company__icontains=query)
        )

        if owner_id:
            filters &= Q(owner_id=owner_id)

        contacts = list(Contact.objects.filter(filters))
        cache.set(cache_key, contacts, self.cache_timeout // 2)  # Shorter cache for search
        return contacts

    def get_contacts_by_company(self, company: str, **kwargs) -> List[Contact]:
        """
        Get contacts by company

        Args:
            company: Company name
            **kwargs: Additional filter criteria

        Returns:
            List of contacts from specified company
        """
        cache_key = self.get_cache_key(f"company_{company}_{hash(str(kwargs))}")

        cached_contacts = cache.get(cache_key)
        if cached_contacts:
            return cached_contacts

        contacts = list(Contact.objects.filter(company__iexact=company, **kwargs))
        cache.set(cache_key, contacts, self.cache_timeout)
        return contacts

    def get_contacts_with_tags(self, tags: List[str], owner_id: Optional[int] = None) -> List[Contact]:
        """
        Get contacts that have all specified tags

        Args:
            tags: List of tags to filter by
            owner_id: Optional owner ID

        Returns:
            List of contacts with specified tags
        """
        cache_key = self.get_cache_key(f"tags_{sorted(tags)}_{owner_id}")

        cached_contacts = cache.get(cache_key)
        if cached_contacts:
            return cached_contacts

        queryset = Contact.objects.all()
        for tag in tags:
            queryset = queryset.filter(tags__contains=[tag])

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        contacts = list(queryset)
        cache.set(cache_key, contacts, self.cache_timeout)
        return contacts

    def get_recent_contacts(self, days: int = 30, owner_id: Optional[int] = None) -> List[Contact]:
        """
        Get contacts created within specified days

        Args:
            days: Number of days to look back
            owner_id: Optional owner ID

        Returns:
            List of recent contacts
        """
        cache_key = self.get_cache_key(f"recent_{days}_{owner_id}")

        cached_contacts = cache.get(cache_key)
        if cached_contacts:
            return cached_contacts

        cutoff_date = timezone.now() - timedelta(days=days)
        queryset = Contact.objects.filter(created_at__gte=cutoff_date)

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        contacts = list(queryset.order_by('-created_at'))
        cache.set(cache_key, contacts, self.cache_timeout)
        return contacts

    def get_contacts_by_lead_source(self, lead_source: str, **kwargs) -> List[Contact]:
        """
        Get contacts by lead source

        Args:
            lead_source: Lead source name
            **kwargs: Additional filter criteria

        Returns:
            List of contacts from specified lead source
        """
        cache_key = self.get_cache_key(f"lead_source_{lead_source}_{hash(str(kwargs))}")

        cached_contacts = cache.get(cache_key)
        if cached_contacts:
            return cached_contacts

        contacts = list(Contact.objects.filter(lead_source=lead_source, **kwargs))
        cache.set(cache_key, contacts, self.cache_timeout)
        return contacts

    def get_active_contacts(self, owner_id: Optional[int] = None) -> List[Contact]:
        """
        Get only active contacts

        Args:
            owner_id: Optional owner ID

        Returns:
            List of active contacts
        """
        cache_key = self.get_cache_key(f"active_{owner_id}")

        cached_contacts = cache.get(cache_key)
        if cached_contacts:
            return cached_contacts

        queryset = Contact.objects.filter(is_active=True)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        contacts = list(queryset)
        cache.set(cache_key, contacts, self.cache_timeout)
        return contacts

    def get_contact_statistics(self, owner_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get contact statistics

        Args:
            owner_id: Optional owner ID

        Returns:
            Dictionary with contact statistics
        """
        cache_key = self.get_cache_key(f"statistics_{owner_id}")

        cached_stats = cache.get(cache_key)
        if cached_stats:
            return cached_stats

        queryset = Contact.objects.all()
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        total_contacts = queryset.count()
        active_contacts = queryset.filter(is_active=True).count()
        inactive_contacts = total_contacts - active_contacts

        # Contacts by company (top 10)
        company_stats = list(
            queryset.values('company')
            .annotate(count=Count('id'))
            .exclude(company__isnull=True)
            .exclude(company='')
            .order_by('-count')[:10]
        )

        # Contacts by lead source
        lead_source_stats = list(
            queryset.values('lead_source')
            .annotate(count=Count('id'))
            .exclude(lead_source__isnull=True)
            .exclude(lead_source='')
            .order_by('-count')
        )

        # Contacts created in last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_contacts = queryset.filter(created_at__gte=thirty_days_ago).count()

        # Average deals per contact
        avg_deals_per_contact = 0
        if total_contacts > 0:
            total_deals = sum(contact.get_deals_count() for contact in queryset)
            avg_deals_per_contact = total_deals / total_contacts

        statistics = {
            'total_contacts': total_contacts,
            'active_contacts': active_contacts,
            'inactive_contacts': inactive_contacts,
            'company_distribution': company_stats,
            'lead_source_distribution': lead_source_stats,
            'recent_contacts': recent_contacts,
            'average_deals_per_contact': round(avg_deals_per_contact, 2),
            'last_updated': timezone.now(),
        }

        cache.set(cache_key, statistics, self.cache_timeout)
        return statistics

    def bulk_create_contacts(self, contacts_data: List[Dict[str, Any]]) -> List[Contact]:
        """
        Bulk create contacts

        Args:
            contacts_data: List of contact data dictionaries

        Returns:
            List of created contacts
        """
        contacts = self.bulk_create(contacts_data)

        # Invalidate cache
        self._invalidate_cache_pattern("statistics")
        self._invalidate_cache_pattern("active")
        self._invalidate_cache_pattern("recent")

        logger.info(f"Bulk created {len(contacts)} contacts")
        return contacts

    def update_contact_tags(self, contact_id: int, tags: List[str]) -> bool:
        """
        Update contact tags

        Args:
            contact_id: Contact ID
            tags: New list of tags

        Returns:
            True if updated, False otherwise
        """
        try:
            contact = Contact.objects.get(id=contact_id)
            old_tags = contact.tags
            contact.tags = tags
            contact.save()

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{contact_id}")
            if hasattr(contact, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{contact.uuid}")
            self._invalidate_cache_pattern("statistics")

            logger.info(f"Updated tags for contact ID {contact_id}: {old_tags} -> {tags}")
            return True
        except Contact.DoesNotExist:
            logger.warning(f"Failed to update tags for contact ID {contact_id}: Not found")
            return False

    def clear_contact_cache(self, contact: Contact):
        """
        Clear all cache related to a specific contact

        Args:
            contact: Contact instance
        """
        cache_keys_to_clear = [
            f"id_{contact.id}",
            f"email_{contact.email.lower()}",
            f"owner_{contact.owner_id}",
            f"company_{contact.company}",
            "active",
            "statistics",
        ]

        if hasattr(contact, 'uuid'):
            cache_keys_to_clear.append(f"uuid_{contact.uuid}")

        for key_suffix in cache_keys_to_clear:
            cache_key = self.get_cache_key(key_suffix)
            cache.delete(cache_key)

        logger.debug(f"Cleared cache for contact {contact.email}")