"""
Base Repository - KISS Implementation
Simple foundation following SOLID Single Responsibility Principle
"""

from django.db import models


class BaseRepository:
    """
    Simple Base Repository - Following KISS principle
    Provides basic CRUD operations without over-engineering
    """

    def __init__(self, model=None):
        """Initialize with model class"""
        self.model = model

    def get_by_id(self, id):
        """Get single record by ID"""
        try:
            return self.model.objects.get(id=id)
        except self.model.DoesNotExist:
            return None

    def get_all(self):
        """Get all records"""
        return self.model.objects.all()

    def create(self, **kwargs):
        """Create new record"""
        return self.model.objects.create(**kwargs)

    def update(self, instance, **kwargs):
        """Update existing record"""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, instance):
        """Delete record (hard delete)"""
        instance.delete()

    def soft_delete(self, instance):
        """Soft delete if model supports it"""
        if hasattr(instance, 'is_deleted'):
            instance.is_deleted = True
            instance.save()
        else:
            self.delete(instance)

    def filter(self, **kwargs):
        """Filter records"""
        return self.model.objects.filter(**kwargs)

    def exists(self, **kwargs):
        """Check if record exists"""
        return self.model.objects.filter(**kwargs).exists()

    def count(self, **kwargs):
        """Count records"""
        return self.model.objects.filter(**kwargs).count()