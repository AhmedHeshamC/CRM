"""
Base Task Classes for Background Processing
Following SOLID principles and comprehensive task management
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from enum import Enum
from django.core.cache import cache
from django.utils import timezone
from celery import Task
from celery.exceptions import Retry, MaxRetriesExceededError
from celery.signals import task_prerun, task_postrun, task_failure, task_success

from .exceptions import (
    TaskExecutionError,
    TaskTimeoutError,
    TaskRetryError,
    TaskValidationError,
    TaskResourceError,
    TaskErrorCodes,
    TaskExceptionFactory,
)

# Configure logger
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """
    Enumeration of possible task statuses.

    This follows the Single Responsibility Principle by providing
    a centralized status management system with helper methods.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"

    def is_completed(self) -> bool:
        """Check if task is in a completed state"""
        return self in {TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.CANCELLED, TaskStatus.TIMEOUT}

    def is_active(self) -> bool:
        """Check if task is in an active state"""
        return self in {TaskStatus.RUNNING, TaskStatus.RETRY}


class TaskPriority(Enum):
    """
    Enumeration of task priorities.

    This follows the Open/Closed Principle by allowing easy extension
    of priority levels while maintaining consistent behavior.
    """

    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class BaseTask(Task, ABC):
    """
    Abstract base class for all background tasks.

    This follows SOLID principles:
    - Single Responsibility: Each subclass handles one specific task type
    - Open/Closed: Extensible without modifying base functionality
    - Liskov Substitution: All subclasses can replace BaseTask
    - Interface Segregation: Minimal abstract interface
    - Dependency Inversion: Depends on abstractions, not implementations
    """

    # Default configuration
    default_retry_delay = 60  # 1 minute
    max_retries = 3
    soft_time_limit = 300  # 5 minutes
    time_limit = 600  # 10 minutes
    default_queue = 'default'

    def __init__(self):
        super().__init__()
        self.task_id = None
        self.created_at = timezone.now()
        self.updated_at = timezone.now()
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.metadata = {}

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Abstract method for task execution logic.

        This follows the Template Method pattern, allowing subclasses
        to define their specific execution logic while maintaining
        consistent behavior across all tasks.

        Args:
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task

        Returns:
            Any: Task execution result

        Raises:
            TaskExecutionError: If task execution fails
            TaskValidationError: If input validation fails
            TaskResourceError: If resource constraints are violated
        """
        pass

    def run(self, *args, **kwargs) -> Any:
        """
        Main task execution method with comprehensive error handling.

        This follows the Decorator pattern by wrapping the abstract execute
        method with additional functionality like status tracking, logging,
        and error handling.
        """
        self.task_id = self.request.id
        operation_name = self.__class__.__name__

        try:
            # Log task start
            self.log_task_start(operation_name, *args, **kwargs)

            # Set initial status
            self.set_task_status(TaskStatus.RUNNING, progress=0)

            # Execute the task with timeout protection
            start_time = time.time()
            result = self.execute(*args, **kwargs)
            execution_time = time.time() - start_time

            # Log successful completion
            self.set_task_status(TaskStatus.SUCCESS, progress=100)
            self.log_task_success(operation_name, execution_time=execution_time)

            return result

        except Retry as e:
            # Handle Celery retry
            self.log_task_failure(operation_name, e, will_retry=True)
            self.set_task_status(TaskStatus.RETRY)
            raise

        except MaxRetriesExceededError as e:
            # Handle max retries exceeded
            self.log_task_failure(operation_name, e, will_retry=False)
            self.set_task_status(TaskStatus.FAILURE)
            raise

        except Exception as e:
            # Handle unexpected errors
            self.log_task_failure(operation_name, e, will_retry=False)
            self.set_task_status(TaskStatus.FAILURE)
            raise

    def validate_inputs(self, *args, **kwargs) -> None:
        """
        Validate task inputs before execution.

        This follows the Single Responsibility Principle by separating
        validation logic from execution logic.

        Args:
            *args: Positional arguments to validate
            **kwargs: Keyword arguments to validate

        Raises:
            TaskValidationError: If validation fails
        """
        # Default implementation - subclasses should override
        pass

    def set_task_status(
        self,
        status: TaskStatus,
        progress: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update task status and store in cache for monitoring.

        This provides centralized status management with Redis persistence
        for monitoring and debugging purposes.
        """
        if progress is not None and (progress < 0 or progress > 100):
            raise ValueError(f"Progress must be between 0 and 100, got {progress}")

        self.status = status
        self.updated_at = timezone.now()

        if progress is not None:
            self.progress = progress

        if metadata:
            self.metadata.update(metadata)

        # Store status in cache for monitoring
        if self.task_id:
            status_data = {
                'status': status.value,
                'progress': self.progress,
                'updated_at': self.updated_at.isoformat(),
                'metadata': self.metadata,
                'task_class': self.__class__.__name__,
            }

            cache.set(
                f'task_status_{self.task_id}',
                status_data,
                timeout=3600  # 1 hour
            )

    def get_task_status(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve current task status from cache.

        Returns:
            Optional[Dict[str, Any]]: Task status data or None if not found
        """
        if not self.task_id:
            return None

        return cache.get(f'task_status_{self.task_id}')

    def calculate_retry_delay(self, retry_count: int) -> int:
        """
        Calculate exponential backoff delay for retries.

        This implements the Exponential Backoff pattern to prevent
        overwhelming the system with rapid retries.

        Args:
            retry_count: Current retry attempt number

        Returns:
            int: Delay in seconds before next retry
        """
        # Base delay of 1 minute with exponential backoff
        base_delay = 60
        max_delay = 300  # 5 minutes maximum

        # Exponential backoff with jitter
        delay = min(base_delay * (2 ** retry_count), max_delay)

        # Add jitter to prevent thundering herd
        jitter = delay * 0.1
        import random
        delay += random.uniform(-jitter, jitter)

        return int(delay)

    def log_task_start(self, operation: str, *args, **kwargs) -> None:
        """Log task start with context information"""
        logger.info(
            f"Starting task: {operation}",
            extra={
                'task_id': self.task_id,
                'task_class': self.__class__.__name__,
                'operation': operation,
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys()),
                'worker': getattr(self.request, 'hostname', 'unknown'),
            }
        )

    def log_task_success(self, operation: str, **context) -> None:
        """Log task success with context information"""
        logger.info(
            f"Task completed successfully: {operation}",
            extra={
                'task_id': self.task_id,
                'task_class': self.__class__.__name__,
                'operation': operation,
                'duration': context.get('execution_time'),
                'worker': getattr(self.request, 'hostname', 'unknown'),
                **context
            }
        )

    def log_task_failure(
        self,
        operation: str,
        error: Exception,
        will_retry: bool = False
    ) -> None:
        """Log task failure with detailed error information"""
        log_level = logger.warning if will_retry else logger.error

        log_level(
            f"Task {'retrying' if will_retry else 'failed permanently'}: {operation}",
            extra={
                'task_id': self.task_id,
                'task_class': self.__class__.__name__,
                'operation': operation,
                'error_type': error.__class__.__name__,
                'error_message': str(error),
                'will_retry': will_retry,
                'worker': getattr(self.request, 'hostname', 'unknown'),
            }
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Callback method for task retry events.

        This follows the Observer pattern by allowing custom behavior
        when tasks are retried.
        """
        retry_count = getattr(self.request, 'retries', 0)
        max_retries = self.max_retries or 3
        backoff_delay = self.calculate_retry_delay(retry_count)

        self.set_task_status(TaskStatus.RETRY)
        self.log_task_failure(
            self.__class__.__name__,
            exc,
            will_retry=retry_count < max_retries
        )

        logger.warning(
            f"Task retry {retry_count} of {max_retries}",
            extra={
                'task_id': self.task_id,
                'retry_count': retry_count,
                'max_retries': max_retries,
                'backoff_delay': backoff_delay,
                'error': str(exc)
            }
        )

    def on_success(self, retval, task_id, args, kwargs):
        """
        Callback method for task success events.

        This follows the Observer pattern by allowing custom behavior
        when tasks complete successfully.
        """
        self.set_task_status(TaskStatus.SUCCESS, progress=100)
        self.log_task_success(self.__class__.__name__)

        logger.info(
            f"Task completed successfully",
            extra={
                'task_id': self.task_id,
                'task_class': self.__class__.__name__,
                'result_type': type(retval).__name__
            }
        )

        return retval, task_id, args, kwargs

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Callback method for task failure events.

        This follows the Observer pattern by allowing custom behavior
        when tasks fail permanently.
        """
        self.set_task_status(TaskStatus.FAILURE)
        self.log_task_failure(self.__class__.__name__, exc, will_retry=False)

        logger.error(
            f"Task failed permanently",
            extra={
                'task_id': self.task_id,
                'task_class': self.__class__.__name__,
                'error_type': exc.__class__.__name__,
                'error_message': str(exc),
                'traceback': str(einfo) if einfo else None
            }
        )

    def cleanup(self) -> None:
        """
        Cleanup method called after task completion.

        This follows the Template Method pattern by allowing subclasses
        to define cleanup procedures while maintaining consistent behavior.
        """
        # Default implementation - subclasses should override if needed
        pass

    def get_task_metrics(self) -> Dict[str, Any]:
        """
        Get task performance and status metrics.

        Returns:
            Dict[str, Any]: Task metrics for monitoring
        """
        return {
            'task_id': self.task_id,
            'task_class': self.__class__.__name__,
            'status': self.status.value,
            'progress': self.progress,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'duration': (self.updated_at - self.created_at).total_seconds(),
            'metadata': self.metadata,
        }


# Signal handlers for task monitoring
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task pre-run signal for monitoring"""
    logger.debug(
        f"Task pre-run: {task.name}",
        extra={
            'task_id': task_id,
            'task_name': task.name,
            'args_count': len(args) if args else 0,
            'kwargs_keys': list(kwargs.keys()) if kwargs else []
        }
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task post-run signal for monitoring"""
    logger.debug(
        f"Task post-run: {task.name} - {state}",
        extra={
            'task_id': task_id,
            'task_name': task.name,
            'state': state,
            'return_type': type(retval).__name__ if retval else None
        }
    )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failure signal for monitoring"""
    logger.error(
        f"Task failed: {sender.name}",
        extra={
            'task_id': task_id,
            'task_name': sender.name,
            'exception_type': exception.__class__.__name__ if exception else None,
            'exception_message': str(exception) if exception else None,
        }
    )


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Handle task success signal for monitoring"""
    logger.debug(
        f"Task succeeded: {sender.name}",
        extra={
            'task_name': sender.name,
            'result_type': type(result).__name__ if result else None
        }
    )