"""
Base Repository Tests - Test-Driven Development Approach
Following enterprise-grade testing standards with comprehensive coverage
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import models
import uuid

from crm.shared.repositories.base import BaseRepository, SoftDeleteRepository

User = get_user_model()


class TestModel(models.Model):
    """Test model for repository testing"""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'test'


class BaseRepositoryTest(TestCase):
    """Test BaseRepository following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.repository = BaseRepository(TestModel)
        self.test_data = {
            'name': 'Test Entity',
            'email': 'test@example.com',
            'is_active': True
        }

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()

    def test_repository_initialization(self):
        """Test repository initialization"""
        # Assert
        self.assertEqual(self.repository.model, TestModel)
        self.assertEqual(self.repository.cache_timeout, 300)
        self.assertEqual(self.repository.cache_prefix, 'testmodel_')

    def test_get_cache_key_generation(self):
        """Test cache key generation"""
        # Act
        cache_key = self.repository.get_cache_key("test_key")

        # Assert
        self.assertEqual(cache_key, "testmodel_test_key")

    @patch('crm.shared.repositories.base.cache')
    def test_get_by_id_cache_hit(self, mock_cache):
        """Test getting entity by ID with cache hit"""
        # Arrange
        mock_entity = Mock()
        mock_cache.get.return_value = mock_entity

        # Act
        result = self.repository.get_by_id(1)

        # Assert
        self.assertEqual(result, mock_entity)
        mock_cache.get.assert_called_once_with('testmodel_id_1')

    @patch('crm.shared.repositories.base.cache')
    @patch.object(TestModel.objects, 'get')
    def test_get_by_id_cache_miss(self, mock_get, mock_cache):
        """Test getting entity by ID with cache miss"""
        # Arrange
        mock_entity = Mock(spec=TestModel)
        mock_entity.id = 1
        mock_cache.get.return_value = None
        mock_get.return_value = mock_entity

        # Act
        result = self.repository.get_by_id(1, use_cache=True)

        # Assert
        self.assertEqual(result, mock_entity)
        mock_cache.get.assert_called_once_with('testmodel_id_1')
        mock_get.assert_called_once_with(id=1)
        mock_cache.set.assert_called_once_with('testmodel_id_1', mock_entity, 300)

    @patch.object(TestModel.objects, 'get')
    def test_get_by_id_not_found(self, mock_get):
        """Test getting entity by ID when not found"""
        # Arrange
        mock_get.side_effect = TestModel.DoesNotExist()

        # Act
        result = self.repository.get_by_id(999)

        # Assert
        self.assertIsNone(result)

    def test_get_by_uuid_with_uuid_attribute(self):
        """Test getting entity by UUID when model has UUID attribute"""
        # Arrange
        test_uuid = str(uuid.uuid4())
        mock_entity = Mock(spec=TestModel)
        mock_entity.uuid = test_uuid

        with patch.object(TestModel.objects, 'get', return_value=mock_entity):
            # Act
            result = self.repository.get_by_uuid(test_uuid)

            # Assert
            self.assertEqual(result, mock_entity)

    def test_get_by_uuid_without_uuid_attribute(self):
        """Test getting entity by UUID when model doesn't have UUID attribute"""
        # Arrange
        test_uuid = str(uuid.uuid4())

        with patch.object(TestModel.objects, 'get', side_effect=TestModel.DoesNotExist()):
            # Act
            result = self.repository.get_by_uuid(test_uuid)

            # Assert
            self.assertIsNone(result)

    @patch('crm.shared.repositories.base.cache')
    def test_get_all_with_cache(self, mock_cache):
        """Test getting all entities with cache"""
        # Arrange
        mock_entities = [Mock(spec=TestModel), Mock(spec=TestModel)]
        mock_cache.get.return_value = mock_entities

        # Act
        result = self.repository.get_all(use_cache=True)

        # Assert
        self.assertEqual(result, mock_entities)
        mock_cache.get.assert_called_once_with('testmodel_all')

    @patch.object(TestModel.objects, 'all')
    def test_get_all_without_cache(self, mock_all):
        """Test getting all entities without cache"""
        # Arrange
        mock_entities = [Mock(spec=TestModel), Mock(spec=TestModel)]
        mock_all.return_value = mock_entities

        # Act
        result = self.repository.get_all(use_cache=False)

        # Assert
        self.assertEqual(result, mock_entities)
        mock_all.assert_called_once()

    @patch.object(TestModel.objects, 'filter')
    def test_filter(self, mock_filter):
        """Test filtering entities"""
        # Arrange
        mock_queryset = Mock()
        mock_filter.return_value = mock_queryset

        # Act
        result = self.repository.filter(name='test', is_active=True)

        # Assert
        self.assertEqual(result, mock_queryset)
        mock_filter.assert_called_once_with(name='test', is_active=True)

    @patch.object(TestModel.objects, 'create')
    def test_create(self, mock_create):
        """Test creating entity"""
        # Arrange
        mock_entity = Mock(spec=TestModel)
        mock_entity.id = 1
        mock_create.return_value = mock_entity

        with patch.object(self.repository, '_invalidate_cache_pattern'):
            # Act
            result = self.repository.create(**self.test_data)

            # Assert
            self.assertEqual(result, mock_entity)
            mock_create.assert_called_once_with(**self.test_data)

    @patch.object(TestModel.objects, 'get')
    def test_update_success(self, mock_get):
        """Test successful entity update"""
        # Arrange
        mock_entity = Mock(spec=TestModel)
        mock_entity.id = 1
        mock_get.return_value = mock_entity

        with patch.object(self.repository, '_invalidate_cache_pattern'):
            # Act
            result = self.repository.update(1, name='Updated Name')

            # Assert
            self.assertEqual(result, mock_entity)
            mock_get.assert_called_once_with(id=1)
            mock_entity.save.assert_called_once()

    @patch.object(TestModel.objects, 'get')
    def test_update_not_found(self, mock_get):
        """Test updating entity that doesn't exist"""
        # Arrange
        mock_get.side_effect = TestModel.DoesNotExist()

        # Act
        result = self.repository.update(999, name='Updated Name')

        # Assert
        self.assertIsNone(result)

    @patch.object(TestModel.objects, 'get')
    @patch.object(TestModel, 'delete')
    def test_delete_success(self, mock_delete, mock_get):
        """Test successful entity deletion"""
        # Arrange
        mock_entity = Mock(spec=TestModel)
        mock_entity.id = 1
        mock_get.return_value = mock_entity

        with patch.object(self.repository, '_invalidate_cache_pattern'):
            # Act
            result = self.repository.delete(1)

            # Assert
            self.assertTrue(result)
            mock_get.assert_called_once_with(id=1)
            mock_entity.delete.assert_called_once()

    @patch.object(TestModel.objects, 'get')
    def test_delete_not_found(self, mock_get):
        """Test deleting entity that doesn't exist"""
        # Arrange
        mock_get.side_effect = TestModel.DoesNotExist()

        # Act
        result = self.repository.delete(999)

        # Assert
        self.assertFalse(result)

    @patch.object(TestModel.objects, 'bulk_create')
    def test_bulk_create(self, mock_bulk_create):
        """Test bulk creating entities"""
        # Arrange
        entities_data = [self.test_data, self.test_data.copy()]
        mock_entities = [Mock(spec=TestModel), Mock(spec=TestModel)]
        mock_bulk_create.return_value = mock_entities

        with patch.object(self.repository, '_invalidate_cache_pattern'):
            # Act
            result = self.repository.bulk_create(entities_data)

            # Assert
            self.assertEqual(result, mock_entities)
            mock_bulk_create.assert_called_once()

    @patch.object(TestModel.objects, 'bulk_update')
    def test_bulk_update(self, mock_bulk_update):
        """Test bulk updating entities"""
        # Arrange
        mock_entities = [Mock(spec=TestModel), Mock(spec=TestModel)]
        mock_bulk_update.return_value = 2

        with patch.object(self.repository, '_invalidate_cache_pattern'):
            # Act
            result = self.repository.bulk_update(mock_entities, ['name', 'email'])

            # Assert
            self.assertEqual(result, 2)
            mock_bulk_update.assert_called_once_with(mock_entities, ['name', 'email'])

    @patch.object(TestModel.objects, 'filter')
    def test_exists(self, mock_filter):
        """Test checking if entity exists"""
        # Arrange
        mock_queryset = Mock()
        mock_queryset.exists.return_value = True
        mock_filter.return_value = mock_queryset

        # Act
        result = self.repository.exists(email='test@example.com')

        # Assert
        self.assertTrue(result)
        mock_filter.assert_called_once_with(email='test@example.com')
        mock_queryset.exists.assert_called_once()

    @patch.object(TestModel.objects, 'filter')
    def test_count(self, mock_filter):
        """Test counting entities"""
        # Arrange
        mock_queryset = Mock()
        mock_queryset.count.return_value = 5
        mock_filter.return_value = mock_queryset

        # Act
        result = self.repository.count(is_active=True)

        # Assert
        self.assertEqual(result, 5)
        mock_filter.assert_called_once_with(is_active=True)
        mock_queryset.count.assert_called_once()

    def test_get_paginated(self):
        """Test getting paginated results"""
        # Arrange
        mock_queryset = Mock()
        mock_entities = [Mock(spec=TestModel) for _ in range(50)]
        mock_queryset.__iter__ = Mock(return_value=iter(mock_entities))

        with patch.object(self.repository, 'filter', return_value=mock_queryset):
            with patch('crm.shared.repositories.base.Paginator') as mock_paginator_class:
                # Arrange paginator mock
                mock_page = Mock()
                mock_page.number = 1
                mock_page.object_list = mock_entities[:20]
                mock_page.has_next.return_value = True
                mock_page.has_previous.return_value = False

                mock_paginator = Mock()
                mock_paginator.num_pages = 3
                mock_paginator.count = 50
                mock_paginator.page.return_value = mock_page
                mock_paginator_class.return_value = mock_paginator

                # Act
                result = self.repository.get_paginated(page=1, per_page=20)

                # Assert
                self.assertEqual(len(result['results']), 20)
                self.assertEqual(result['pagination']['page'], 1)
                self.assertEqual(result['pagination']['per_page'], 20)
                self.assertEqual(result['pagination']['total_pages'], 3)
                self.assertEqual(result['pagination']['total_items'], 50)
                self.assertTrue(result['pagination']['has_next'])
                self.assertFalse(result['pagination']['has_previous'])

    @patch('crm.shared.repositories.base.cache')
    def test_invalidate_cache_pattern(self, mock_cache):
        """Test cache invalidation"""
        # Act
        self.repository._invalidate_cache_pattern("test_pattern")

        # Assert
        mock_cache.delete.assert_called_once_with('testmodel_test_pattern')

    @patch('crm.shared.repositories.base.cache')
    def test_clear_cache(self, mock_cache):
        """Test clearing all cache"""
        # Act
        self.repository.clear_cache()

        # Assert
        mock_cache.delete.assert_called_once_with('testmodel_all')


