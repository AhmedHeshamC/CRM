"""
Database Utilities for CRM Project
Following SOLID and KISS principles
Single Responsibility: Database connection testing and backup operations
"""

import os
import subprocess
import logging
from django.conf import settings
from django.db import connection
from django.core.management import call_command
import psycopg2
from psycopg2.extensions import connection as pg_connection
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class DatabaseHealthChecker:
    """
    Database Health Check Utility
    Following SOLID Single Responsibility principle
    """

    @staticmethod
    def test_postgresql_connection() -> bool:
        """
        Test PostgreSQL connection availability
        GREEN: Implementation for test_postgresql_connection()
        """
        try:
            db_config = settings.DATABASES['default']

            # Create connection with timeout
            conn = psycopg2.connect(
                host=db_config['HOST'],
                port=db_config['PORT'],
                database=db_config['NAME'],
                user=db_config['USER'],
                password=db_config['PASSWORD'],
                connect_timeout=10
            )

            # Test simple query
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1')
                result = cursor.fetchone()

            conn.close()
            return result[0] == 1

        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    @staticmethod
    def run_database_migrations(verbosity: int = 0) -> bool:
        """
        Run database migrations
        GREEN: Implementation for _run_database_migrations()
        """
        try:
            call_command('migrate', verbosity=verbosity)
            return True
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

    @staticmethod
    def get_database_info() -> Dict:
        """
        Get database connection information
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        version() as version,
                        current_database() as database,
                        current_user as user,
                        inet_server_addr() as server_ip,
                        inet_server_port() as server_port
                """)
                result = cursor.fetchone()

                return {
                    'version': result[0],
                    'database': result[1],
                    'user': result[2],
                    'server_ip': result[3],
                    'server_port': result[4],
                    'engine': settings.DATABASES['default']['ENGINE']
                }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {'error': str(e)}


class DatabaseBackupManager:
    """
    Database Backup and Recovery Utility
    Following SOLID Single Responsibility principle
    """

    def __init__(self):
        self.db_config = settings.DATABASES['default']
        self.backup_dir = os.environ.get('BACKUP_DIR', '/var/backups/crm')

    def generate_backup_command(self, backup_file: str = None) -> str:
        """
        Generate pg_dump backup command
        GREEN: Implementation for _generate_backup_command()
        Following KISS principle - simple command generation
        """
        if backup_file is None:
            backup_file = f"{self.backup_dir}/crm_backup_{self._get_timestamp()}.sql"

        # Use environment variable for password (PGPASSWORD)
        command = (
            f"PGPASSWORD='{self.db_config['PASSWORD']}' "
            f"pg_dump -h {self.db_config['HOST']} "
            f"-U {self.db_config['USER']} "
            f"-d {self.db_config['NAME']} "
            f"-f {backup_file} "
            f"--verbose --no-password"
        )

        return command

    def create_backup(self, backup_file: str = None) -> Tuple[bool, str]:
        """
        Create database backup
        """
        try:
            # Ensure backup directory exists
            os.makedirs(self.backup_dir, exist_ok=True)

            command = self.generate_backup_command(backup_file)
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                backup_path = backup_file or f"{self.backup_dir}/crm_backup_{self._get_timestamp()}.sql"
                return True, f"Backup created successfully: {backup_path}"
            else:
                return False, f"Backup failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Backup failed: timeout exceeded"
        except Exception as e:
            return False, f"Backup failed: {str(e)}"

    def generate_restore_command(self, backup_file: str) -> str:
        """
        Generate psql restore command
        """
        command = (
            f"PGPASSWORD='{self.db_config['PASSWORD']}' "
            f"psql -h {self.db_config['HOST']} "
            f"-U {self.db_config['USER']} "
            f"-d {self.db_config['NAME']} "
            f"-f {backup_file} "
            f"--verbose --no-password"
        )

        return command

    def restore_backup(self, backup_file: str) -> Tuple[bool, str]:
        """
        Restore database from backup
        """
        try:
            if not os.path.exists(backup_file):
                return False, f"Backup file not found: {backup_file}"

            command = self.generate_restore_command(backup_file)
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                return True, "Database restored successfully"
            else:
                return False, f"Restore failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Restore failed: timeout exceeded"
        except Exception as e:
            return False, f"Restore failed: {str(e)}"

    def _get_timestamp(self) -> str:
        """Generate timestamp for backup files"""
        from datetime import datetime
        return datetime.now().strftime('%Y%m%d_%H%M%S')


class DatabaseConnectionPool:
    """
    Simple Connection Pool Manager
    Following KISS principle - minimal implementation
    """

    def __init__(self, max_connections: int = 20, min_connections: int = 5):
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.active_connections = 0

    def get_connection_status(self) -> Dict:
        """
        Get connection pool status
        GREEN: Implementation for connection pooling test
        """
        return {
            'max_connections': self.max_connections,
            'min_connections': self.min_connections,
            'active_connections': self.active_connections,
            'pool_status': 'active' if self.active_connections > 0 else 'idle'
        }