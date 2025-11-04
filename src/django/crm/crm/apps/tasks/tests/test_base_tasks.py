"""
Test suite for Base Task Classes
Following TDD principles and SOLID design patterns
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.test import TestCase
from django.core.cache import cache
from django.utils import timezone
from celery.exceptions import Retry, MaxRetriesExceededError
from ..base_tasks import BaseTask, TaskStatus, TaskPriority
from ..exceptions import TaskExecutionError, TaskTimeoutError, TaskRetryError


class TestTaskStatus:
    """Test the TaskStatus enum for robust status tracking"""

    def test_task_status_values(self):
        """Test that TaskStatus has all required values"""
        assert TaskStatus.PENDING.value == 'PENDING'
        assert TaskStatus.RUNNING.value == 'RUNNING'
        assert TaskStatus.SUCCESS.value == 'SUCCESS'
        assert TaskStatus.FAILURE.value == 'FAILURE'
        assert TaskStatus.RETRY.value == 'RETRY'
        assert TaskStatus.CANCELLED.value == 'CANCELLED'
        assert TaskStatus.TIMEOUT.value == 'TIMEOUT'

    def test_task_status_is_completed(self):
        """Test completed status checking"""
        assert TaskStatus.SUCCESS.is_completed() is True
        assert TaskStatus.FAILURE.is_completed() is True
        assert TaskStatus.CANCELLED.is_completed() is True
        assert TaskStatus.TIMEOUT.is_completed() is True

        assert TaskStatus.PENDING.is_completed() is False
        assert TaskStatus.RUNNING.is_completed() is False
        assert TaskStatus.RETRY.is_completed() is False

    def test_task_status_is_active(self):
        """Test active status checking"""
        assert TaskStatus.RUNNING.is_active() is True
        assert TaskStatus.RETRY.is_active() is True

        assert TaskStatus.PENDING.is_active() is False
        assert TaskStatus.SUCCESS.is_active() is False
        assert TaskStatus.FAILURE.is_active() is False
        assert TaskStatus.CANCELLED.is_active() is False
        assert TaskStatus.TIMEOUT.is_active() is False


class TestTaskPriority:
    """Test the TaskPriority enum for queue management"""

    def test_task_priority_values(self):
        """Test that TaskPriority has correct numeric values"""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 5
        assert TaskPriority.HIGH.value == 8
        assert TaskPriority.CRITICAL.value == 10

    def test_task_priority_ordering(self):
        """Test that priorities can be compared"""
        priorities = [TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH, TaskPriority.CRITICAL]
        sorted_priorities = sorted(priorities, key=lambda p: p.value)

        assert sorted_priorities[0] == TaskPriority.LOW
        assert sorted_priorities[-1] == TaskPriority.CRITICAL


class TestBaseTask(TestCase):
    """Test the BaseTask abstract class for consistent task behavior"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-task-id-123'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-worker'
        self.mock_task.request.timestamp = timezone.now()

        # Clear cache before each test
        cache.clear()

    def test_base_task_initialization(self):
        """Test BaseTask initialization with required parameters"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()
        self.assertIsNotNone(task.task_id)
        self.assertIsInstance(task.created_at, datetime)
        self.assertEqual(task.status, TaskStatus.PENDING)

    @patch('crm.apps.tasks.base_tasks.cache')
    def test_set_task_status_updates_cache(self, mock_cache):
        """Test that set_task_status properly updates cache"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()
        task.task_id = 'test-task-id'

        task.set_task_status(TaskStatus.RUNNING, progress=50)

        expected_data = {
            'status': TaskStatus.RUNNING.value,
            'progress': 50,
            'updated_at': task.updated_at.isoformat(),
        }
        mock_cache.set.assert_called_once_with(
            f'task_status_{task.task_id}',
            expected_data,
            timeout=3600
        )

    def test_set_task_status_validation(self):
        """Test set_task_status input validation"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()

        # Test invalid progress values
        with self.assertRaises(ValueError):
            task.set_task_status(TaskStatus.RUNNING, progress=-1)

        with self.assertRaises(ValueError):
            task.set_task_status(TaskStatus.RUNNING, progress=101)

    def test_set_task_status_with_metadata(self):
        """Test set_task_status with additional metadata"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()
        task.task_id = 'test-task-id'

        metadata = {'processed_count': 100, 'total_count': 200}
        with patch('crm.apps.tasks.base_tasks.cache') as mock_cache:
            task.set_task_status(TaskStatus.RUNNING, progress=50, metadata=metadata)

            call_args = mock_cache.set.call_args[0]
            cached_data = call_args[1]
            self.assertEqual(cached_data['metadata'], metadata)

    def test_get_task_status(self):
        """Test retrieving task status from cache"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()
        task.task_id = 'test-task-id'

        # Test with cached data
        cached_data = {
            'status': TaskStatus.RUNNING.value,
            'progress': 75,
            'updated_at': timezone.now().isoformat(),
            'metadata': {'processed': 150}
        }

        with patch('crm.apps.tasks.base_tasks.cache.get', return_value=cached_data):
            status = task.get_task_status()
            self.assertEqual(status['status'], TaskStatus.RUNNING.value)
            self.assertEqual(status['progress'], 75)
            self.assertEqual(status['metadata'], {'processed': 150})

    def test_get_task_status_not_found(self):
        """Test getting task status when not in cache"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()
        task.task_id = 'test-task-id'

        with patch('crm.apps.tasks.base_tasks.cache.get', return_value=None):
            status = task.get_task_status()
            self.assertIsNone(status)

    def test_calculate_retry_delay_with_exponential_backoff(self):
        """Test exponential backoff calculation for retries"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()

        # Test exponential backoff progression
        delay_0 = task.calculate_retry_delay(0)
        delay_1 = task.calculate_retry_delay(1)
        delay_2 = task.calculate_retry_delay(2)

        assert delay_1 > delay_0
        assert delay_2 > delay_1

        # Test maximum delay cap
        delay_10 = task.calculate_retry_delay(10)
        self.assertLessEqual(delay_10, 300)  # Max 5 minutes

    def test_log_task_start(self):
        """Test task start logging"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()
        task.task_id = 'test-task-id'

        with patch('crm.apps.tasks.base_tasks.logger') as mock_logger:
            task.log_task_start('Test operation', param1='value1')

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0]
            self.assertIn('Starting task: Test operation', call_args[0])
            self.assertIn('task_id', call_args[1])

    def test_log_task_success(self):
        """Test task success logging"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()
        task.task_id = 'test-task-id'

        with patch('crm.apps.tasks.base_tasks.logger') as mock_logger:
            task.log_task_success('Test operation', result_count=42)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0]
            self.assertIn('Task completed successfully: Test operation', call_args[0])
            self.assertEqual(call_args[1]['result_count'], 42)

    def test_log_task_failure_with_retry(self):
        """Test task failure logging with retry"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()
        task.task_id = 'test-task-id'

        with patch('crm.apps.tasks.base_tasks.logger') as mock_logger:
            task.log_task_failure('Test operation', Exception('Test error'), will_retry=True)

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0]
            self.assertIn('Task failed, will retry: Test operation', call_args[0])
            self.assertIn('error', call_args[1])

    def test_log_task_failure_no_retry(self):
        """Test task failure logging without retry"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "test result"

        task = TestTask()
        task.task_id = 'test-task-id'

        with patch('crm.apps.tasks.base_tasks.logger') as mock_logger:
            task.log_task_failure('Test operation', Exception('Test error'), will_retry=False)

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0]
            self.assertIn('Task failed permanently: Test operation', call_args[0])

    def test_run_with_successful_execution(self):
        """Test successful task execution flow"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "success"

        task = TestTask()
        task.task_id = 'test-task-id'
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch.object(task, 'log_task_start') as mock_log_start:
                with patch.object(task, 'log_task_success') as mock_log_success:
                    result = task.run("test", param="value")

                    self.assertEqual(result, "success")
                    mock_log_start.assert_called_once_with("TestTask", test="test", param="value")
                    mock_set_status.assert_any_call(TaskStatus.RUNNING, progress=0)
                    mock_set_status.assert_any_call(TaskStatus.SUCCESS, progress=100)
                    mock_log_success.assert_called_once_with("TestTask")

    def test_run_with_retry_exception(self):
        """Test task execution with retry"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                raise Retry("Retry this task")

        task = TestTask()
        task.task_id = 'test-task-id'
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status'):
            with patch.object(task, 'log_task_failure') as mock_log_failure:
                with pytest.raises(Retry):
                    task.run("test")

                mock_log_failure.assert_called_once()

    def test_run_with_max_retries_exceeded(self):
        """Test task execution when max retries exceeded"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                raise MaxRetriesExceededError("Max retries exceeded")

        task = TestTask()
        task.task_id = 'test-task-id'
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status'):
            with patch.object(task, 'log_task_failure') as mock_log_failure:
                with pytest.raises(MaxRetriesExceededError):
                    task.run("test")

                mock_log_failure.assert_called_once()

    def test_run_with_unexpected_exception(self):
        """Test task execution with unexpected exception"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                raise ValueError("Unexpected error")

        task = TestTask()
        task.task_id = 'test-task-id'
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status'):
            with patch.object(task, 'log_task_failure') as mock_log_failure:
                with pytest.raises(ValueError):
                    task.run("test")

                mock_log_failure.assert_called_once()

    def test_on_retry_callback(self):
        """Test retry callback functionality"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "success"

        task = TestTask()
        task.task_id = 'test-task-id'

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch.object(task, 'log_task_failure') as mock_log_failure:
                task.on_retry(Exception("Test error"), None, "test", param="value")

                mock_set_status.assert_called_once_with(TaskStatus.RETRY)
                mock_log_failure.assert_called_once()

    def test_on_success_callback(self):
        """Test success callback functionality"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "success"

        task = TestTask()
        task.task_id = 'test-task-id'

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch.object(task, 'log_task_success') as mock_log_success:
                retval, task_id, args, kwargs = task.on_success("success result", None, "test", param="value")

                self.assertEqual(retval, "success result")
                self.assertEqual(task_id, None)
                self.assertEqual(args, ("test",))
                self.assertEqual(kwargs, {"param": "value"})
                mock_set_status.assert_called_once_with(TaskStatus.SUCCESS, progress=100)
                mock_log_success.assert_called_once_with("TestTask")

    def test_on_failure_callback(self):
        """Test failure callback functionality"""
        class TestTask(BaseTask):
            def execute(self, *args, **kwargs):
                return "success"

        task = TestTask()
        task.task_id = 'test-task-id'

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch.object(task, 'log_task_failure') as mock_log_failure:
                task.on_failure(Exception("Test error"), None, "test", param="value")

                mock_set_status.assert_called_once_with(TaskStatus.FAILURE)
                mock_log_failure.assert_called_once()