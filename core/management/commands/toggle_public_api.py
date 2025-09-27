"""
Management command to toggle public API testing mode.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Toggle public API testing mode for development'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--enable',
            action='store_true',
            help='Enable public API testing mode',
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Disable public API testing mode',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show current status of public API testing',
        )
    
    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write(
                self.style.ERROR(
                    'Public API testing is only available in DEBUG mode'
                )
            )
            return
        
        env_file = '.env'
        
        if options['status']:
            current_status = getattr(settings, 'ENABLE_PUBLIC_API_TESTING', False)
            status_text = "ENABLED" if current_status else "DISABLED"
            self.stdout.write(
                self.style.SUCCESS(f'Public API testing is currently: {status_text}')
            )
            return
        
        if options['enable']:
            self._update_env_file(env_file, 'ENABLE_PUBLIC_API_TESTING', 'True')
            self.stdout.write(
                self.style.SUCCESS(
                    'Public API testing ENABLED. Restart the server to apply changes.'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    'WARNING: APIs are now publicly accessible without authentication!'
                )
            )
            
        elif options['disable']:
            self._update_env_file(env_file, 'ENABLE_PUBLIC_API_TESTING', 'False')
            self.stdout.write(
                self.style.SUCCESS(
                    'Public API testing DISABLED. Restart the server to apply changes.'
                )
            )
            self.stdout.write(
                'Authentication is now required for all protected endpoints.'
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Please specify --enable, --disable, or --status'
                )
            )
    
    def _update_env_file(self, env_file, key, value):
        """Update or add a key-value pair in the .env file."""
        lines = []
        key_found = False
        
        # Read existing file if it exists
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
        
        # Update existing key or mark for addition
        for i, line in enumerate(lines):
            if line.strip().startswith(f'{key}='):
                lines[i] = f'{key}={value}\n'
                key_found = True
                break
        
        # Add key if not found
        if not key_found:
            lines.append(f'{key}={value}\n')
        
        # Write back to file
        with open(env_file, 'w') as f:
            f.writelines(lines)