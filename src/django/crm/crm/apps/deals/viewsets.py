"""
Deal ViewSets - API Endpoint Layer
Following SOLID principles and enterprise best practices
"""

from decimal import Decimal
from datetime import date, datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from .models import Deal, DealStageHistory
from .serializers import (
    DealSerializer, DealDetailSerializer, DealCreateSerializer,
    DealUpdateSerializer, DealSummarySerializer,
    DealStageHistorySerializer, DealBulkOperationSerializer,
    DealPipelineStatisticsSerializer, DealForecastSerializer
)
from ..shared.repositories.deal_repository import DealRepository
from ..shared.services.deal_service import DealService
from crm.apps.contacts.models import Contact
from ...shared.authentication.permissions import DealPermission, IsAdminUser

User = get_user_model()


class DealViewSet(viewsets.ModelViewSet):
    """
    Deal ViewSet for comprehensive deal management
    Following SOLID principles and clean architecture
    """

    # Repository and Service layers
    repository = DealRepository()
    service = DealService(repository)

    # Permission and authentication
    permission_classes = [DealPermission]

    # Filtering and searching
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['stage', 'currency', 'contact', 'owner']
    search_fields = ['title', 'description', 'contact__first_name', 'contact__last_name', 'contact__company']
    ordering_fields = ['title', 'value', 'stage', 'probability', 'expected_close_date', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Get deals based on user permissions
        Following SOLID principles for access control
        """
        user = self.request.user

        # Admin users can see all deals
        if user.is_admin():
            return Deal.objects.all()

        # Managers can see deals of their team (implementation depends on requirements)
        # For now, managers see their own deals
        if user.is_manager():
            return Deal.objects.filter(owner=user)

        # Regular users only see their own deals
        return Deal.objects.filter(owner=user)

    def get_serializer_class(self):
        """
        Select appropriate serializer based on action
        Following Single Responsibility Principle
        """
        if self.action == 'create':
            return DealCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return DealUpdateSerializer
        elif self.action == 'retrieve':
            return DealDetailSerializer
        elif self.action == 'list':
            return DealSummarySerializer
        return DealSerializer

    def perform_create(self, serializer):
        """
        Handle deal creation with business logic
        Following SOLID principles for clean business logic separation
        """
        user = self.request.user
        validated_data = serializer.validated_data.copy()

        # Set owner to current user if not specified
        if 'owner' not in validated_data:
            validated_data['owner'] = user

        # Validate business rules
        try:
            deal = self.service.create_deal(validated_data, user.id)
            return deal
        except Exception as e:
            raise ValidationError(str(e))

    def perform_update(self, serializer):
        """
        Handle deal update with business logic
        Following SOLID principles for clean business logic separation
        """
        user = self.request.user
        deal_id = self.get_object().id
        validated_data = serializer.validated_data.copy()

        try:
            deal = self.service.update_deal(deal_id, validated_data, user.id)
            return deal
        except Exception as e:
            raise ValidationError(str(e))

    def get_object(self):
        """
        Get deal with permission checking
        Following SOLID principles for proper access control
        """
        pk = self.kwargs.get('pk')
        try:
            deal = Deal.objects.get(pk=pk)
        except Deal.DoesNotExist:
            raise NotFound('Deal not found.')

        # Check permissions
        user = self.request.user
        if not user.is_admin() and deal.owner != user:
            raise NotFound('Deal not found.')

        return deal

    def list(self, request, *args, **kwargs):
        """
        List deals with enhanced filtering and pagination
        Following KISS principle for clean, readable implementation
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Custom filtering logic
        stage = request.query_params.get('stage')
        if stage:
            queryset = queryset.filter(stage=stage)

        currency = request.query_params.get('currency')
        if currency:
            queryset = queryset.filter(currency=currency)

        value_min = request.query_params.get('value_min')
        if value_min:
            try:
                queryset = queryset.filter(value__gte=Decimal(value_min))
            except ValueError:
                pass

        value_max = request.query_params.get('value_max')
        if value_max:
            try:
                queryset = queryset.filter(value__lte=Decimal(value_max))
            except ValueError:
                pass

        # Date filtering
        created_after = request.query_params.get('created_after')
        if created_after:
            try:
                date_obj = datetime.strptime(created_after, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_obj)
            except ValueError:
                pass

        created_before = request.query_params.get('created_before')
        if created_before:
            try:
                date_obj = datetime.strptime(created_before, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_obj)
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
    def change_stage(self, request, pk=None):
        """
        Change deal stage with tracking
        Following Single Responsibility Principle
        """
        deal = self.get_object()
        user = request.user
        new_stage = request.data.get('new_stage')
        notes = request.data.get('notes', '')

        if not new_stage:
            raise ValidationError('New stage is required.')

        # Validate stage transition
        if not deal.can_transition_to(new_stage):
            raise ValidationError(f'Cannot transition from {deal.stage} to {new_stage}.')

        try:
            # Track stage change
            DealStageHistory.objects.create(
                deal=deal,
                old_stage=deal.stage,
                new_stage=new_stage,
                changed_by=user
            )

            # Update deal
            deal.stage = new_stage
            deal._changed_by_user = user  # For stage history tracking
            deal.save()

            return Response({
                'message': 'Deal stage updated successfully',
                'old_stage': deal.stage,
                'new_stage': new_stage,
                'deal_id': deal.id
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """
        Close deal as won or lost
        Following Single Responsibility Principle
        """
        deal = self.get_object()
        user = request.user
        outcome = request.data.get('outcome')  # 'won' or 'lost'
        final_value = request.data.get('final_value')
        notes = request.data.get('notes', '')

        if outcome not in ['won', 'lost']:
            raise ValidationError('Outcome must be either "won" or "lost".')

        try:
            if outcome == 'won':
                if final_value:
                    final_value = Decimal(str(final_value))
                    deal.close_as_won(final_value)
                else:
                    deal.close_as_won()
            else:
                deal.close_as_lost(notes)

            return Response({
                'message': f'Deal closed as {outcome} successfully',
                'outcome': outcome,
                'final_value': str(deal.closed_value) if deal.closed_value else None,
                'deal_id': deal.id
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """
        Perform bulk operations on deals
        Following Single Responsibility Principle
        """
        serializer = DealBulkOperationSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        deal_ids = serializer.validated_data['deal_ids']
        operation = serializer.validated_data['operation']
        new_stage = serializer.validated_data.get('new_stage')
        user = request.user

        updated_count = 0

        try:
            for deal_id in deal_ids:
                deal = Deal.objects.get(id=deal_id)

                # Check permissions
                if not user.is_admin() and deal.owner != user:
                    continue

                if operation == 'archive':
                    deal.is_archived = True
                    deal.save()
                    updated_count += 1
                elif operation == 'unarchive':
                    deal.is_archived = False
                    deal.save()
                    updated_count += 1
                elif operation == 'stage_change' and new_stage:
                    # Track stage change
                    DealStageHistory.objects.create(
                        deal=deal,
                        old_stage=deal.stage,
                        new_stage=new_stage,
                        changed_by=user
                    )
                    deal.stage = new_stage
                    deal._changed_by_user = user
                    deal.save()
                    updated_count += 1
                elif operation == 'delete':
                    deal.delete()
                    updated_count += 1

            return Response({
                'message': f'Bulk {operation} completed successfully',
                'updated_count': updated_count
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['get'])
    def pipeline_statistics(self, request):
        """
        Get pipeline statistics for the current user
        Following Single Responsibility Principle
        """
        user = request.user
        queryset = self.get_queryset()

        # Basic statistics
        total_deals = queryset.count()
        total_value = queryset.aggregate(total=Sum('value'))['total'] or Decimal('0')
        avg_deal_size = queryset.aggregate(avg=Avg('value'))['avg'] or Decimal('0')

        # Win rate calculation
        won_deals = queryset.filter(stage='closed_won').count()
        lost_deals = queryset.filter(stage='closed_lost').count()
        total_closed = won_deals + lost_deals
        win_rate = (won_deals / total_closed * 100) if total_closed > 0 else 0

        # Deals by stage
        deals_by_stage = {}
        for stage_choice in Deal.STAGE_CHOICES:
            stage_name = stage_choice[0]
            stage_display = stage_choice[1]
            count = queryset.filter(stage=stage_name).count()
            value = queryset.filter(stage=stage_name).aggregate(total=Sum('value'))['total'] or Decimal('0')
            deals_by_stage[stage_name] = {
                'display': stage_display,
                'count': count,
                'value': str(value)
            }

        # Average sales cycle (in days)
        closed_deals_with_dates = queryset.filter(
            stage__in=['closed_won', 'closed_lost'],
            closed_date__isnull=False
        )
        avg_sales_cycle = 0
        if closed_deals_with_dates.exists():
            total_cycle_days = sum(
                (deal.closed_date.date() - deal.created_at.date()).days
                for deal in closed_deals_with_dates
            )
            avg_sales_cycle = total_cycle_days // closed_deals_with_dates.count()

        # Deals by month (last 6 months)
        deals_by_month = {}
        for i in range(6):
            month_date = date.today().replace(day=1) - timedelta(days=i*30)
            month_str = month_date.strftime('%Y-%m')
            month_deals = queryset.filter(created_at__year=month_date.year, created_at__month=month_date.month)
            deals_by_month[month_str] = {
                'count': month_deals.count(),
                'value': str(month_deals.aggregate(total=Sum('value'))['total'] or Decimal('0'))
            }

        # Top performing stages (by conversion rate)
        top_performing_stages = []
        for stage_name, stage_data in deals_by_stage.items():
            if stage_name not in ['closed_won', 'closed_lost']:
                conversion_data = self._calculate_stage_conversion_rate(queryset, stage_name)
                top_performing_stages.append({
                    'stage': stage_name,
                    'display': stage_data['display'],
                    'conversion_rate': conversion_data['conversion_rate'],
                    'total_deals': conversion_data['total_deals'],
                    'won_deals': conversion_data['won_deals']
                })

        # Sort by conversion rate
        top_performing_stages.sort(key=lambda x: x['conversion_rate'], reverse=True)

        return Response({
            'total_deals': total_deals,
            'total_value': str(total_value),
            'average_deal_size': str(avg_deal_size),
            'win_rate': round(win_rate, 2),
            'average_sales_cycle': avg_sales_cycle,
            'deals_by_stage': deals_by_stage,
            'deals_by_month': deals_by_month,
            'top_performing_stages': top_performing_stages[:5]  # Top 5
        })

    def _calculate_stage_conversion_rate(self, queryset, stage_name):
        """Helper method to calculate conversion rate for a stage"""
        stage_deals = queryset.filter(stage=stage_name)
        total_stage_deals = stage_deals.count()

        if total_stage_deals == 0:
            return {'conversion_rate': 0, 'total_deals': 0, 'won_deals': 0}

        # Find deals that moved from this stage to closed_won
        stage_transitions = DealStageHistory.objects.filter(
            old_stage=stage_name,
            deal__in=stage_deals
        )

        # Get deals that eventually won
        won_deal_ids = Deal.objects.filter(
            stage='closed_won',
            id__in=stage_transitions.values('deal_id')
        ).values_list('id', flat=True)

        won_count = len(set(won_deal_ids))
        conversion_rate = (won_count / total_stage_deals) * 100 if total_stage_deals > 0 else 0

        return {
            'conversion_rate': round(conversion_rate, 2),
            'total_deals': total_stage_deals,
            'won_deals': won_count
        }

    @action(detail=False, methods=['get'])
    def forecast(self, request):
        """
        Get sales forecast for specified period
        Following Single Responsibility Principle
        """
        user = request.user
        period = request.query_params.get('period', 'current_quarter')
        queryset = self.get_queryset()

        # Calculate date range based on period
        today = date.today()
        if period == 'current_month':
            start_date = today.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        elif period == 'current_quarter':
            quarter = (today.month - 1) // 3 + 1
            start_date = date(today.year, (quarter - 1) * 3 + 1, 1)
            if quarter == 4:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, quarter * 3 + 1, 1) - timedelta(days=1)
        elif period == 'current_year':
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        elif period == 'next_month':
            next_month = today.replace(day=28) + timedelta(days=4)  # Go to next month
            start_date = next_month.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        elif period == 'next_quarter':
            quarter = (today.month - 1) // 3 + 1
            if quarter == 4:
                start_date = date(today.year + 1, 1, 1)
                end_date = date(today.year + 1, 3, 31)
            else:
                start_date = date(today.year, quarter * 3 + 1, 1)
                if quarter + 1 == 4:
                    end_date = date(today.year, 12, 31)
                else:
                    end_date = date(today.year, (quarter + 1) * 3, 30)
        else:  # next_year
            start_date = date(today.year + 1, 1, 1)
            end_date = date(today.year + 1, 12, 31)

        # Filter deals by expected close date in period
        period_deals = queryset.filter(
            expected_close_date__range=[start_date, end_date],
            stage__in=['prospect', 'qualified', 'proposal', 'negotiation']
        )

        # Calculate forecast metrics
        deals_count = period_deals.count()
        forecast_value = period_deals.aggregate(total=Sum('value'))['total'] or Decimal('0')

        # Weighted value based on probability
        weighted_value = sum(
            deal.value * (deal.probability / 100)
            for deal in period_deals
        )

        # Confidence level based on deal stages and probabilities
        if deals_count == 0:
            confidence_level = 0
        else:
            avg_probability = period_deals.aggregate(avg=Avg('probability'))['avg'] or 0
            # Adjust confidence based on stage distribution
            high_confidence_deals = period_deals.filter(stage__in=['negotiation', 'proposal']).count()
            stage_confidence = (high_confidence_deals / deals_count) * 20 if deals_count > 0 else 0
            confidence_level = min(100, avg_probability + stage_confidence)

        # Risk factors
        risk_factors = []

        # Check for high-value, low-probability deals
        risky_deals = period_deals.filter(value__gt=forecast_value / deals_count * 2, probability__lt=30)
        if risky_deals.exists():
            risk_factors.append(f"{risky_deals.count()} high-value, low-probability deals")

        # Check for deals closing soon
        soon_closing = period_deals.filter(
            expected_close_date__lte=today + timedelta(days=7),
            stage__in=['prospect', 'qualified']
        )
        if soon_closing.exists():
            risk_factors.append(f"{soon_closing.count()} deals closing soon with low stage")

        # Check for stale deals
        stale_threshold = today - timedelta(days=90)
        stale_deals = period_deals.filter(created_at__date__lt=stale_threshold)
        if stale_deals.exists():
            risk_factors.append(f"{stale_deals.count()} deals in pipeline for over 90 days")

        return Response({
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'deals_count': deals_count,
            'forecast_value': str(forecast_value),
            'weighted_value': str(round(weighted_value, 2)),
            'confidence_level': round(confidence_level, 2),
            'risk_factors': risk_factors
        })

    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """
        Get activities related to a deal
        Following Single Responsibility Principle
        """
        deal = self.get_object()
        user = request.user

        # Check permissions
        if not user.is_admin() and deal.owner != user:
            raise PermissionDenied("You don't have permission to view activities for this deal.")

        from crm.apps.activities.models import Activity
        activities = Activity.objects.filter(deal=deal).order_by('-created_at')

        # Serialize activities
        from crm.apps.activities.serializers import ActivitySummarySerializer
        serializer = ActivitySummarySerializer(activities, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def closing_soon(self, request):
        """
        Get deals closing within specified days
        Following Single Responsibility Principle
        """
        user = request.user
        days = int(request.query_params.get('days', 30))

        cutoff_date = date.today() + timedelta(days=days)
        queryset = self.get_queryset().filter(
            expected_close_date__lte=cutoff_date,
            expected_close_date__gte=date.today(),
            stage__in=['qualified', 'proposal', 'negotiation']
        ).order_by('expected_close_date')

        serializer = DealSummarySerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stalled(self, request):
        """
        Get stalled deals (no recent activity)
        Following Single Responsibility Principle
        """
        user = request.user
        days = int(request.query_params.get('days', 30))

        cutoff_date = timezone.now() - timedelta(days=days)
        queryset = self.get_queryset().filter(
            updated_at__lt=cutoff_date,
            stage__in=['prospect', 'qualified', 'proposal', 'negotiation']
        ).order_by('updated_at')

        serializer = DealSummarySerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Override create to handle business logic properly
        Following SOLID principles
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            deal = self.perform_create(serializer)
            response_serializer = DealDetailSerializer(deal)
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
            deal = self.perform_update(serializer)
            response_serializer = DealDetailSerializer(deal)
            return Response(response_serializer.data)
        except Exception as e:
            raise ValidationError(str(e))


class DealStageHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    DealStageHistory ViewSet for viewing deal progression
    Following SOLID principles and clean architecture
    """

    serializer_class = DealStageHistorySerializer
    permission_classes = [DealPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['deal', 'old_stage', 'new_stage', 'changed_by']
    ordering = ['-changed_at']

    def get_queryset(self):
        """
        Get stage history based on user permissions
        Following SOLID principles for access control
        """
        user = self.request.user

        if user.is_admin():
            return DealStageHistory.objects.all()

        # Get deals user has access to and their stage history
        accessible_deals = Deal.objects.filter(
            Q(owner=user) | (Q(owner__role='manager') & Q(owner=user))
        )

        return DealStageHistory.objects.filter(deal__in=accessible_deals)