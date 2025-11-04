"""
Activity API Views
Following SOLID and KISS principles
Single Responsibility: Each view handles one specific use case
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Activity
from .serializers import SimpleActivitySerializer


class ActivityListCreateView(generics.ListCreateAPIView):
    """
    Handle activity listing and creation
    Single Responsibility: Activity list and creation management
    KISS Principle: Simple, focused implementation
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SimpleActivitySerializer

    def get_queryset(self):
        """Only return activities for the authenticated user"""
        return Activity.objects.filter(owner=self.request.user)

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


class ActivityDetailView(generics.RetrieveUpdateAPIView):
    """
    Handle activity detail operations
    Single Responsibility: Individual activity management
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SimpleActivitySerializer

    def get_queryset(self):
        """Only return activities for the authenticated user"""
        return Activity.objects.filter(owner=self.request.user)