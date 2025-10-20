from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import date, timedelta
from authentication.models import CustomUser, Role
from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord
from germination.models import SeedSource, GerminationSetup, GerminationRecord
from core.models import ClimateCondition


class SeedSourceModelTest(TestCase):
    """Test cases for SeedSource model."""
    
    def setUp(self):
        """Set up test data."""
        # Create role and user
        self.role = Role.objects.create(name='Polinizador')
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create plant and pollination record for internal source
        self.plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 1',
            pared='Pared A'
        )
        
        self.pollination_type = PollinationType.objects.create(
            name='Self',
            description='Autopolinización'
        )
        
        self.climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0
        )
        
        self.pollination_record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today() - timedelta(days=100),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
    
    def test_seed_source_creation_internal(self):
        """Test seed source creation from internal pollination."""
        seed_source = SeedSource.objects.create(
            name='Semillas de Autopolinización Cattleya',
            source_type='Autopolinización',
            description='Semillas obtenidas de autopolinización controlada',
            pollination_record=self.pollination_record,
            collection_date=date.today() - timedelta(days=30)
        )
        
        self.assertEqual(seed_source.name, 'Semillas de Autopolinización Cattleya')
        self.assertEqual(seed_source.source_type, 'Autopolinización')
        self.assertTrue(seed_source.is_active)
        self.assertIsNotNone(seed_source.created_at)
    
    def test_seed_source_creation_external(self):
        """Test seed source creation from external supplier."""
        seed_source = SeedSource.objects.create(
            name='Semillas Comerciales Dendrobium',
            source_type='Otra fuente',
            description='Semillas adquiridas de proveedor comercial',
            external_supplier='Orquídeas del Valle S.A.',
            collection_date=date.today() - timedelta(days=15)
        )
        
        self.assertEqual(seed_source.source_type, 'Otra fuente')
        self.assertEqual(seed_source.external_supplier, 'Orquídeas del Valle S.A.')
        self.assertTrue(seed_source.is_active)
    
    def test_seed_source_str_representation(self):
        """Test seed source string representation."""
        seed_source = SeedSource.objects.create(
            name='Test Seeds',
            source_type='Híbrido',
            external_supplier='Test Supplier'
        )
        expected = "Test Seeds (Hibridación)"
        self.assertEqual(str(seed_source), expected)
    
    def test_seed_source_future_date_validation(self):
        """Test validation of future collection dates."""
        future_date = date.today() + timedelta(days=1)
        seed_source = SeedSource(
            name='Test Seeds',
            source_type='Otra fuente',
            external_supplier='Test Supplier',
            collection_date=future_date
        )
        
        with self.assertRaises(ValidationError):
            seed_source.clean()
    
    def test_seed_source_external_supplier_validation(self):
        """Test validation requiring external supplier for external sources."""
        seed_source = SeedSource(
            name='Test Seeds',
            source_type='Otra fuente'
            # Missing external_supplier
        )
        
        with self.assertRaises(ValidationError):
            seed_source.clean()


class GerminationSetupModelTest(TestCase):
    """Test cases for GerminationSetup model."""
    
    def test_germination_setup_creation(self):
        """Test germination setup creation."""
        climate_condition = ClimateCondition.objects.create(
            climate='I',
            notes='Condición climática intermedia'
        )
        
        setup = GerminationSetup.objects.create(
            climate_condition=climate_condition,
            setup_notes='Configuración óptima para germinación'
        )
        
        self.assertEqual(setup.climate_condition.climate, 'I')
        self.assertEqual(setup.climate_display, 'Intermedio')
        self.assertIsNotNone(setup.temperature_range)
    
    def test_germination_setup_str_representation(self):
        """Test germination setup string representation."""
        climate_condition = ClimateCondition.objects.create(
            climate='I',
            notes='Test climate'
        )
        setup = GerminationSetup.objects.create(
            climate_condition=climate_condition,
            setup_notes='Test setup'
        )
        expected = "Intermedio"
        self.assertEqual(str(setup), expected)
    
    def test_germination_setup_properties(self):
        """Test germination setup properties."""
        climate_condition = ClimateCondition.objects.create(
            climate='IW',
            notes='Test warm climate'
        )
        setup = GerminationSetup.objects.create(
            climate_condition=climate_condition,
            setup_notes='Test setup'
        )
        
        self.assertEqual(setup.climate_display, 'Intermedio Caliente')
        self.assertIsNotNone(setup.temperature_range)
        self.assertIsNotNone(setup.climate_description)


