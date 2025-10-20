"""
Management command to set up predefined climate conditions.
Creates the basic climate conditions for both pollination and germination.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import ClimateCondition
from germination.models import GerminationSetup


class Command(BaseCommand):
    help = 'Set up predefined climate conditions for pollination and germination'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing climate conditions before creating new ones',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Setting up predefined climate conditions...')
        )

        with transaction.atomic():
            if options['reset']:
                self.stdout.write('Deleting existing climate conditions...')
                ClimateCondition.objects.all().delete()
                GerminationSetup.objects.all().delete()

            # Create shared climate conditions
            self.create_climate_conditions()
            
            # Create germination setups
            self.create_germination_setups()

        self.stdout.write(
            self.style.SUCCESS('Successfully set up climate conditions!')
        )

    def create_climate_conditions(self):
        """Create shared climate conditions."""
        climates = [
            {
                'climate': 'C',
                'notes': 'Condición climática fría para especies de montaña'
            },
            {
                'climate': 'IC',
                'notes': 'Condición climática intermedia fría para especies templadas'
            },
            {
                'climate': 'I',
                'notes': 'Condición climática intermedia estándar para la mayoría de especies'
            },
            {
                'climate': 'IW',
                'notes': 'Condición climática intermedia caliente para especies subtropicales'
            },
            {
                'climate': 'W',
                'notes': 'Condición climática caliente para especies tropicales'
            }
        ]

        for climate_data in climates:
            climate, created = ClimateCondition.objects.get_or_create(
                climate=climate_data['climate'],
                defaults={'notes': climate_data['notes']}
            )
            if created:
                self.stdout.write(f'  Created climate condition: {climate.get_climate_display()}')
            else:
                self.stdout.write(f'  Climate condition already exists: {climate.get_climate_display()}')

    def create_germination_setups(self):
        """Create predefined germination setups."""
        # First ensure we have climate conditions
        climate_conditions = {}
        for climate_code in ['C', 'IC', 'I', 'IW', 'W']:
            climate_conditions[climate_code] = ClimateCondition.objects.get(climate=climate_code)
        
        setups = [
            {
                'climate_code': 'C',
                'setup_notes': 'Configuración climática fría para especies de alta montaña'
            },
            {
                'climate_code': 'IC',
                'setup_notes': 'Configuración climática intermedia fría para especies templadas'
            },
            {
                'climate_code': 'I',
                'setup_notes': 'Configuración climática intermedia estándar para la mayoría de especies'
            },
            {
                'climate_code': 'IW',
                'setup_notes': 'Configuración climática intermedia caliente para especies subtropicales'
            },
            {
                'climate_code': 'W',
                'setup_notes': 'Configuración climática caliente para especies tropicales'
            }
        ]

        for setup_data in setups:
            climate_condition = climate_conditions[setup_data['climate_code']]
            setup, created = GerminationSetup.objects.get_or_create(
                climate_condition=climate_condition,
                defaults={
                    'setup_notes': setup_data['setup_notes']
                }
            )
            if created:
                self.stdout.write(f'  Created germination setup: {setup.climate_display}')
            else:
                self.stdout.write(f'  Germination setup already exists: {setup.climate_display}')