from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from authentication.models import CustomUser, Role
from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord
from pollination.services import PollinationService, ValidationService


class PollinationServiceTest(TestCase):
    """Test cases for PollinationService."""
    
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
        
        # Create plants
        self.mother_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 1',
            pared='Pared A'
        )
        self.father_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 2',
            pared='Pared B'
        )
        self.new_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 3',
            pared='Pared C'
        )
        
        # Create pollination type
        self.pollination_type = PollinationType.objects.create(
            name='Self',
            description='Autopolinización',
            maturation_days=120
        )
        
        # Create climate condition
        self.climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0,
            humidity=65
        )
    
    def test_calculate_maturation_date(self):
        """Test maturation date calculation."""
        pollination_date = date.today()
        maturation_date = PollinationService.calculate_maturation_date(
            pollination_date, self.pollination_type
        )
        expected_date = pollination_date + timedelta(days=120)
        self.assertEqual(maturation_date, expected_date)
    
    def test_calculate_maturation_date_invalid_inputs(self):
        """Test maturation date calculation with invalid inputs."""
        with self.assertRaises(ValueError):
            PollinationService.calculate_maturation_date("invalid_date", self.pollination_type)
        
        with self.assertRaises(ValueError):
            PollinationService.calculate_maturation_date(date.today(), "invalid_type")
    
    def test_get_maturation_status_pending(self):
        """Test maturation status for pending records."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        status = PollinationService.get_maturation_status(record)
        self.assertEqual(status['status'], 'pending')
        self.assertEqual(status['days_remaining'], 120)
        self.assertFalse(status['is_overdue'])
    
    def test_get_maturation_status_approaching(self):
        """Test maturation status for approaching records."""
        past_date = date.today() - timedelta(days=115)  # 5 days remaining
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=past_date,
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        status = PollinationService.get_maturation_status(record)
        self.assertEqual(status['status'], 'approaching')
        self.assertEqual(status['days_remaining'], 5)
        self.assertFalse(status['is_overdue'])
    
    def test_get_maturation_status_overdue(self):
        """Test maturation status for overdue records."""
        past_date = date.today() - timedelta(days=130)  # 10 days overdue
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=past_date,
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        status = PollinationService.get_maturation_status(record)
        self.assertEqual(status['status'], 'overdue')
        self.assertEqual(status['days_remaining'], -10)
        self.assertTrue(status['is_overdue'])
    
    def test_get_maturation_status_confirmed(self):
        """Test maturation status for confirmed records."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today() - timedelta(days=100),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5,
            maturation_confirmed=True,
            maturation_confirmed_date=date.today()
        )
        
        status = PollinationService.get_maturation_status(record)
        self.assertEqual(status['status'], 'confirmed')
        self.assertEqual(status['days_remaining'], 0)
        self.assertFalse(status['is_overdue'])
    
    def test_get_records_by_maturation_status_pending(self):
        """Test filtering records by pending status."""
        # Create a pending record (more than 7 days remaining)
        PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        records = PollinationService.get_records_by_maturation_status(
            user=self.user, status_filter='pending'
        )
        self.assertEqual(records.count(), 1)
    
    def test_get_records_by_maturation_status_overdue(self):
        """Test filtering records by overdue status."""
        # Create an overdue record
        past_date = date.today() - timedelta(days=130)
        PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=past_date,
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        records = PollinationService.get_records_by_maturation_status(
            user=self.user, status_filter='overdue'
        )
        self.assertEqual(records.count(), 1)
    
    def test_confirm_maturation(self):
        """Test maturation confirmation."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today() - timedelta(days=100),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        confirmed_record = PollinationService.confirm_maturation(record)
        
        self.assertTrue(confirmed_record.maturation_confirmed)
        self.assertEqual(confirmed_record.maturation_confirmed_date, date.today())
        self.assertTrue(confirmed_record.is_successful)
    
    def test_confirm_maturation_already_confirmed(self):
        """Test confirming already confirmed maturation."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today() - timedelta(days=100),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5,
            maturation_confirmed=True
        )
        
        with self.assertRaises(ValidationError):
            PollinationService.confirm_maturation(record)
    
    def test_get_success_statistics(self):
        """Test success statistics calculation."""
        # Create various records
        PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today() - timedelta(days=100),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5,
            maturation_confirmed=True,
            is_successful=True
        )
        
        PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today() - timedelta(days=90),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=3,
            maturation_confirmed=True,
            is_successful=False
        )
        
        PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=4
        )
        
        stats = PollinationService.get_success_statistics(user=self.user)
        
        self.assertEqual(stats['total_records'], 3)
        self.assertEqual(stats['confirmed_records'], 2)
        self.assertEqual(stats['successful_records'], 1)
        self.assertEqual(stats['success_rate'], 50.0)
        self.assertEqual(stats['confirmation_rate'], 66.67)


