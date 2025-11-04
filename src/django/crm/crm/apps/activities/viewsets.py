"""
Activity ViewSets - API Endpoint Layer
Following SOLID principles and enterprise best practices
"""

from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from .models import Activity, ActivityComment
from .serializers import (
    ActivitySerializer, ActivityDetailSerializer, ActivityCreateSerializer,
    ActivityUpdateSerializer, ActivitySummarySerializer,
    ActivityCommentSerializer, ActivityBulkOperationSerializer,
    ActivityStatisticsSerializer
)
from ..shared.repositories.activity_repository import ActivityRepository
from ..shared.services.activity_service import ActivityService
from crm.apps.contacts.models import Contact
from crm.apps.deals.models import Deal
from ...shared.authentication.permissions import ActivityPermission, IsAdminUser

User = get_user_model()


class ActivityViewSet(viewsets.ModelViewSet):
    """
    Activity ViewSet for comprehensive activity management
    Following SOLID principles and clean architecture
    """

    # Repository and Service layers
    repository = ActivityRepository()
    service = ActivityService(repository)

    # Permission and authentication
    permission_classes = [ActivityPermission]

    # Filtering and searching
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type', 'priority', 'is_completed', 'is_cancelled', 'contact', 'deal']
    search_fields = ['title', 'description', 'contact__first_name', 'contact__last_name', 'deal__title']
    ordering_fields = ['title', 'type', 'priority', 'scheduled_at', 'created_at', 'updated_at']
    ordering = ['scheduled_at']

    def get_queryset(self):
        """
        Get activities based on user permissions
        Following SOLID principles for access control
        """
        user = self.request.user

        # Admin users can see all activities
        if user.is_admin():
            return Activity.objects.all()

        # Managers can see activities of their team (implementation depends on requirements)
        # For now, managers see their own activities
        if user.is_manager():
            return Activity.objects.filter(owner=user)

        # Regular users only see their own activities
        return Activity.objects.filter(owner=user)

    def get_serializer_class(self):
        """
        Select appropriate serializer based on action
        Following Single Responsibility Principle
        """
        if self.action == 'create':
            return ActivityCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return ActivityUpdateSerializer
        elif self.action == 'retrieve':
            return ActivityDetailSerializer
        elif self.action == 'list':
            return ActivitySummarySerializer
        return ActivitySerializer

    def perform_create(self, serializer):
        """
        Handle activity creation with business logic
        Following SOLID principles for clean business logic separation
        """
        user = self.request.user
        validated_data = serializer.validated_data.copy()

        # Set owner to current user if not specified
        if 'owner' not in validated_data:
            validated_data['owner'] = user

        # Validate business rules
        try:
            activity = self.service.create_activity(validated_data, user.id)
            return activity
        except Exception as e:
            raise ValidationError(str(e))

    def perform_update(self, serializer):
        """
        Handle activity update with business logic
        Following SOLID principles for clean business logic separation
        """
        user = self.request.user
        activity_id = self.get_object().id
        validated_data = serializer.validated_data.copy()

        try:
            activity = self.service.update_activity(activity_id, validated_data, user.id)
            return activity
        except Exception as e:
            raise ValidationError(str(e))

    def get_object(self):
        """
        Get activity with permission checking
        Following SOLID principles for proper access control
        """
        pk = self.kwargs.get('pk')
        try:
            activity = Activity.objects.get(pk=pk)
        except Activity.DoesNotExist:
            raise NotFound('Activity not found.')

        # Check permissions
        user = self.request.user
        if not user.is_admin() and activity.owner != user:
            raise NotFound('Activity not found.')

        return activity

    def list(self, request, *args, **kwargs):
        """
        List activities with enhanced filtering and pagination
        Following KISS principle for clean, readable implementation
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Custom filtering logic
        activity_type = request.query_params.get('type')
        if activity_type:
            queryset = queryset.filter(type=activity_type)

        priority = request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        is_completed = request.query_params.get('is_completed')
        if is_completed is not None:
            queryset = queryset.filter(is_completed=is_completed.lower() == 'true')

        is_cancelled = request.query_params.get('is_cancelled')
        if is_cancelled is not None:
            queryset = queryset.filter(is_cancelled=is_cancelled.lower() == 'true')

        # Date filtering
        scheduled_after = request.query_params.get('scheduled_after')
        if scheduled_after:
            try:
                datetime_obj = datetime.fromisoformat(scheduled_after.replace('Z', '+00:00'))
                queryset = queryset.filter(scheduled_at__gte=datetime_obj)
            except ValueError:
                pass

        scheduled_before = request.query_params.get('scheduled_before')
        if scheduled_before:
            try:
                datetime_obj = datetime.fromisoformat(scheduled_before.replace('Z', '+00:00'))
                queryset = queryset.filter(scheduled_at__lte=datetime_obj)
            except ValueError:
                pass

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Complete an activity
        Following Single Responsibility Principle
        """
        activity = self.get_object()
        user = request.user
        completion_notes = request.data.get('completion_notes', '')

        try:
            self.service.complete_activity(activity.id, completion_notes, user.id)
            return Response({
                'message': 'Activity completed successfully',
                'activity_id': activity.id,
                'status': 'completed',
                'completed_at': activity.completed_at
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel an activity
        Following Single Responsibility Principle
        """
        activity = self.get_object()
        user = request.user

        try:
            self.service.cancel_activity(activity.id, user.id)
            return Response({
                'message': 'Activity cancelled successfully',
                'activity_id': activity.id,
                'status': 'cancelled'
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """
        Reschedule an activity
        Following Single Responsibility Principle
        """
        activity = self.get_object()
        user = request.user
        new_scheduled_time = request.data.get('new_scheduled_time')
        reason = request.data.get('reason', '')

        if not new_scheduled_time:
            raise ValidationError('New scheduled time is required.')

        try:
            # Parse the new scheduled time
            new_time = datetime.fromisoformat(new_scheduled_time.replace('Z', '+00:00'))

            # Reschedule activity
            activity = self.service.reschedule_activity(activity.id, new_time, user.id)

            # Log the reschedule reason if provided
            if reason:
                ActivityComment.objects.create(
                    activity=activity,
                    author=user,
                    comment=f"Rescheduled: {reason}"
                )

            return Response({
                'message': 'Activity rescheduled successfully',
                'activity_id': activity.id,
                'new_scheduled_time': activity.scheduled_at.isoformat(),
                'reason': reason
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """
        Add comment to activity
        Following Single Responsibility Principle
        """
        activity = self.get_object()
        user = request.user
        comment_text = request.data.get('comment', '')

        if not comment_text:
            raise ValidationError('Comment text is required.')

        try:
            comment = ActivityComment.objects.create(
                activity=activity,
                author=user,
                comment=comment_text
            )

            serializer = ActivityCommentSerializer(comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """
        Perform bulk operations on activities
        Following Single Responsibility Principle
        """
        serializer = ActivityBulkOperationSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        activity_ids = serializer.validated_data['activity_ids']
        operation = serializer.validated_data['operation']
        new_scheduled_time = serializer.validated_data.get('new_scheduled_time')
        completion_notes = serializer.validated_data.get('completion_notes', '')
        user = request.user

        updated_count = 0

        try:
            for activity_id in activity_ids:
                activity = Activity.objects.get(id=activity_id)

                # Check permissions
                if not user.is_admin() and activity.owner != user:
                    continue

                if operation == 'complete':
                    self.service.complete_activity(activity_id, completion_notes, user.id)
                    updated_count += 1
                elif operation == 'cancel':
                    self.service.cancel_activity(activity_id, user.id)
                    updated_count += 1
                elif operation == 'reschedule' and new_scheduled_time:
                    new_time = datetime.fromisoformat(new_scheduled_time.replace('Z', '+00:00'))
                    self.service.reschedule_activity(activity_id, new_time, user.id)
                    updated_count += 1
                elif operation == 'delete':
                    activity.delete()
                    updated_count += 1

            return Response({
                'message': f'Bulk {operation} completed successfully',
                'updated_count': updated_count
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Get upcoming activities
        Following Single Responsibility Principle
        """
        user = request.user
        days = int(request.query_params.get('days', 7))

        cutoff_time = timezone.now() + timedelta(days=days)
        queryset = self.get_queryset().filter(
            scheduled_at__gte=timezone.now(),
            scheduled_at__lte=cutoff_time,
            is_completed=False,
            is_cancelled=False
        ).order_by('scheduled_at')

        serializer = ActivitySummarySerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """
        Get overdue activities
        Following Single Responsibility Principle
        """
        user = request.user
        queryset = self.get_queryset().filter(
            scheduled_at__lt=timezone.now(),
            is_completed=False,
            is_cancelled=False
        ).order_by('scheduled_at')

        serializer = ActivitySummarySerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """
        Get activities for today
        Following Single Responsibility Principle
        """
        user = request.user
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        queryset = self.get_queryset().filter(
            scheduled_at__gte=today_start,
            scheduled_at__lt=today_end,
            is_cancelled=False
        ).order_by('scheduled_at')

        serializer = ActivitySummarySerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def this_week(self, request):
        """
        Get activities for this week
        Following Single Responsibility Principle
        """
        user = request.user
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_start = timezone.make_aware(datetime.combine(week_start, datetime.min.time()))
        week_end = week_start + timedelta(days=7)

        queryset = self.get_queryset().filter(
            scheduled_at__gte=week_start,
            scheduled_at__lt=week_end,
            is_cancelled=False
        ).order_by('scheduled_at')

        serializer = ActivitySummarySerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get activity statistics for the current user
        Following Single Responsibility Principle
        """
        user = request.user
        queryset = self.get_queryset()

        # Basic statistics
        total_activities = queryset.count()
        completed_activities = queryset.filter(is_completed=True).count()
        pending_activities = queryset.filter(is_completed=False, is_cancelled=False).count()
        cancelled_activities = queryset.filter(is_cancelled=True).count()
        overdue_activities = queryset.filter(
            scheduled_at__lt=timezone.now(),
            is_completed=False,
            is_cancelled=False
        ).count()

        # Completion rate
        completion_rate = (completed_activities / total_activities * 100) if total_activities > 0 else 0

        # Activities by type
        activities_by_type = {}
        for activity_type in Activity.ACTIVITY_TYPES:
            type_name = activity_type[0]
            type_display = activity_type[1]
            count = queryset.filter(type=type_name).count()
            activities_by_type[type_name] = {
                'display': type_display,
                'count': count
            }

        # Activities by priority
        activities_by_priority = {}
        for priority_choice in Activity.PRIORITY_CHOICES:
            priority_name = priority_choice[0]
            priority_display = priority_choice[1]
            count = queryset.filter(priority=priority_name).count()
            activities_by_priority[priority_name] = {
                'display': priority_display,
                'count': count
            }

        # Activities this week and month
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        activities_this_week = queryset.filter(
            scheduled_at__date__gte=week_start,
            scheduled_at__date__lte=today
        ).count()

        activities_this_month = queryset.filter(
            scheduled_at__date__gte=month_start,
            scheduled_at__date__lte=today
        ).count()

        return Response({
            'total_activities': total_activities,
            'completed_activities': completed_activities,
            'pending_activities': pending_activities,
            'cancelled_activities': cancelled_activities,
            'overdue_activities': overdue_activities,
            'completion_rate': round(completion_rate, 2),
            'activities_by_type': activities_by_type,
            'activities_by_priority': activities_by_priority,
            'activities_this_week': activities_this_week,
            'activities_this_month': activities_this_month
        })

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """
        Get activities for calendar view
        Following Single Responsibility Principle
        """
        user = request.user
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            raise ValidationError('Both start_date and end_date are required.')

        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError('Invalid date format. Use ISO format.')

        if start_dt >= end_dt:
            raise ValidationError('End date must be after start date.')

        # Limit to 1 year
        if (end_dt - start_dt).days > 365:
            raise ValidationError('Date range cannot exceed 1 year.')

        queryset = self.get_queryset().filter(
            scheduled_at__gte=start_dt,
            scheduled_at__lte=end_dt,
            is_cancelled=False
        ).order_by('scheduled_at')

        # Return simplified calendar data
        calendar_data = []
        for activity in queryset:
            calendar_data.append({
                'id': activity.id,
                'title': activity.title,
                'start': activity.scheduled_at.isoformat(),
                'type': activity.type,
                'priority': activity.priority,
                'is_completed': activity.is_completed,
                'contact_name': activity.contact.full_name if activity.contact else None,
                'deal_title': activity.deal.title if activity.deal else None
            })

        return Response({
            'start_date': start_date,
            'end_date': end_date,
            'activities': calendar_data
        })

    @action(detail=False, methods=['get'])
    def by_contact(self, request):
        """
        Get activities by contact
        Following Single Responsibility Principle
        """
        user = request.user
        contact_id = request.query_params.get('contact_id')

        if not contact_id:
            raise ValidationError('Contact ID is required.')

        try:
            contact = Contact.objects.get(id=contact_id)

            # Check permissions
            if not user.is_admin() and contact.owner != user:
                raise PermissionDenied("You don't have permission to view activities for this contact.")

            queryset = self.get_queryset().filter(contact=contact).order_by('-scheduled_at')
            serializer = ActivitySummarySerializer(queryset, many=True)
            return Response(serializer.data)
        except Contact.DoesNotExist:
            raise NotFound('Contact not found.')

    @action(detail=False, methods=['get'])
    def by_deal(self, request):
        """
        Get activities by deal
        Following Single Responsibility Principle
        """
        user = request.user
        deal_id = request.query_params.get('deal_id')

        if not deal_id:
            raise ValidationError('Deal ID is required.')

        try:
            deal = Deal.objects.get(id=deal_id)

            # Check permissions
            if not user.is_admin() and deal.owner != user:
                raise PermissionDenied("You don't have permission to view activities for this deal.")

            queryset = self.get_queryset().filter(deal=deal).order_by('-scheduled_at')
            serializer = ActivitySummarySerializer(queryset, many=True)
            return Response(serializer.data)
        except Deal.DoesNotExist:
            raise NotFound('Deal not found.')

    def create(self, request, *args, **kwargs):
        """
        Override create to handle business logic properly
        Following SOLID principles
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            activity = self.perform_create(serializer)
            response_serializer = ActivityDetailSerializer(activity)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            raise ValidationError(str(e))

    def update(self, request, *args, **kwargs):
        """
        Override update to handle business logic properly
        Following SOLID principles
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            activity = self.perform_update(serializer)
            response_serializer = ActivityDetailSerializer(activity)
            return Response(response_serializer.data)
        except Exception as e:
            raise ValidationError(str(e))


class ActivityCommentViewSet(viewsets.ModelViewSet):
    """
    ActivityComment ViewSet for activity comment management
    Following SOLID principles and clean architecture
    """

    serializer_class = ActivityCommentSerializer
    permission_classes = [ActivityPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['activity']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Get comments based on user permissions
        Following SOLID principles for access control
        """
        user = self.request.user

        if user.is_admin():
            return ActivityComment.objects.all()

        # Get activities user has access to and their comments
        accessible_activities = Activity.objects.filter(
            Q(owner=user) | (Q(owner__role='manager') & Q(owner=user))
        )

        return ActivityComment.objects.filter(activity__in=accessible_activities)

    def perform_create(self, serializer):
        """
        Handle comment creation with proper user assignment
        Following SOLID principles
        """
        # Set author to current user if not already set
        if not serializer.validated_data.get('author'):
            serializer.validated_data['author'] = self.request.user

        serializer.save()

    def get_object(self):
        """
        Get comment with permission checking
        Following SOLID principles for proper access control
        """
        pk = self.kwargs.get('pk')
        try:
            comment = ActivityComment.objects.get(pk=pk)
        except ActivityComment.DoesNotExist:
            raise NotFound('Comment not found.')

        # Check permissions through activity
        user = self.request.user
        if not user.is_admin() and comment.activity.owner != user:
            raise NotFound('Comment not found.')

        return comment