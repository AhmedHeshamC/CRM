"""
Base Service Layer Implementation
Following SOLID principles and enterprise best practices
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseService(Generic[T], ABC):
    """
    Abstract base service implementing common business logic patterns
    Following SOLID principles for clean business logic layer
    """

    def __init__(self, repository):
        """
        Initialize service with repository

        Args:
            repository: Repository instance for data operations
        """
        self.repository = repository
        self.logger = logger

    @abstractmethod
    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data for create operation

        Args:
            data: Input data

        Returns:
            Validated and cleaned data

        Raises:
            ValidationError: If data is invalid
        """
        pass

    @abstractmethod
    def validate_update_data(self, entity_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data for update operation

        Args:
            entity_id: Entity ID
            data: Input data

        Returns:
            Validated and cleaned data

        Raises:
            ValidationError: If data is invalid
            NotFoundError: If entity doesn't exist
        """
        pass

    def create(self, data: Dict[str, Any]) -> T:
        """
        Create new entity with validation

        Args:
            data: Entity data

        Returns:
            Created entity

        Raises:
            ValidationError: If data is invalid
        """
        validated_data = self.validate_create_data(data)
        entity = self.repository.create(**validated_data)
        self.logger.info(f"Created {self.repository.model.__name__} with ID {entity.id}")
        return entity

    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Get entity by ID

        Args:
            entity_id: Entity ID

        Returns:
            Entity instance or None
        """
        return self.repository.get_by_id(entity_id)

    def get_by_uuid(self, uuid: str) -> Optional[T]:
        """
        Get entity by UUID

        Args:
            uuid: Entity UUID

        Returns:
            Entity instance or None
        """
        return self.repository.get_by_uuid(uuid)

    def update(self, entity_id: int, data: Dict[str, Any]) -> Optional[T]:
        """
        Update entity with validation

        Args:
            entity_id: Entity ID
            data: Update data

        Returns:
            Updated entity or None

        Raises:
            ValidationError: If data is invalid
            NotFoundError: If entity doesn't exist
        """
        validated_data = self.validate_update_data(entity_id, data)
        entity = self.repository.update(entity_id, **validated_data)
        if entity:
            self.logger.info(f"Updated {self.repository.model.__name__} with ID {entity_id}")
        return entity

    def delete(self, entity_id: int) -> bool:
        """
        Delete entity by ID

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted, False otherwise
        """
        success = self.repository.delete(entity_id)
        if success:
            self.logger.info(f"Deleted {self.repository.model.__name__} with ID {entity_id}")
        return success

    def list(self, **filters) -> List[T]:
        """
        List entities with optional filters

        Args:
            **filters: Filter criteria

        Returns:
            List of entities
        """
        return self.repository.filter(**filters)

    def get_paginated(self, page: int = 1, per_page: int = 20, **filters) -> Dict[str, Any]:
        """
        Get paginated results

        Args:
            page: Page number
            per_page: Items per page
            **filters: Filter criteria

        Returns:
            Dictionary with pagination info and results
        """
        return self.repository.get_paginated(page, per_page, **filters)


class BusinessLogicError(Exception):
    """Base exception for business logic errors"""
    pass


class ValidationError(BusinessLogicError):
    """Exception raised when data validation fails"""
    pass


class NotFoundError(BusinessLogicError):
    """Exception raised when requested entity is not found"""
    pass


class PermissionError(BusinessLogicError):
    """Exception raised when user doesn't have permission"""
    pass


class ConflictError(BusinessLogicError):
    """Exception raised when business rule conflict occurs"""
    pass