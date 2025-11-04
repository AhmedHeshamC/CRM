"""
Contact API Views
Following SOLID and KISS principles
Single Responsibility: Each view handles one specific use case
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Contact
from .serializers import SimpleContactSerializer


class ContactListCreateView(generics.ListCreateAPIView):
    """
    Handle contact listing and creation
    Single Responsibility: Contact list and creation management
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SimpleContactSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'company', 'tags']
    search_fields = ['first_name', 'last_name', 'email', 'company']
    ordering_fields = ['created_at', 'last_name', 'first_name']
    ordering = ['-created_at']

    def get_queryset(self):
        """Only return contacts for the authenticated user"""
        return Contact.objects.filter(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        """Override list to add pagination metadata"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'count': len(serializer.data)
        })


class ContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Handle contact detail operations
    Single Responsibility: Individual contact management
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SimpleContactSerializer

    def get_queryset(self):
        """Only return contacts for the authenticated user"""
        return Contact.objects.filter(owner=self.request.user)

    def perform_destroy(self, instance):
        """Override to implement soft delete"""
        instance.delete()  # This calls the soft delete method