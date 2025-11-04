"""
Base Repository Pattern Implementation
Following SOLID principles and enterprise best practices
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any
from django.db import models
from django.core.paginator import Paginator
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=models.Model)


class BaseRepository(Generic[T], ABC):
    """
    Abstract base repository implementing Repository Pattern
    Following SOLID principles for clean data access layer
    """

    def __init__(self, model: type[T], cache_timeout: int = 300):
        """
        Initialize repository with model class and cache timeout

        Args:
            model: Django model class
            cache_timeout: Cache timeout in seconds
        """
        self.model = model
        self.cache_timeout = cache_timeout
        self.cache_prefix = f"{model._meta.model_name}_"

    def get_cache_key(self, key: str) -> str:
        """Generate cache key with prefix"""
        return f"{self.cache_prefix}{key}"

    def get_by_id(self, id: int, use_cache: bool = True) -> Optional[T]:
        """
        Get entity by ID with optional caching

        Args:
            id: Entity ID
            use_cache: Whether to use cache

        Returns:
            Entity instance or None
        """
        cache_key = self.get_cache_key(f"id_{id}")

        if use_cache:
            cached_entity = cache.get(cache_key)
            if cached_entity:
                logger.debug(f"Cache hit for {self.model.__name__} ID {id}")
                return cached_entity

        try:
            entity = self.model.objects.get(id=id)
            if use_cache:
                cache.set(cache_key, entity, self.cache_timeout)
            return entity
        except self.model.DoesNotExist:
            logger.debug(f"{self.model.__name__} with ID {id} not found")
            return None

    def get_by_uuid(self, uuid: str, use_cache: bool = True) -> Optional[T]:
        """
        Get entity by UUID with optional caching

        Args:
            uuid: Entity UUID
            use_cache: Whether to use cache

        Returns:
            Entity instance or None
        """
        cache_key = self.get_cache_key(f"uuid_{uuid}")

        if use_cache:
            cached_entity = cache.get(cache_key)
            if cached_entity:
                logger.debug(f"Cache hit for {self.model.__name__} UUID {uuid}")
                return cached_entity

        try:
            entity = self.model.objects.get(uuid=uuid)
            if use_cache:
                cache.set(cache_key, entity, self.cache_timeout)
            return entity
        except (self.model.DoesNotExist, AttributeError):
            logger.debug(f"{self.model.__name__} with UUID {uuid} not found")
            return None

    def get_all(self, use_cache: bool = False) -> List[T]:
        """
        Get all entities

        Args:
            use_cache: Whether to use cache (disabled by default for large datasets)

        Returns:
            List of entities
        """
        cache_key = self.get_cache_key("all")

        if use_cache:
            cached_entities = cache.get(cache_key)
            if cached_entities:
                logger.debug(f"Cache hit for all {self.model.__name__} entities")
                return cached_entities

        entities = list(self.model.objects.all())
        if use_cache:
            cache.set(cache_key, entities, self.cache_timeout)
        return entities

    def filter(self, **kwargs) -> models.QuerySet[T]:
        """
        Filter entities with given criteria

        Args:
            **kwargs: Filter criteria

        Returns:
            QuerySet of filtered entities
        """
        return self.model.objects.filter(**kwargs)

    def create(self, **kwargs) -> T:
        """
        Create new entity

        Args:
            **kwargs: Entity data

        Returns:
            Created entity
        """
        entity = self.model.objects.create(**kwargs)
        self._invalidate_cache_pattern(f"id_{entity.id}")
        self._invalidate_cache_pattern("all")
        logger.info(f"Created {self.model.__name__} with ID {entity.id}")
        return entity

    def update(self, id: int, **kwargs) -> Optional[T]:
        """
        Update entity by ID

        Args:
            id: Entity ID
            **kwargs: Update data

        Returns:
            Updated entity or None
        """
        try:
            entity = self.model.objects.get(id=id)
            for key, value in kwargs.items():
                setattr(entity, key, value)
            entity.save()

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{id}")
            if hasattr(entity, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{entity.uuid}")
            self._invalidate_cache_pattern("all")

            logger.info(f"Updated {self.model.__name__} with ID {id}")
            return entity
        except self.model.DoesNotExist:
            logger.warning(f"Failed to update {self.model.__name__} with ID {id}: Not found")
            return None

    def delete(self, id: int) -> bool:
        """
        Delete entity by ID

        Args:
            id: Entity ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            entity = self.model.objects.get(id=id)
            entity.delete()

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{id}")
            if hasattr(entity, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{entity.uuid}")
            self._invalidate_cache_pattern("all")

            logger.info(f"Deleted {self.model.__name__} with ID {id}")
            return True
        except self.model.DoesNotExist:
            logger.warning(f"Failed to delete {self.model.__name__} with ID {id}: Not found")
            return False

    def bulk_create(self, entities: List[Dict[str, Any]]) -> List[T]:
        """
        Bulk create entities

        Args:
            entities: List of entity data dictionaries

        Returns:
            List of created entities
        """
        created_entities = self.model.objects.bulk_create([
            self.model(**entity_data) for entity_data in entities
        ])

        # Invalidate cache
        self._invalidate_cache_pattern("all")

        logger.info(f"Bulk created {len(created_entities)} {self.model.__name__} entities")
        return created_entities

    def bulk_update(self, entities: List[T], fields: List[str]) -> int:
        """
        Bulk update entities

        Args:
            entities: List of entity instances
            fields: List of fields to update

        Returns:
            Number of updated entities
        """
        updated_count = self.model.objects.bulk_update(entities, fields)

        # Invalidate cache
        self._invalidate_cache_pattern("all")
        for entity in entities:
            self._invalidate_cache_pattern(f"id_{entity.id}")
            if hasattr(entity, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{entity.uuid}")

        logger.info(f"Bulk updated {updated_count} {self.model.__name__} entities")
        return updated_count

    def exists(self, **kwargs) -> bool:
        """
        Check if entity exists with given criteria

        Args:
            **kwargs: Filter criteria

        Returns:
            True if entity exists, False otherwise
        """
        return self.model.objects.filter(**kwargs).exists()

    def count(self, **kwargs) -> int:
        """
        Count entities with given criteria

        Args:
            **kwargs: Filter criteria

        Returns:
            Count of entities
        """
        return self.model.objects.filter(**kwargs).count()

    def get_paginated(self, page: int = 1, per_page: int = 20, **kwargs) -> Dict[str, Any]:
        """
        Get paginated results

        Args:
            page: Page number
            per_page: Items per page
            **kwargs: Filter criteria

        Returns:
            Dictionary with pagination info and results
        """
        queryset = self.filter(**kwargs)
        paginator = Paginator(queryset, per_page)

        try:
            page_obj = paginator.page(page)
        except:
            page_obj = paginator.page(1)

        return {
            'results': list(page_obj.object_list),
            'pagination': {
                'page': page_obj.number,
                'per_page': per_page,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }

    def _invalidate_cache_pattern(self, pattern: str):
        """
        Invalidate cache keys matching pattern

        Args:
            pattern: Cache key pattern
        """
        cache_key = self.get_cache_key(pattern)
        cache.delete(cache_key)

    def clear_cache(self):
        """Clear all cache for this repository"""
        # This is a simplified implementation
        # In production, you might want to use cache.delete_many with pattern matching
        self._invalidate_cache_pattern("all")
        logger.info(f"Cleared cache for {self.model.__name__} repository")


class SoftDeleteRepository(BaseRepository[T]):
    """
    Base repository for models with soft delete functionality
    """

    def __init__(self, model: type[T], cache_timeout: int = 300):
        super().__init__(model, cache_timeout)
        self.include_deleted = False

    def get_by_id(self, id: int, use_cache: bool = True, include_deleted: bool = None) -> Optional[T]:
        """Get entity by ID with soft delete support"""
        if include_deleted is None:
            include_deleted = self.include_deleted

        cache_key = self.get_cache_key(f"id_{id}_deleted_{include_deleted}")

        if use_cache:
            cached_entity = cache.get(cache_key)
            if cached_entity:
                return cached_entity

        try:
            if include_deleted:
                entity = self.model.objects_with_deleted.get(id=id)
            else:
                entity = self.model.objects.get(id=id)

            if use_cache:
                cache.set(cache_key, entity, self.cache_timeout)
            return entity
        except self.model.DoesNotExist:
            return None

    def soft_delete(self, id: int) -> bool:
        """
        Soft delete entity by ID

        Args:
            id: Entity ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            entity = self.model.objects.get(id=id)
            if hasattr(entity, 'delete'):
                entity.delete()  # This should be the soft delete method
            else:
                entity.is_deleted = True
                entity.save()

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{id}")
            if hasattr(entity, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{entity.uuid}")
            self._invalidate_cache_pattern("all")

            logger.info(f"Soft deleted {self.model.__name__} with ID {id}")
            return True
        except self.model.DoesNotExist:
            logger.warning(f"Failed to soft delete {self.model.__name__} with ID {id}: Not found")
            return False

    def restore(self, id: int) -> bool:
        """
        Restore soft-deleted entity

        Args:
            id: Entity ID

        Returns:
            True if restored, False otherwise
        """
        try:
            entity = self.model.objects_with_deleted.get(id=id)
            if hasattr(entity, 'restore'):
                entity.restore()
            else:
                entity.is_deleted = False
                entity.save()

            # Invalidate cache
            self._invalidate_cache_pattern(f"id_{id}")
            if hasattr(entity, 'uuid'):
                self._invalidate_cache_pattern(f"uuid_{entity.uuid}")
            self._invalidate_cache_pattern("all")

            logger.info(f"Restored {self.model.__name__} with ID {id}")
            return True
        except self.model.DoesNotExist:
            logger.warning(f"Failed to restore {self.model.__name__} with ID {id}: Not found")
            return False

    def get_deleted(self, **kwargs) -> List[T]:
        """Get only deleted entities"""
        if hasattr(self.model, 'objects_with_deleted'):
            return list(self.model.objects_with_deleted.filter(is_deleted=True, **kwargs))
        else:
            return list(self.model.objects.filter(is_deleted=True, **kwargs))