class SoftDeleteRepositoryTest(TestCase):
    """Test SoftDeleteRepository following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.repository = SoftDeleteRepository(TestModel)

    def test_soft_delete_repository_initialization(self):
        """Test soft delete repository initialization"""
        # Assert
        self.assertEqual(self.repository.model, TestModel)
        self.assertFalse(self.repository.include_deleted)

    def test_soft_delete_success(self):
        """Test successful soft delete"""
        # Arrange
        mock_entity = Mock(spec=TestModel)
        mock_entity.id = 1

        with patch.object(self.repository, 'get_by_id', return_value=mock_entity):
            with patch.object(self.repository, '_invalidate_cache_pattern'):
                # Act
                result = self.repository.soft_delete(1)

                # Assert
                self.assertTrue(result)
                mock_entity.delete.assert_called_once()

    def test_soft_delete_not_found(self):
        """Test soft delete when entity doesn't exist"""
        # Arrange
        with patch.object(self.repository, 'get_by_id', return_value=None):
            # Act
            result = self.repository.soft_delete(999)

            # Assert
            self.assertFalse(result)

    def test_restore_success(self):
        """Test successful restore"""
        # Arrange
        mock_entity = Mock(spec=TestModel)
        mock_entity.id = 1

        with patch.object(TestModel, 'objects_with_deleted') as mock_manager:
            mock_manager.get.return_value = mock_entity

            with patch.object(self.repository, '_invalidate_cache_pattern'):
                # Act
                result = self.repository.restore(1)

                # Assert
                self.assertTrue(result)
                mock_entity.restore.assert_called_once()

    def test_restore_with_is_deleted_flag(self):
        """Test restore when model uses is_deleted flag"""
        # Arrange
        mock_entity = Mock(spec=TestModel)
        mock_entity.id = 1
        del mock_entity.restore  # Remove restore method

        with patch.object(TestModel, 'objects_with_deleted') as mock_manager:
            mock_manager.get.return_value = mock_entity

            with patch.object(self.repository, '_invalidate_cache_pattern'):
                # Act
                result = self.repository.restore(1)

                # Assert
                self.assertTrue(result)
                self.assertFalse(mock_entity.is_deleted)
                mock_entity.save.assert_called_once()

    def test_get_deleted_with_objects_with_deleted(self):
        """Test getting deleted entities with objects_with_deleted manager"""
        # Arrange
        mock_entities = [Mock(spec=TestModel), Mock(spec=TestModel)]
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_entities

        with patch.object(TestModel, 'objects_with_deleted') as mock_manager:
            mock_manager.filter.return_value = mock_queryset

            # Act
            result = self.repository.get_deleted()

            # Assert
            self.assertEqual(result, mock_entities)
            mock_manager.filter.assert_called_once_with(is_deleted=True)

    def test_get_deleted_without_objects_with_deleted(self):
        """Test getting deleted entities without objects_with_deleted manager"""
        # Arrange
        mock_entities = [Mock(spec=TestModel), Mock(spec=TestModel)]
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_entities

        with patch.object(TestModel, 'objects', mock_queryset):
            del TestModel.objects_with_deleted  # Remove the manager

            # Act
            result = self.repository.get_deleted()

            # Assert
            self.assertEqual(result, mock_entities)
            mock_queryset.filter.assert_called_once_with(is_deleted=True)