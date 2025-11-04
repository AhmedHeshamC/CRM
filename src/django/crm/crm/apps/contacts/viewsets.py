"""
Contact ViewSets - API Endpoint Layer
Following SOLID principles and enterprise best practices
"""

from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from .models import Contact, ContactInteraction
from .serializers import (
    ContactSerializer, ContactDetailSerializer, ContactCreateSerializer,
    ContactUpdateSerializer, ContactSummarySerializer,
    ContactInteractionSerializer, ContactBulkOperationSerializer
)
from ...shared.repositories.contact_repository import ContactRepository
from ...shared.services.contact_service import ContactService
from ...shared.authentication.permissions import ContactPermission, IsAdminUser

User = get_user_model()


class ContactViewSet(viewsets.ModelViewSet):
    """
    Contact ViewSet for comprehensive contact management
    Following SOLID principles and clean architecture
    """

    # Repository and Service layers
    repository = ContactRepository()
    service = ContactService(repository)

    # Permission and authentication - Use role-based permissions
    permission_classes = [ContactPermission]

    # Filtering and searching
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'is_active', 'lead_source', 'tags']
    search_fields = ['first_name', 'last_name', 'email', 'company']
    ordering_fields = ['first_name', 'last_name', 'company', 'created_at', 'updated_at']
    ordering = ['last_name', 'first_name']

    def get_queryset(self):
        """
        Get contacts based on user permissions
        Following SOLID principles for access control
        """
        user = self.request.user

        # Admin users can see all contacts
        if user.is_admin():
            return Contact.objects.all()

        # Managers can see contacts of their team (implementation depends on requirements)
        # For now, managers see their own contacts
        if user.is_manager():
            return Contact.objects.filter(owner=user)

        # Regular users only see their own contacts
        return Contact.objects.filter(owner=user)

    def get_serializer_class(self):
        """
        Select appropriate serializer based on action
        Following Single Responsibility Principle
        """
        if self.action == 'create':
            return ContactCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return ContactUpdateSerializer
        elif self.action == 'retrieve':
            return ContactDetailSerializer
        elif self.action == 'list':
            return ContactSummarySerializer
        return ContactSerializer

    def perform_create(self, serializer):
        """
        Handle contact creation with business logic
        Following SOLID principles for clean business logic separation
        """
        user = self.request.user
        validated_data = serializer.validated_data.copy()

        # Set owner to current user if not specified
        if 'owner' not in validated_data:
            validated_data['owner'] = user

        # Validate business rules
        try:
            contact = self.service.create_contact(validated_data, user.id)
            return contact
        except Exception as e:
            raise ValidationError(str(e))

    def perform_update(self, serializer):
        """
        Handle contact update with business logic
        Following SOLID principles for clean business logic separation
        """
        user = self.request.user
        contact_id = self.get_object().id
        validated_data = serializer.validated_data.copy()

        try:
            contact = self.service.update_contact(contact_id, validated_data, user.id)
            return contact
        except Exception as e:
            raise ValidationError(str(e))

    def perform_destroy(self, instance):
        """
        Handle soft delete with business logic
        Following SOLID principles for clean business logic separation
        """
        user = self.request.user
        try:
            self.service.soft_delete_contact(instance.id, user.id)
        except Exception as e:
            raise ValidationError(str(e))

    def get_object(self):
        """
        Get contact with permission checking
        Following SOLID principles for proper access control
        """
        pk = self.kwargs.get('pk')
        try:
            contact = Contact.objects.get(pk=pk)
        except Contact.DoesNotExist:
            raise NotFound('Contact not found.')

        # Check permissions
        user = self.request.user
        if not user.is_admin() and contact.owner != user:
            raise NotFound('Contact not found.')

        return contact

    def list(self, request, *args, **kwargs):
        """
        List contacts with enhanced filtering and pagination
        Following KISS principle for clean, readable implementation
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Custom filtering logic
        company = request.query_params.get('company')
        if company:
            queryset = queryset.filter(company__icontains=company)

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        tags = request.query_params.get('tags')
        if tags:
            tag_list = tags.split(',')
            queryset = queryset.filter(tags__overlap=tag_list)

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        Restore soft-deleted contact
        Following Single Responsibility Principle
        """
        contact = self.get_object()
        user = request.user

        if not contact.is_deleted:
            raise ValidationError('Contact is not deleted.')

        try:
            self.service.restore_contact(contact.id, user.id)
            return Response({
                'message': 'Contact restored successfully',
                'contact_id': contact.id
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['get'])
    def deals(self, request, pk=None):
        """
        Get all deals for a specific contact
        Following Single Responsibility Principle
        """
        contact = self.get_object()
        user = request.user

        try:
            deals = self.service.get_contact_deals(contact.id, user.id)

            # Serialize deals
            from crm.apps.deals.serializers import DealSummarySerializer
            serializer = DealSummarySerializer(deals, many=True)
            return Response(serializer.data)
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['post'])
    def update_tags(self, request, pk=None):
        """
        Update contact tags
        Following Single Responsibility Principle
        """
        contact = self.get_object()
        user = request.user
        tags = request.data.get('tags')

        if not isinstance(tags, list):
            raise ValidationError('Tags must be a list.')

        try:
            success = self.service.update_contact_tags(contact.id, tags, user.id)
            if success:
                contact.refresh_from_db()
                return Response({
                    'message': 'Tags updated successfully',
                    'tags': contact.tags
                })
            else:
                raise ValidationError('Failed to update tags.')
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """
        Perform bulk operations on contacts
        Following Single Responsibility Principle
        """
        serializer = ContactBulkOperationSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        contact_ids = serializer.validated_data['contact_ids']
        operation = serializer.validated_data['operation']
        user = request.user

        updated_count = 0

        try:
            for contact_id in contact_ids:
                contact = Contact.objects.get(id=contact_id)

                # Check permissions
                if not user.is_admin() and contact.owner != user:
                    continue

                if operation == 'delete':
                    self.service.soft_delete_contact(contact_id, user.id)
                    updated_count += 1
                elif operation == 'restore':
                    self.service.restore_contact(contact_id, user.id)
                    updated_count += 1
                elif operation == 'activate':
                    contact.is_active = True
                    contact.save()
                    updated_count += 1
                elif operation == 'deactivate':
                    contact.is_active = False
                    contact.save()
                    updated_count += 1

            return Response({
                'message': f'Bulk {operation} completed successfully',
                'updated_count': updated_count
            })
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get contact statistics for the current user
        Following Single Responsibility Principle
        """
        user = request.user
        user_id = user.id if not user.is_admin() else None

        try:
            stats = self.service.get_contact_statistics(user_id)
            return Response(stats)
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recently created contacts
        Following Single Responsibility Principle
        """
        user = request.user
        days = int(request.query_params.get('days', 30))

        try:
            contacts = self.service.get_recent_contacts(user.id, days)
            serializer = ContactSummarySerializer(contacts, many=True)
            return Response(serializer.data)
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['get'])
    def by_company(self, request):
        """
        Get contacts by company name
        Following Single Responsibility Principle
        """
        user = request.user
        company = request.query_params.get('company')

        if not company:
            raise ValidationError('Company parameter is required.')

        try:
            contacts = self.service.get_contacts_by_company(user.id, company)
            serializer = ContactSummarySerializer(contacts, many=True)
            return Response(serializer.data)
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search contacts with comprehensive query
        Following Single Responsibility Principle
        """
        user = request.user
        query = request.query_params.get('q')

        if not query:
            raise ValidationError('Search query parameter "q" is required.')

        try:
            contacts = self.service.search_user_contacts(user.id, query)
            serializer = ContactSummarySerializer(contacts, many=True)
            return Response(serializer.data)
        except Exception as e:
            raise ValidationError(str(e))

    @action(detail=True, methods=['get', 'post'])
    def interactions(self, request, pk=None):
        """
        Get or create interactions for a contact
        Following Single Responsibility Principle
        """
        contact = self.get_object()

        if request.method == 'GET':
            interactions = ContactInteraction.objects.filter(contact=contact).order_by('-created_at')
            serializer = ContactInteractionSerializer(interactions, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            data = request.data.copy()
            data['contact'] = contact.id
            data['created_by'] = request.user.id

            serializer = ContactInteractionSerializer(data=data)
            if serializer.is_valid():
                interaction = serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                raise ValidationError(serializer.errors)

    def create(self, request, *args, **kwargs):
        """
        Override create to handle business logic properly
        Following SOLID principles
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            contact = self.perform_create(serializer)
            response_serializer = ContactDetailSerializer(contact)
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
            contact = self.perform_update(serializer)
            response_serializer = ContactDetailSerializer(contact)
            return Response(response_serializer.data)
        except Exception as e:
            raise ValidationError(str(e))

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to handle soft delete properly
        Following SOLID principles
        """
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            raise ValidationError(str(e))


class ContactInteractionViewSet(viewsets.ModelViewSet):
    """
    ContactInteraction ViewSet for interaction management
    Following SOLID principles and clean architecture
    """

    serializer_class = ContactInteractionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['interaction_type', 'contact']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Get interactions based on user permissions
        Following SOLID principles for access control
        """
        user = self.request.user

        if user.is_admin():
            return ContactInteraction.objects.all()

        # Get contacts user has access to
        accessible_contacts = Contact.objects.filter(
            Q(owner=user) | (Q(owner__role='manager') & Q(owner=user))
        )

        return ContactInteraction.objects.filter(contact__in=accessible_contacts)

    def perform_create(self, serializer):
        """
        Handle interaction creation with proper user assignment
        Following SOLID principles
        """
        # Set created_by to current user if not already set
        if not serializer.validated_data.get('created_by'):
            serializer.validated_data['created_by'] = self.request.user

        serializer.save()

    def get_object(self):
        """
        Get interaction with permission checking
        Following SOLID principles for proper access control
        """
        pk = self.kwargs.get('pk')
        try:
            interaction = ContactInteraction.objects.get(pk=pk)
        except ContactInteraction.DoesNotExist:
            raise NotFound('Interaction not found.')

        # Check permissions through contact
        user = self.request.user
        if not user.is_admin() and interaction.contact.owner != user:
            raise NotFound('Interaction not found.')

        return interaction