class GerminationRecordModelTest(TestCase):
    """Test cases for GerminationRecord model."""
    
    def setUp(self):
        """Set up test data."""
        # Create role and user
        self.role = Role.objects.create(name='Germinador')
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create plant
        self.plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 1',
            pared='Pared A'
        )
        
        # Create seed source
        self.seed_source = SeedSource.objects.create(
            name='Semillas Test',
            source_type='Otra fuente',
            external_supplier='Test Supplier'
        )
        
        # Create germination setup
        climate_condition = ClimateCondition.objects.create(
            climate='I',
            notes='Test climate condition'
        )
        self.germination_setup = GerminationSetup.objects.create(
            climate_condition=climate_condition,
            setup_notes='Test setup'
        )
    
    def test_germination_record_creation(self):
        """Test germination record creation."""
        record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=100,
            seedlings_germinated=75,
            transplant_days=90
        )
        
        self.assertEqual(record.responsible, self.user)
        self.assertEqual(record.plant, self.plant)
        self.assertEqual(record.seeds_planted, 100)
        self.assertEqual(record.seedlings_germinated, 75)
        self.assertIsNotNone(record.estimated_transplant_date)
        self.assertFalse(record.transplant_confirmed)
    
    def test_germination_record_str_representation(self):
        """Test germination record string representation."""
        record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=50
        )
        
        expected = f"Orchidaceae cattleya - {date.today()} - testuser"
        self.assertEqual(str(record), expected)
    
    def test_estimated_transplant_date_calculation(self):
        """Test automatic calculation of estimated transplant date."""
        germination_date = date.today()
        record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=germination_date,
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=50,
            transplant_days=90
        )
        
        expected_date = germination_date + timedelta(days=90)
        self.assertEqual(record.estimated_transplant_date, expected_date)
    
    def test_future_date_validation(self):
        """Test validation of future germination dates."""
        future_date = date.today() + timedelta(days=1)
        record = GerminationRecord(
            responsible=self.user,
            germination_date=future_date,
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=50
        )
        
        with self.assertRaises(ValidationError):
            record.clean()
    
    def test_seedlings_validation(self):
        """Test validation that seedlings don't exceed seeds planted."""
        record = GerminationRecord(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=50,
            seedlings_germinated=75  # More than planted
        )
        
        with self.assertRaises(ValidationError):
            record.clean()
    
    def test_transplant_date_validation(self):
        """Test validation of transplant confirmation date."""
        record = GerminationRecord(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=50,
            transplant_confirmed_date=date.today() - timedelta(days=1)  # Before germination
        )
        
        with self.assertRaises(ValidationError):
            record.clean()
    
    def test_is_transplant_overdue(self):
        """Test transplant overdue check."""
        past_date = date.today() - timedelta(days=100)
        record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=past_date,
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=50,
            transplant_days=90
        )
        
        self.assertTrue(record.is_transplant_overdue())
    
    def test_days_to_transplant(self):
        """Test days to transplant calculation."""
        record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=50,
            transplant_days=90
        )
        
        self.assertEqual(record.days_to_transplant(), 90)
    
    def test_germination_rate(self):
        """Test germination rate calculation."""
        record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=100,
            seedlings_germinated=75
        )
        
        self.assertEqual(record.germination_rate(), 75.0)
    
    def test_confirm_transplant(self):
        """Test transplant confirmation."""
        record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today() - timedelta(days=100),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=50
        )
        
        confirmation_date = date.today()
        record.confirm_transplant(confirmation_date, is_successful=True)
        
        self.assertTrue(record.transplant_confirmed)
        self.assertEqual(record.transplant_confirmed_date, confirmation_date)
        self.assertTrue(record.is_successful)
    
    def test_transplant_status_property(self):
        """Test transplant status property."""
        # Test pending status (more than 7 days remaining)
        record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germination_setup,
            seeds_planted=50,
            transplant_days=90
        )
        self.assertEqual(record.transplant_status, 'pending')
        
        # Test approaching status (7 days or less remaining)
        record.germination_date = date.today() - timedelta(days=85)  # 5 days remaining
        record.estimated_transplant_date = None  # Reset to recalculate
        record.save()
        self.assertEqual(record.transplant_status, 'approaching')
        
        # Test overdue status
        record.germination_date = date.today() - timedelta(days=100)  # 10 days overdue
        record.estimated_transplant_date = None  # Reset to recalculate
        record.save()
        self.assertEqual(record.transplant_status, 'overdue')
        
        # Test confirmed status
        record.confirm_transplant()
        self.assertEqual(record.transplant_status, 'confirmed')
