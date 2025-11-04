"""
Activity Repository Implementation
Following SOLID principles and enterprise best practices
"""

from typing import List, Optional, Dict, Any
from django.db.models import Q, Count, Sum
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

from .base import BaseRepository
from crm.apps.activities.models import Activity

logger = logging.getLogger(__name__)


class ActivityRepository(BaseRepository[Activity]):
    """
    Repository for Activity model operations
    Following Repository Pattern and SOLID principles
    """

    def __init__(self, cache_timeout: int = 300):
        """Initialize activity repository"""
        super().__init__(Activity, cache_timeout)

    def get_by_owner(self, owner_id: int, **kwargs) -> List[Activity]:
        """
        Get activities by owner

        Args:
            owner_id: Owner user ID
            **kwargs: Additional filter criteria

        Returns:
            List of activities owned by specified user
        """
        cache_key = self.get_cache_key(f"owner_{owner_id}_{hash(str(kwargs))}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        activities = list(Activity.objects.filter(owner_id=owner_id, **kwargs))
        cache.set(cache_key, activities, self.cache_timeout)
        return activities

    def get_by_contact(self, contact_id: int, **kwargs) -> List[Activity]:
        """
        Get activities for specific contact

        Args:
            contact_id: Contact ID
            **kwargs: Additional filter criteria

        Returns:
            List of activities for specified contact
        """
        cache_key = self.get_cache_key(f"contact_{contact_id}_{hash(str(kwargs))}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        activities = list(Activity.objects.filter(contact_id=contact_id, **kwargs))
        cache.set(cache_key, activities, self.cache_timeout)
        return activities

    def get_by_deal(self, deal_id: int, **kwargs) -> List[Activity]:
        """
        Get activities for specific deal

        Args:
            deal_id: Deal ID
            **kwargs: Additional filter criteria

        Returns:
            List of activities for specified deal
        """
        cache_key = self.get_cache_key(f"deal_{deal_id}_{hash(str(kwargs))}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        activities = list(Activity.objects.filter(deal_id=deal_id, **kwargs))
        cache.set(cache_key, activities, self.cache_timeout)
        return activities

    def get_by_type(self, activity_type: str, owner_id: Optional[int] = None) -> List[Activity]:
        """
        Get activities by type

        Args:
            activity_type: Activity type
            owner_id: Optional owner ID

        Returns:
            List of activities of specified type
        """
        cache_key = self.get_cache_key(f"type_{activity_type}_{owner_id}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        queryset = Activity.objects.filter(type=activity_type)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        activities = list(queryset)
        cache.set(cache_key, activities, self.cache_timeout)
        return activities

    def get_upcoming_activities(self, owner_id: Optional[int] = None, days: Optional[int] = None) -> List[Activity]:
        """
        Get upcoming activities

        Args:
            owner_id: Optional owner ID
            days: Optional days filter (next N days)

        Returns:
            List of upcoming activities
        """
        cache_key = self.get_cache_key(f"upcoming_{owner_id}_{days}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        queryset = Activity.objects.filter(
            scheduled_at__gte=timezone.now(),
            is_completed=False,
            is_cancelled=False
        )

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if days:
            cutoff_date = timezone.now() + timedelta(days=days)
            queryset = queryset.filter(scheduled_at__lte=cutoff_date)

        activities = list(queryset.order_by('scheduled_at'))
        cache.set(cache_key, activities, self.cache_timeout)
        return activities

    def get_overdue_activities(self, owner_id: Optional[int] = None) -> List[Activity]:
        """
        Get overdue activities

        Args:
            owner_id: Optional owner ID

        Returns:
            List of overdue activities
        """
        cache_key = self.get_cache_key(f"overdue_{owner_id}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        queryset = Activity.objects.filter(
            scheduled_at__lt=timezone.now(),
            is_completed=False,
            is_cancelled=False
        )

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        activities = list(queryset.order_by('scheduled_at'))
        cache.set(cache_key, activities, self.cache_timeout)
        return activities

    def get_due_soon_activities(self, hours: int = 24, owner_id: Optional[int] = None) -> List[Activity]:
        """
        Get activities due within specified hours

        Args:
            hours: Number of hours ahead
            owner_id: Optional owner ID

        Returns:
            List of activities due soon
        """
        cache_key = self.get_cache_key(f"due_soon_{hours}_{owner_id}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        cutoff_time = timezone.now() + timedelta(hours=hours)
        queryset = Activity.objects.filter(
            scheduled_at__lte=cutoff_time,
            scheduled_at__gte=timezone.now(),
            is_completed=False,
            is_cancelled=False
        )

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        activities = list(queryset.order_by('scheduled_at'))
        cache.set(cache_key, activities, self.cache_timeout)
        return activities

    def get_completed_activities(self, owner_id: Optional[int] = None, days: Optional[int] = None) -> List[Activity]:
        """
        Get completed activities

        Args:
            owner_id: Optional owner ID
            days: Optional days filter (last N days)

        Returns:
            List of completed activities
        """
        cache_key = self.get_cache_key(f"completed_{owner_id}_{days}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        queryset = Activity.objects.filter(is_completed=True)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if days:
            cutoff_date = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(completed_at__gte=cutoff_date)

        activities = list(queryset.order_by('-completed_at'))
        cache.set(cache_key, activities, self.cache_timeout)
        return activities

    def get_activities_by_priority(self, priority: str, owner_id: Optional[int] = None) -> List[Activity]:
        """
        Get activities by priority

        Args:
            priority: Priority level
            owner_id: Optional owner ID

        Returns:
            List of activities with specified priority
        """
        cache_key = self.get_cache_key(f"priority_{priority}_{owner_id}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        queryset = Activity.objects.filter(priority=priority, is_completed=False, is_cancelled=False)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        activities = list(queryset.order_by('scheduled_at'))
        cache.set(cache_key, activities, self.cache_timeout)
        return activities

    def get_activities_for_date_range(self, start_date, end_date, owner_id: Optional[int] = None) -> List[Activity]:
        """
        Get activities within date range

        Args:
            start_date: Start date
            end_date: End date
            owner_id: Optional owner ID

        Returns:
            List of activities in date range
        """
        cache_key = self.get_cache_key(f"range_{start_date}_{end_date}_{owner_id}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        queryset = Activity.objects.filter(
            scheduled_at__range=[start_date, end_date],
            is_cancelled=False
        )

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        activities = list(queryset.order_by('scheduled_at'))
        cache.set(cache_key, activities, self.cache_timeout)
        return activities

    def search_activities(self, query: str, owner_id: Optional[int] = None) -> List[Activity]:
        """
        Search activities by title, description

        Args:
            query: Search query
            owner_id: Optional owner ID

        Returns:
            List of matching activities
        """
        cache_key = self.get_cache_key(f"search_{query.lower()}_{owner_id}")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        filters = Q(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(contact__first_name__icontains=query) |
            Q(contact__last_name__icontains=query) |
            Q(deal__title__icontains=query)
        )

        if owner_id:
            filters &= Q(owner_id=owner_id)

        activities = list(
            Activity.objects.select_related('contact', 'deal')
            .filter(filters)
        )
        cache.set(cache_key, activities, self.cache_timeout // 2)  # Shorter cache for search
        return activities

    def get_activities_needing_reminders(self) -> List[Activity]:
        """
        Get activities that need reminders sent

        Returns:
            List of activities needing reminders
        """
        cache_key = self.get_cache_key("need_reminders")

        cached_activities = cache.get(cache_key)
        if cached_activities:
            return cached_activities

        activities = list(Activity.objects.filter(
            reminder_at__lte=timezone.now(),
            reminder_sent=False,
            is_completed=False,
            is_cancelled=False
        ).order_by('reminder_at'))

        cache.set(cache_key, activities, 60)  # Very short cache for reminders
        return activities

    def get_activity_statistics(self, owner_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive activity statistics

        Args:
            owner_id: Optional owner ID

        Returns:
            Dictionary with activity statistics
        """
        cache_key = self.get_cache_key(f"statistics_{owner_id}")

        cached_stats = cache.get(cache_key)
        if cached_stats:
            return cached_stats

        queryset = Activity.objects.all()
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        # Basic counts
        total_activities = queryset.count()
        completed_activities = queryset.filter(is_completed=True).count()
        cancelled_activities = queryset.filter(is_cancelled=True).count()
        upcoming_activities = queryset.filter(
            scheduled_at__gte=timezone.now(),
            is_completed=False,
            is_cancelled=False
        ).count()
        overdue_activities = queryset.filter(
            scheduled_at__lt=timezone.now(),
            is_completed=False,
            is_cancelled=False
        ).count()

        # Type distribution
        type_stats = list(
            queryset.values('type')
            .annotate(count=Count('id'))
            .order_by('type')
        )

        # Priority distribution
        priority_stats = list(
            queryset.filter(is_completed=False, is_cancelled=False)
            .values('priority')
            .annotate(count=Count('id'))
            .order_by('priority')
        )

        # Recent activities (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_activities = queryset.filter(created_at__gte=seven_days_ago).count()

        # Activities completed this week
        week_start = timezone.now() - timedelta(days=timezone.now().weekday())
        completed_this_week = queryset.filter(
            is_completed=True,
            completed_at__gte=week_start
        ).count()

        # Completion rate
        completion_rate = (completed_activities / total_activities * 100) if total_activities > 0 else 0

        statistics = {
            'total_activities': total_activities,
            'completed_activities': completed_activities,
            'cancelled_activities': cancelled_activities,
            'upcoming_activities': upcoming_activities,
            'overdue_activities': overdue_activities,
            'completion_rate': round(completion_rate, 2),
            'recent_activities': recent_activities,
            'completed_this_week': completed_this_week,
            'type_distribution': type_stats,
            'priority_distribution': priority_stats,
            'last_updated': timezone.now(),
        }

        cache.set(cache_key, statistics, self.cache_timeout)
        return statistics

    def complete_activity(self, activity_id: int, notes: Optional[str] = None) -> bool:
        """
        Mark activity as completed

        Args:
            activity_id: Activity ID
            notes: Optional completion notes

        Returns:
            True if completed, False otherwise
        """
        try:
            activity = Activity.objects.get(id=activity_id)
            activity.mark_completed(notes)

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{activity_id}")
            if hasattr(activity, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{activity.uuid}")
            self._invalidate_cache_pattern("statistics")

            logger.info(f"Completed activity {activity_id}")
            return True
        except Activity.DoesNotExist:
            logger.warning(f"Failed to complete activity {activity_id}: Not found")
            return False

    def cancel_activity(self, activity_id: int) -> bool:
        """
        Cancel activity

        Args:
            activity_id: Activity ID

        Returns:
            True if cancelled, False otherwise
        """
        try:
            activity = Activity.objects.get(id=activity_id)
            activity.mark_cancelled()

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{activity_id}")
            if hasattr(activity, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{activity.uuid}")
            self._invalidate_cache_pattern("statistics")

            logger.info(f"Cancelled activity {activity_id}")
            return True
        except Activity.DoesNotExist:
            logger.warning(f"Failed to cancel activity {activity_id}: Not found")
            return False

    def reschedule_activity(self, activity_id: int, new_time: timezone.datetime) -> bool:
        """
        Reschedule activity to new time

        Args:
            activity_id: Activity ID
            new_time: New scheduled time

        Returns:
            True if rescheduled, False otherwise
        """
        try:
            activity = Activity.objects.get(id=activity_id)
            activity.reschedule(new_time)

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{activity_id}")
            if hasattr(activity, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{activity.uuid}")
            self._invalidate_cache_pattern("statistics")

            logger.info(f"Rescheduled activity {activity_id} to {new_time}")
            return True
        except Activity.DoesNotExist:
            logger.warning(f"Failed to reschedule activity {activity_id}: Not found")
            return False

    def send_reminder(self, activity_id: int) -> bool:
        """
        Mark reminder as sent for activity

        Args:
            activity_id: Activity ID

        Returns:
            True if reminder sent, False otherwise
        """
        try:
            activity = Activity.objects.get(id=activity_id)
            activity.send_reminder()

            # Invalidate cache
            self._invalidate_cache_pattern("need_reminders")

            logger.info(f"Marked reminder as sent for activity {activity_id}")
            return True
        except Activity.DoesNotExist:
            logger.warning(f"Failed to send reminder for activity {activity_id}: Not found")
            return False

    def clear_activity_cache(self, activity: Activity):
        """
        Clear all cache related to a specific activity

        Args:
            activity: Activity instance
        """
        cache_keys_to_clear = [
            f"id_{activity.id}",
            f"owner_{activity.owner_id}",
            f"type_{activity.type}",
            f"priority_{activity.priority}",
            "statistics",
            "need_reminders",
        ]

        if hasattr(activity, 'uuid'):
            cache_keys_to_clear.append(f"uuid_{activity.uuid}")

        if activity.contact_id:
            cache_keys_to_clear.append(f"contact_{activity.contact_id}")
        if activity.deal_id:
            cache_keys_to_clear.append(f"deal_{activity.deal_id}")

        for key_suffix in cache_keys_to_clear:
            cache_key = self.get_cache_key(key_suffix)
            cache.delete(cache_key)

        logger.debug(f"Cleared cache for activity {activity.title}")