"""
Management command to set up predefined climate conditions.
Creates the basic climate conditions for both pollination and germination.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from pollination.models import ClimateCondition as PollinationClimate
from germination.models import GerminationCondition


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
                PollinationClimate.objects.all().delete()
                GerminationCondition.objects.all().delete()

            # Create pollination climate conditions
            self.create_pollination_climates()
            
            # Create germination conditions
            self.create_germination_conditions()

        self.stdout.write(
            self.style.SUCCESS('Successfully set up climate conditions!')
        )

    def create_pollination_climates(self):
        """Create predefined pollination climate conditions."""
        climates = [
            {
                'climate': 'C',
                'notes': 'Condición climática fría predefinida para especies de montaña'
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
            climate, created = PollinationClimate.objects.get_or_create(
                climate=climate_data['climate'],
                defaults={'notes': climate_data['notes']}
            )
            if created:
                self.stdout.write(f'  Created pollination climate: {climate.get_climate_display()}')
            else:
                self.stdout.write(f'  Pollination climate already exists: {climate.get_climate_display()}')

    def create_germination_conditions(self):
        """Create predefined germination conditions."""
        conditions = [
            {
                'climate': 'C',
                'substrate': 'Turba',
                'location': 'Cámara fría controlada',
                'substrate_details': 'Turba pura con drenaje excelente',
                'notes': 'Condiciones frías para especies de alta montaña'
            },
            {
                'climate': 'IC',
                'substrate': 'Musgo sphagnum',
                'location': 'Invernadero templado',
                'substrate_details': 'Musgo sphagnum húmedo con perlita',
                'notes': 'Condiciones templadas para especies intermedias'
            },
            {
                'climate': 'I',
                'substrate': 'Corteza de pino',
                'location': 'Invernadero estándar',
                'substrate_details': 'Corteza de pino fina con vermiculita',
                'notes': 'Condiciones estándar para la mayoría de especies'
            },
            {
                'climate': 'IW',
                'substrate': 'Mezcla personalizada',
                'location': 'Invernadero cálido',
                'substrate_details': 'Mezcla de turba, perlita y corteza',
                'notes': 'Condiciones cálidas para especies subtropicales'
            },
            {
                'climate': 'W',
                'substrate': 'Perlita',
                'location': 'Cámara tropical',
                'substrate_details': 'Perlita pura con alta retención de humedad',
                'notes': 'Condiciones tropicales para especies de clima caliente'
            }
        ]

        for condition_data in conditions:
            condition, created = GerminationCondition.objects.get_or_create(
                climate=condition_data['climate'],
                substrate=condition_data['substrate'],
                location=condition_data['location'],
                defaults={
                    'substrate_details': condition_data['substrate_details'],
                    'notes': condition_data['notes']
                }
            )
            if created:
                self.stdout.write(f'  Created germination condition: {condition.get_climate_display()} - {condition.substrate}')
            else:
                self.stdout.write(f'  Germination condition already exists: {condition.get_climate_display()} - {condition.substrate}')