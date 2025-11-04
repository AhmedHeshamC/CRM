"""
Deal API Views
Following SOLID and KISS principles
Single Responsibility: Each view handles one specific use case
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Deal
from .serializers import SimpleDealSerializer


class DealListCreateView(generics.ListCreateAPIView):
    """
    Handle deal listing and creation
    Single Responsibility: Deal list and creation management
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SimpleDealSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['stage', 'currency', 'contact']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'value', 'expected_close_date']
    ordering = ['-created_at']

    def get_queryset(self):
        """Only return deals for the authenticated user"""
        return Deal.objects.filter(owner=self.request.user)

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


class DealDetailView(generics.RetrieveUpdateAPIView):
    """
    Handle deal detail operations
    Single Responsibility: Individual deal management
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SimpleDealSerializer

    def get_queryset(self):
        """Only return deals for the authenticated user"""
        return Deal.objects.filter(owner=self.request.user)