class ValidationServiceTest(TestCase):
    """Test cases for ValidationService."""
    
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
        
        # Create plants
        self.mother_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 1',
            pared='Pared A'
        )
        self.father_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 2',
            pared='Pared B'
        )
        self.new_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 3',
            pared='Pared C'
        )
        
        # Create different species plant for hybrid testing
        self.hybrid_father = Plant.objects.create(
            genus='Orchidaceae',
            species='dendrobium',
            vivero='Vivero 1',
            mesa='Mesa 4',
            pared='Pared D'
        )
        
        # Create pollination types
        self.self_type = PollinationType.objects.create(
            name='Self',
            description='Autopolinización'
        )
        self.sibling_type = PollinationType.objects.create(
            name='Sibling',
            description='Polinización entre hermanos'
        )
        self.hybrid_type = PollinationType.objects.create(
            name='Híbrido',
            description='Hibridación'
        )
        
        # Create climate condition
        self.climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0,
            humidity=65
        )
    
    def test_validate_pollination_data_valid(self):
        """Test validation of valid pollination data."""
        data = {
            'responsible': self.user,
            'pollination_type': self.self_type,
            'pollination_date': date.today(),
            'mother_plant': self.mother_plant,
            'new_plant': self.new_plant,
            'climate_condition': self.climate,
            'capsules_quantity': 5
        }
        
        result = ValidationService.validate_pollination_data(data)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_pollination_data_missing_fields(self):
        """Test validation with missing required fields."""
        data = {
            'responsible': self.user,
            # Missing other required fields
        }
        
        result = ValidationService.validate_pollination_data(data)
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_pollination_data_future_date(self):
        """Test validation with future pollination date."""
        future_date = date.today() + timedelta(days=1)
        data = {
            'responsible': self.user,
            'pollination_type': self.self_type,
            'pollination_date': future_date,
            'mother_plant': self.mother_plant,
            'new_plant': self.new_plant,
            'climate_condition': self.climate,
            'capsules_quantity': 5
        }
        
        result = ValidationService.validate_pollination_data(data)
        self.assertFalse(result['is_valid'])
        self.assertIn('pollination_date', result['errors'])
    
    def test_validate_pollination_data_invalid_capsules(self):
        """Test validation with invalid capsules quantity."""
        data = {
            'responsible': self.user,
            'pollination_type': self.self_type,
            'pollination_date': date.today(),
            'mother_plant': self.mother_plant,
            'new_plant': self.new_plant,
            'climate_condition': self.climate,
            'capsules_quantity': 0  # Invalid quantity
        }
        
        result = ValidationService.validate_pollination_data(data)
        self.assertFalse(result['is_valid'])
        self.assertIn('capsules_quantity', result['errors'])
    
    def test_validate_plant_compatibility_self_valid(self):
        """Test plant compatibility validation for Self pollination."""
        result = ValidationService.validate_plant_compatibility(
            self.mother_plant, None, self.self_type
        )
        self.assertTrue(result['is_compatible'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_plant_compatibility_self_with_father(self):
        """Test plant compatibility validation for Self with father plant."""
        result = ValidationService.validate_plant_compatibility(
            self.mother_plant, self.father_plant, self.self_type
        )
        self.assertFalse(result['is_compatible'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_plant_compatibility_sibling_valid(self):
        """Test plant compatibility validation for Sibling pollination."""
        result = ValidationService.validate_plant_compatibility(
            self.mother_plant, self.father_plant, self.sibling_type
        )
        self.assertTrue(result['is_compatible'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_plant_compatibility_sibling_no_father(self):
        """Test plant compatibility validation for Sibling without father."""
        result = ValidationService.validate_plant_compatibility(
            self.mother_plant, None, self.sibling_type
        )
        self.assertFalse(result['is_compatible'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_plant_compatibility_hybrid_valid(self):
        """Test plant compatibility validation for Hybrid pollination."""
        result = ValidationService.validate_plant_compatibility(
            self.mother_plant, self.hybrid_father, self.hybrid_type
        )
        self.assertTrue(result['is_compatible'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_plant_compatibility_hybrid_same_species(self):
        """Test plant compatibility validation for Hybrid with same species."""
        result = ValidationService.validate_plant_compatibility(
            self.mother_plant, self.father_plant, self.hybrid_type
        )
        self.assertFalse(result['is_compatible'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_maturation_confirmation_valid(self):
        """Test valid maturation confirmation."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=date.today() - timedelta(days=100),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        result = ValidationService.validate_maturation_confirmation(record)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_maturation_confirmation_already_confirmed(self):
        """Test maturation confirmation for already confirmed record."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=date.today() - timedelta(days=100),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5,
            maturation_confirmed=True
        )
        
        result = ValidationService.validate_maturation_confirmation(record)
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_maturation_confirmation_future_date(self):
        """Test maturation confirmation with future date."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=date.today() - timedelta(days=100),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        future_date = date.today() + timedelta(days=1)
        result = ValidationService.validate_maturation_confirmation(record, future_date)
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_maturation_confirmation_too_early(self):
        """Test maturation confirmation too early."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=date.today() - timedelta(days=10),  # Only 10 days ago
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        result = ValidationService.validate_maturation_confirmation(record)
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)