from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
import os


class Command(BaseCommand):
    help = 'Load initial fixtures for the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fixture',
            type=str,
            help='Specific fixture file to load (default: all fixtures)'
        )

    def handle(self, *args, **options):
        fixtures_dir = 'fixtures'
        
        if options['fixture']:
            # Load specific fixture
            fixture_path = os.path.join(fixtures_dir, options['fixture'])
            if not fixture_path.endswith('.json'):
                fixture_path += '.json'
            
            if os.path.exists(fixture_path):
                self.load_fixture(fixture_path)
            else:
                self.stdout.write(
                    self.style.ERROR(f'Fixture file not found: {fixture_path}')
                )
        else:
            # Load all fixtures
            self.load_all_fixtures(fixtures_dir)

    def load_all_fixtures(self, fixtures_dir):
        """Load all fixture files in the fixtures directory."""
        if not os.path.exists(fixtures_dir):
            self.stdout.write(
                self.style.ERROR(f'Fixtures directory not found: {fixtures_dir}')
            )
            return

        fixture_files = [
            f for f in os.listdir(fixtures_dir) 
            if f.endswith('.json')
        ]

        if not fixture_files:
            self.stdout.write(
                self.style.WARNING('No fixture files found in fixtures directory')
            )
            return

        # Load fixtures in order (initial_data first)
        ordered_fixtures = []
        if 'initial_data.json' in fixture_files:
            ordered_fixtures.append('initial_data.json')
            fixture_files.remove('initial_data.json')
        
        ordered_fixtures.extend(sorted(fixture_files))

        for fixture_file in ordered_fixtures:
            fixture_path = os.path.join(fixtures_dir, fixture_file)
            self.load_fixture(fixture_path)

    def load_fixture(self, fixture_path):
        """Load a specific fixture file."""
        try:
            with transaction.atomic():
                self.stdout.write(f'Loading fixture: {fixture_path}')
                call_command('loaddata', fixture_path, verbosity=0)
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully loaded: {fixture_path}')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading {fixture_path}: {str(e)}')
            )