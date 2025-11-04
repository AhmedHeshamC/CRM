#!/usr/bin/env python
"""
Wait for database to be available
"""

import os
import time
import sys
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.exceptions import ImproperlyConfigured


class Command(BaseCommand):
    help = 'Wait for database to be available'

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database connection...')

        max_retries = 30
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                connection.ensure_connection()
                self.stdout.write(self.style.SUCCESS('Database connection established!'))
                break
            except Exception as e:
                self.stdout.write(f'Attempt {attempt + 1}/{max_retries}: {e}')
                if attempt == max_retries - 1:
                    self.stdout.write(self.style.ERROR('Failed to connect to database'))
                    sys.exit(1)
                time.sleep(retry_delay)