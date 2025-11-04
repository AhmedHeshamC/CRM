"""
Deal Repository Implementation
Following SOLID principles and enterprise best practices
"""

from typing import List, Optional, Dict, Any
from django.db.models import Q, Count, Sum, Avg
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

from .base import BaseRepository
from crm.apps.deals.models import Deal

logger = logging.getLogger(__name__)


class DealRepository(BaseRepository[Deal]):
    """
    Repository for Deal model operations
    Following Repository Pattern and SOLID principles
    """

    def __init__(self, cache_timeout: int = 300):
        """Initialize deal repository"""
        super().__init__(Deal, cache_timeout)

    def get_by_owner(self, owner_id: int, **kwargs) -> List[Deal]:
        """
        Get deals by owner

        Args:
            owner_id: Owner user ID
            **kwargs: Additional filter criteria

        Returns:
            List of deals owned by specified user
        """
        cache_key = self.get_cache_key(f"owner_{owner_id}_{hash(str(kwargs))}")

        cached_deals = cache.get(cache_key)
        if cached_deals:
            return cached_deals

        deals = list(Deal.objects.filter(owner_id=owner_id, **kwargs))
        cache.set(cache_key, deals, self.cache_timeout)
        return deals

    def get_by_contact(self, contact_id: int, **kwargs) -> List[Deal]:
        """
        Get deals for specific contact

        Args:
            contact_id: Contact ID
            **kwargs: Additional filter criteria

        Returns:
            List of deals for specified contact
        """
        cache_key = self.get_cache_key(f"contact_{contact_id}_{hash(str(kwargs))}")

        cached_deals = cache.get(cache_key)
        if cached_deals:
            return cached_deals

        deals = list(Deal.objects.filter(contact_id=contact_id, **kwargs))
        cache.set(cache_key, deals, self.cache_timeout)
        return deals

    def get_by_stage(self, stage: str, owner_id: Optional[int] = None) -> List[Deal]:
        """
        Get deals by specific stage

        Args:
            stage: Deal stage
            owner_id: Optional owner ID

        Returns:
            List of deals in specified stage
        """
        cache_key = self.get_cache_key(f"stage_{stage}_{owner_id}")

        cached_deals = cache.get(cache_key)
        if cached_deals:
            return cached_deals

        queryset = Deal.objects.filter(stage=stage)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        deals = list(queryset)
        cache.set(cache_key, deals, self.cache_timeout)
        return deals

    def get_open_deals(self, owner_id: Optional[int] = None) -> List[Deal]:
        """
        Get all open deals (not won or lost)

        Args:
            owner_id: Optional owner ID

        Returns:
            List of open deals
        """
        cache_key = self.get_cache_key(f"open_{owner_id}")

        cached_deals = cache.get(cache_key)
        if cached_deals:
            return cached_deals

        queryset = Deal.objects.exclude(stage__in=['closed_won', 'closed_lost'])
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        deals = list(queryset.order_by('-created_at'))
        cache.set(cache_key, deals, self.cache_timeout)
        return deals

    def get_won_deals(self, owner_id: Optional[int] = None, days: Optional[int] = None) -> List[Deal]:
        """
        Get won deals

        Args:
            owner_id: Optional owner ID
            days: Optional days filter (last N days)

        Returns:
            List of won deals
        """
        cache_key = self.get_cache_key(f"won_{owner_id}_{days}")

        cached_deals = cache.get(cache_key)
        if cached_deals:
            return cached_deals

        queryset = Deal.objects.filter(stage='closed_won')
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if days:
            cutoff_date = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(closed_date__gte=cutoff_date)

        deals = list(queryset.order_by('-closed_date'))
        cache.set(cache_key, deals, self.cache_timeout)
        return deals

    def get_lost_deals(self, owner_id: Optional[int] = None, days: Optional[int] = None) -> List[Deal]:
        """
        Get lost deals

        Args:
            owner_id: Optional owner ID
            days: Optional days filter (last N days)

        Returns:
            List of lost deals
        """
        cache_key = self.get_cache_key(f"lost_{owner_id}_{days}")

        cached_deals = cache.get(cache_key)
        if cached_deals:
            return cached_deals

        queryset = Deal.objects.filter(stage='closed_lost')
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if days:
            cutoff_date = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(closed_date__gte=cutoff_date)

        deals = list(queryset.order_by('-closed_date'))
        cache.set(cache_key, deals, self.cache_timeout)
        return deals

    def get_closing_soon(self, days: int = 30, owner_id: Optional[int] = None) -> List[Deal]:
        """
        Get deals expected to close within specified days

        Args:
            days: Number of days ahead
            owner_id: Optional owner ID

        Returns:
            List of deals closing soon
        """
        cache_key = self.get_cache_key(f"closing_soon_{days}_{owner_id}")

        cached_deals = cache.get(cache_key)
        if cached_deals:
            return cached_deals

        cutoff_date = timezone.now() + timedelta(days=days)
        queryset = Deal.objects.filter(
            expected_close_date__lte=cutoff_date,
            stage__in=['qualified', 'proposal', 'negotiation']
        )

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        deals = list(queryset.order_by('expected_close_date'))
        cache.set(cache_key, deals, self.cache_timeout)
        return deals

    def get_overdue_deals(self, owner_id: Optional[int] = None) -> List[Deal]:
        """
        Get deals past their expected close date

        Args:
            owner_id: Optional owner ID

        Returns:
            List of overdue deals
        """
        cache_key = self.get_cache_key(f"overdue_{owner_id}")

        cached_deals = cache.get(cache_key)
        if cached_deals:
            return cached_deals

        queryset = Deal.objects.filter(
            expected_close_date__lt=timezone.now().date(),
            stage__in=['qualified', 'proposal', 'negotiation']
        )

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        deals = list(queryset.order_by('expected_close_date'))
        cache.set(cache_key, deals, self.cache_timeout)
        return deals

    def get_deals_by_value_range(self, min_value: float, max_value: float, owner_id: Optional[int] = None) -> List[Deal]:
        """
        Get deals within value range

        Args:
            min_value: Minimum deal value
            max_value: Maximum deal value
            owner_id: Optional owner ID

        Returns:
            List of deals within value range
        """
        cache_key = self.get_cache_key(f"value_{min_value}_{max_value}_{owner_id}")

        cached_deals = cache.get(cache_key)
        if cached_deals:
            return cached_deals

        queryset = Deal.objects.filter(value__gte=min_value, value__lte=max_value)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        deals = list(queryset.order_by('-value'))
        cache.set(cache_key, deals, self.cache_timeout)
        return deals

    def search_deals(self, query: str, owner_id: Optional[int] = None) -> List[Deal]:
        """
        Search deals by title, description, company

        Args:
            query: Search query
            owner_id: Optional owner ID

        Returns:
            List of matching deals
        """
        cache_key = self.get_cache_key(f"search_{query.lower()}_{owner_id}")

        cached_deals = cache.get(cache_key)
        if cached_deals:
            return cached_deals

        filters = Q(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(contact__first_name__icontains=query) |
            Q(contact__last_name__icontains=query) |
            Q(contact__company__icontains=query)
        )

        if owner_id:
            filters &= Q(owner_id=owner_id)

        deals = list(Deal.objects.select_related('contact').filter(filters))
        cache.set(cache_key, deals, self.cache_timeout // 2)  # Shorter cache for search
        return deals

    def get_deal_statistics(self, owner_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive deal statistics

        Args:
            owner_id: Optional owner ID

        Returns:
            Dictionary with deal statistics
        """
        cache_key = self.get_cache_key(f"statistics_{owner_id}")

        cached_stats = cache.get(cache_key)
        if cached_stats:
            return cached_stats

        queryset = Deal.objects.all()
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        # Basic counts
        total_deals = queryset.count()
        open_deals = queryset.exclude(stage__in=['closed_won', 'closed_lost']).count()
        won_deals = queryset.filter(stage='closed_won').count()
        lost_deals = queryset.filter(stage='closed_lost').count()

        # Value calculations
        total_pipeline_value = queryset.aggregate(Sum('value'))['value__sum'] or 0
        won_deals_value = queryset.filter(stage='closed_won').aggregate(Sum('value'))['value__sum'] or 0

        # Stage distribution
        stage_stats = list(
            queryset.values('stage')
            .annotate(count=Count('id'), total_value=Sum('value'))
            .order_by('stage')
        )

        # Recent deals (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_deals = queryset.filter(created_at__gte=thirty_days_ago).count()

        # Average deal size
        avg_deal_size = queryset.aggregate(Avg('value'))['value__avg'] or 0

        # Conversion rates
        conversion_rate = (won_deals / total_deals * 100) if total_deals > 0 else 0

        # Average time to close (for closed deals)
        closed_deals = queryset.filter(stage__in=['closed_won', 'closed_lost'], closed_date__isnull=False)
        avg_time_to_close = 0
        if closed_deals.exists():
            total_days = sum(
                (deal.closed_date.date() - deal.created_at.date()).days
                for deal in closed_deals
            )
            avg_time_to_close = total_days / closed_deals.count()

        # Top deals by value
        top_deals = list(
            queryset.order_by('-value')[:5]
            .values('id', 'title', 'value', 'stage')
        )

        statistics = {
            'total_deals': total_deals,
            'open_deals': open_deals,
            'won_deals': won_deals,
            'lost_deals': lost_deals,
            'total_pipeline_value': float(total_pipeline_value),
            'won_deals_value': float(won_deals_value),
            'conversion_rate': round(conversion_rate, 2),
            'average_deal_size': float(avg_deal_size),
            'average_time_to_close_days': round(avg_time_to_close, 1),
            'recent_deals': recent_deals,
            'stage_distribution': stage_stats,
            'top_deals': top_deals,
            'last_updated': timezone.now(),
        }

        cache.set(cache_key, statistics, self.cache_timeout)
        return statistics

    def get_pipeline_value_by_stage(self, owner_id: Optional[int] = None) -> Dict[str, float]:
        """
        Get pipeline value breakdown by stage

        Args:
            owner_id: Optional owner ID

        Returns:
            Dictionary with pipeline values by stage
        """
        cache_key = self.get_cache_key(f"pipeline_value_{owner_id}")

        cached_values = cache.get(cache_key)
        if cached_values:
            return cached_values

        queryset = Deal.objects.all()
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        stage_values = (
            queryset.values('stage')
            .annotate(total_value=Sum('value'))
            .order_by('stage')
        )

        pipeline_values = {
            item['stage']: float(item['total_value'] or 0)
            for item in stage_values
        }

        cache.set(cache_key, pipeline_values, self.cache_timeout)
        return pipeline_values

    def update_deal_stage(self, deal_id: int, new_stage: str, changed_by_user_id: Optional[int] = None) -> bool:
        """
        Update deal stage with validation

        Args:
            deal_id: Deal ID
            new_stage: New stage
            changed_by_user_id: User ID who made the change

        Returns:
            True if updated, False otherwise
        """
        try:
            deal = Deal.objects.get(id=deal_id)

            # Validate stage transition
            if not deal.can_transition_to(new_stage):
                logger.warning(f"Invalid stage transition for deal {deal_id}: {deal.stage} -> {new_stage}")
                return False

            old_stage = deal.stage
            deal.stage = new_stage
            deal._changed_by_user_id = changed_by_user_id
            deal.save()

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{deal_id}")
            if hasattr(deal, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{deal.uuid}")
            self._invalidate_cache_pattern("statistics")
            self._invalidate_cache_pattern("pipeline_value")

            logger.info(f"Updated deal {deal_id} stage: {old_stage} -> {new_stage}")
            return True
        except Deal.DoesNotExist:
            logger.warning(f"Failed to update stage for deal {deal_id}: Not found")
            return False

    def close_deal_as_won(self, deal_id: int, final_value: Optional[float] = None) -> bool:
        """
        Close deal as won

        Args:
            deal_id: Deal ID
            final_value: Optional final value override

        Returns:
            True if closed, False otherwise
        """
        try:
            deal = Deal.objects.get(id=deal_id)
            deal.close_as_won(final_value)

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{deal_id}")
            if hasattr(deal, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{deal.uuid}")
            self._invalidate_cache_pattern("statistics")
            self._invalidate_cache_pattern("pipeline_value")

            logger.info(f"Closed deal {deal_id} as won")
            return True
        except Deal.DoesNotExist:
            logger.warning(f"Failed to close deal {deal_id} as won: Not found")
            return False

    def close_deal_as_lost(self, deal_id: int, loss_reason: str) -> bool:
        """
        Close deal as lost

        Args:
            deal_id: Deal ID
            loss_reason: Reason for losing the deal

        Returns:
            True if closed, False otherwise
        """
        try:
            deal = Deal.objects.get(id=deal_id)
            deal.close_as_lost(loss_reason)

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{deal_id}")
            if hasattr(deal, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{deal.uuid}")
            self._invalidate_cache_pattern("statistics")
            self._invalidate_cache_pattern("pipeline_value")

            logger.info(f"Closed deal {deal_id} as lost: {loss_reason}")
            return True
        except Deal.DoesNotExist:
            logger.warning(f"Failed to close deal {deal_id} as lost: Not found")
            return False

    def clear_deal_cache(self, deal: Deal):
        """
        Clear all cache related to a specific deal

        Args:
            deal: Deal instance
        """
        cache_keys_to_clear = [
            f"id_{deal.id}",
            f"owner_{deal.owner_id}",
            f"contact_{deal.contact_id}",
            f"stage_{deal.stage}",
            "statistics",
            "pipeline_value",
        ]

        if hasattr(deal, 'uuid'):
            cache_keys_to_clear.append(f"uuid_{deal.uuid}")

        for key_suffix in cache_keys_to_clear:
            cache_key = self.get_cache_key(key_suffix)
            cache.delete(cache_key)

        logger.debug(f"Cleared cache for deal {deal.title}")