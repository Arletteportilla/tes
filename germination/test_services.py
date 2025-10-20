"""
Unit tests for germination services.
Tests business logic, validations, and calculations.
"""

from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import GerminationRecord, SeedSource, GerminationSetup
from core.models import ClimateCondition
from .services import GerminationService, GerminationValidationService
from pollination.models import Plant, PollinationType, PollinationRecord, ClimateCondition

User = get_user_model()


class GerminationServiceTest(TestCase):
    """Test cases for GerminationService."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.plant = Plant.objects.create(
            genus='Orchidaceae',
            species='test_species',
            vivero='Test Vivero',
            mesa='Test Mesa',
            pared='Test Pared'
        )
        
        self.seed_source = SeedSource.objects.create(
            name='Test Source',
            source_type='Otra fuente',
            external_supplier='Test Supplier'
        )
        
        climate_condition = ClimateCondition.objects.create(climate='I', notes='Test climate')
        self.germination_setup = GerminationSetup.objects.create(
            climate_condition=climate_condition,
            setup_notes='Test setup'
        )
    
    def test_calculate_transplant_date_default(self):
        """Test transplant date calculation with default days."""
        germination_date = date(2024, 1, 15)
        
        transplant_date = GerminationService.calculate_transplant_date(
            germination_date, self.plant
        )
        
        # Orchidaceae should use 120 days
        expected_date = germination_date + timedelta(days=120)
        self.assertEqual(transplant_date, expected_date)
    
    def test_calculate_transplant_date_custom(self):
        """Test transplant date calculation with custom days."""
        germination_date = date(2024, 1, 15)
        custom_days = 60
        
        transplant_date = GerminationService.calculate_transplant_date(
            germination_date, self.plant, custom_days
        )
        
        expected_date = germination_date + timedelta(days=custom_days)
        self.assertEqual(transplant_date, expected_date)
    
    def test_calculate_transplant_date_unknown_genus(self):
        """Test transplant date calculation for unknown genus."""
        plant = Plant.objects.create(
            genus='Unknown',
            species='test_species',
            vivero='Test Vivero',
            mesa='Test Mesa',
            pared='Test Pared'
        )
        
        germination_date = date(2024, 1, 15)
        
        transplant_date = GerminationService.calculate_transplant_date(
            germination_date, plant
        )
        
        # Should use default 90 days
        expected_date = germination_date + timedelta(days=90)
        self.assertEqual(transplant_date, expected_date)
    
    def test_get_transplant_recommendations_completed(self):
        """Test transplant recommendations for completed transplant."""
        germination_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date(2024, 1, 15),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=10,
            transplant_confirmed=True,
            transplant_confirmed_date=date(2024, 4, 15)
        )
        
        recommendations = GerminationService.get_transplant_recommendations(
            germination_record
        )
        
        self.assertEqual(recommendations['status'], 'completed')
        self.assertFalse(recommendations['action_required'])
    
    def test_get_transplant_recommendations_overdue(self):
        """Test transplant recommendations for overdue transplant."""
        past_date = date.today() - timedelta(days=10)
        
        germination_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=past_date - timedelta(days=120),
            estimated_transplant_date=past_date,
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=10
        )
        
        recommendations = GerminationService.get_transplant_recommendations(
            germination_record
        )
        
        self.assertEqual(recommendations['status'], 'overdue')
        self.assertTrue(recommendations['action_required'])
        self.assertEqual(recommendations['urgency'], 'high')
    
    def test_get_transplant_recommendations_approaching(self):
        """Test transplant recommendations for approaching transplant."""
        future_date = date.today() + timedelta(days=5)
        
        germination_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today() - timedelta(days=85),
            estimated_transplant_date=future_date,
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=10
        )
        
        recommendations = GerminationService.get_transplant_recommendations(
            germination_record
        )
        
        self.assertEqual(recommendations['status'], 'approaching')
        self.assertTrue(recommendations['action_required'])
        self.assertEqual(recommendations['urgency'], 'medium')
    
    def test_calculate_germination_statistics_empty(self):
        """Test statistics calculation with empty records."""
        stats = GerminationService.calculate_germination_statistics([])
        
        self.assertEqual(stats['total_records'], 0)
        self.assertEqual(stats['total_seeds_planted'], 0)
        self.assertEqual(stats['total_seedlings_germinated'], 0)
        self.assertEqual(stats['average_germination_rate'], 0)
        self.assertEqual(stats['success_rate'], 0)
    
    def test_calculate_germination_statistics_with_data(self):
        """Test statistics calculation with actual data."""
        records = []
        
        # Create test records
        for i in range(3):
            record = GerminationRecord.objects.create(
                responsible=self.user,
                germination_date=date.today() - timedelta(days=i),
                plant=self.plant,
                seed_source=self.seed_source,
                germination_setup=self.germination_setup,
                seeds_planted=10,
                seedlings_germinated=8 if i < 2 else 6,  # 2 successful, 1 less successful
                is_successful=True if i < 2 else False
            )
            records.append(record)
        
        stats = GerminationService.calculate_germination_statistics(records)
        
        self.assertEqual(stats['total_records'], 3)
        self.assertEqual(stats['total_seeds_planted'], 30)
        self.assertEqual(stats['total_seedlings_germinated'], 22)  # 8+8+6
        self.assertEqual(stats['average_germination_rate'], 73.33)  # 22/30 * 100
        self.assertEqual(stats['success_rate'], 66.67)  # 2/3 * 100
    
    def test_get_pending_transplants(self):
        """Test getting pending transplants."""
        # Create records with different transplant dates
        today = date.today()
        
        # Pending within range
        pending_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=today - timedelta(days=60),
            estimated_transplant_date=today + timedelta(days=15),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=10
        )
        
        # Already confirmed
        GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=today - timedelta(days=90),
            estimated_transplant_date=today + timedelta(days=10),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=10,
            transplant_confirmed=True
        )
        
        # Too far in future
        GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=today - timedelta(days=30),
            estimated_transplant_date=today + timedelta(days=60),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=10
        )
        
        pending = GerminationService.get_pending_transplants(days_ahead=30)
        
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].id, pending_record.id)
    
    def test_get_overdue_transplants(self):
        """Test getting overdue transplants."""
        today = date.today()
        
        # Overdue record
        overdue_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=today - timedelta(days=120),
            estimated_transplant_date=today - timedelta(days=10),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=10
        )
        
        # Future record
        GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=today - timedelta(days=60),
            estimated_transplant_date=today + timedelta(days=30),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=10
        )
        
        overdue = GerminationService.get_overdue_transplants()
        
        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue[0].id, overdue_record.id)


class GerminationValidationServiceTest(TestCase):
    """Test cases for GerminationValidationService."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.plant = Plant.objects.create(
            genus='Test',
            species='test_species',
            vivero='Test Vivero',
            mesa='Test Mesa',
            pared='Test Pared'
        )
        
        self.seed_source = SeedSource.objects.create(
            name='Test Source',
            source_type='Otra fuente',
            external_supplier='Test Supplier'
        )
    
    def test_validate_germination_record_valid(self):
        """Test validation of valid germination record."""
        data = {
            'germination_date': date.today() - timedelta(days=1),
            'seeds_planted': 10,
            'seedlings_germinated': 8,
            'transplant_days': 90,
            'seed_source': self.seed_source.id,
            'plant': self.plant.id
        }
        
        is_valid, errors = GerminationValidationService.validate_germination_record(data)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_germination_record_future_date(self):
        """Test validation with future germination date."""
        data = {
            'germination_date': date.today() + timedelta(days=1),
            'seeds_planted': 10,
            'seedlings_germinated': 8,
            'transplant_days': 90
        }
        
        is_valid, errors = GerminationValidationService.validate_germination_record(data)
        
        self.assertFalse(is_valid)
        self.assertIn('La fecha de germinación no puede ser futura', errors)
    
    def test_validate_germination_record_invalid_quantities(self):
        """Test validation with invalid seed quantities."""
        data = {
            'germination_date': date.today() - timedelta(days=1),
            'seeds_planted': 5,
            'seedlings_germinated': 10,  # More than planted
            'transplant_days': 90
        }
        
        is_valid, errors = GerminationValidationService.validate_germination_record(data)
        
        self.assertFalse(is_valid)
        self.assertIn('Las plántulas germinadas no pueden exceder las semillas sembradas', errors)
    
    def test_validate_germination_record_zero_seeds(self):
        """Test validation with zero seeds planted."""
        data = {
            'germination_date': date.today() - timedelta(days=1),
            'seeds_planted': 0,
            'seedlings_germinated': 0,
            'transplant_days': 90
        }
        
        is_valid, errors = GerminationValidationService.validate_germination_record(data)
        
        self.assertFalse(is_valid)
        self.assertIn('Debe especificar al menos una semilla sembrada', errors)
    
    def test_validate_germination_record_invalid_transplant_days(self):
        """Test validation with invalid transplant days."""
        data = {
            'germination_date': date.today() - timedelta(days=1),
            'seeds_planted': 10,
            'seedlings_germinated': 8,
            'transplant_days': 400  # Too many days
        }
        
        is_valid, errors = GerminationValidationService.validate_germination_record(data)
        
        self.assertFalse(is_valid)
        self.assertIn('Los días de trasplante no pueden exceder un año', errors)
    
    def test_validate_seed_source_valid(self):
        """Test validation of valid seed source."""
        data = {
            'source_type': 'Otra fuente',
            'external_supplier': 'Test Supplier',
            'collection_date': date.today() - timedelta(days=30)
        }
        
        is_valid, errors = GerminationValidationService.validate_seed_source(data)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_seed_source_future_collection_date(self):
        """Test validation with future collection date."""
        data = {
            'source_type': 'Otra fuente',
            'external_supplier': 'Test Supplier',
            'collection_date': date.today() + timedelta(days=1)
        }
        
        is_valid, errors = GerminationValidationService.validate_seed_source(data)
        
        self.assertFalse(is_valid)
        self.assertIn('La fecha de recolección no puede ser futura', errors)
    
    def test_validate_seed_source_missing_external_supplier(self):
        """Test validation with missing external supplier."""
        data = {
            'source_type': 'Otra fuente',
            'collection_date': date.today() - timedelta(days=30)
        }
        
        is_valid, errors = GerminationValidationService.validate_seed_source(data)
        
        self.assertFalse(is_valid)
        self.assertIn('Se requiere especificar el proveedor externo', errors)
    
    def test_validate_germination_condition_valid(self):
        """Test validation of valid germination condition."""
        data = {
            'climate': 'Controlado',
            'substrate': 'Turba',
            'location': 'Test Location',
            'temperature': 25.5,
            'humidity': 80,
            'light_hours': 12
        }
        
        is_valid, errors = GerminationValidationService.validate_germination_condition(data)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_germination_condition_invalid_temperature(self):
        """Test validation with invalid temperature."""
        data = {
            'climate': 'Controlado',
            'substrate': 'Turba',
            'location': 'Test Location',
            'temperature': -60  # Too low
        }
        
        is_valid, errors = GerminationValidationService.validate_germination_condition(data)
        
        self.assertFalse(is_valid)
        self.assertIn('La temperatura debe estar entre -50°C y 60°C', errors)
    
    def test_validate_germination_condition_invalid_humidity(self):
        """Test validation with invalid humidity."""
        data = {
            'climate': 'Controlado',
            'substrate': 'Turba',
            'location': 'Test Location',
            'humidity': 150  # Too high
        }
        
        is_valid, errors = GerminationValidationService.validate_germination_condition(data)
        
        self.assertFalse(is_valid)
        self.assertIn('La humedad debe estar entre 0% y 100%', errors)
    
    def test_validate_germination_condition_invalid_light_hours(self):
        """Test validation with invalid light hours."""
        data = {
            'climate': 'Controlado',
            'substrate': 'Turba',
            'location': 'Test Location',
            'light_hours': 30  # Too many hours
        }
        
        is_valid, errors = GerminationValidationService.validate_germination_condition(data)
        
        self.assertFalse(is_valid)
        self.assertIn('Las horas de luz deben estar entre 0 y 24 horas', errors)
    
    def test_validate_germination_condition_missing_required_fields(self):
        """Test validation with missing required fields."""
        data = {
            'temperature': 25.5,
            'humidity': 80
        }
        
        is_valid, errors = GerminationValidationService.validate_germination_condition(data)
        
        self.assertFalse(is_valid)
        self.assertIn('El tipo de clima es requerido', errors)
        self.assertIn('El tipo de sustrato es requerido', errors)
        self.assertIn('La ubicación es requerida', errors)
    
    def test_check_duplicate_germination_exists(self):
        """Test duplicate check when duplicate exists."""
        # Create existing record
        existing_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=GerminationSetup.objects.create(
                climate_condition=ClimateCondition.objects.create(climate='I', notes='Test'),
                setup_notes='Test setup'
            ),
            seeds_planted=10
        )
        
        # Check for duplicate
        is_duplicate = GerminationValidationService.check_duplicate_germination(
            germination_date=date.today(),
            plant_id=self.plant.id,
            seed_source_id=self.seed_source.id,
            responsible_id=self.user.id
        )
        
        self.assertTrue(is_duplicate)
    
    def test_check_duplicate_germination_not_exists(self):
        """Test duplicate check when no duplicate exists."""
        is_duplicate = GerminationValidationService.check_duplicate_germination(
            germination_date=date.today(),
            plant_id=self.plant.id,
            seed_source_id=self.seed_source.id,
            responsible_id=self.user.id
        )
        
        self.assertFalse(is_duplicate)
    
    def test_check_duplicate_germination_exclude_self(self):
        """Test duplicate check excluding specific record."""
        # Create existing record
        existing_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=GerminationSetup.objects.create(
                climate_condition=ClimateCondition.objects.create(climate='I', notes='Test'),
                setup_notes='Test setup'
            ),
            seeds_planted=10
        )
        
        # Check for duplicate excluding the existing record (for updates)
        is_duplicate = GerminationValidationService.check_duplicate_germination(
            germination_date=date.today(),
            plant_id=self.plant.id,
            seed_source_id=self.seed_source.id,
            responsible_id=self.user.id,
            exclude_id=existing_record.id
        )
        
        self.assertFalse(is_duplicate)