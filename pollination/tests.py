from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import date, timedelta
from authentication.models import CustomUser, Role
from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord


class PlantModelTest(TestCase):
    """Test cases for Plant model."""
    
    def setUp(self):
        """Set up test data."""
        self.plant_data = {
            'genus': 'Orchidaceae',
            'species': 'cattleya',
            'vivero': 'Vivero Principal',
            'mesa': 'Mesa 1',
            'pared': 'Pared A'
        }
    
    def test_plant_creation(self):
        """Test plant creation with valid data."""
        plant = Plant.objects.create(**self.plant_data)
        self.assertEqual(plant.genus, 'Orchidaceae')
        self.assertEqual(plant.species, 'cattleya')
        self.assertTrue(plant.is_active)
        self.assertIsNotNone(plant.created_at)
        self.assertIsNotNone(plant.updated_at)
    
    def test_plant_str_representation(self):
        """Test plant string representation."""
        plant = Plant.objects.create(**self.plant_data)
        expected = "Orchidaceae cattleya - Vivero Principal/Mesa 1/Pared A"
        self.assertEqual(str(plant), expected)
    
    def test_plant_full_scientific_name(self):
        """Test full scientific name property."""
        plant = Plant.objects.create(**self.plant_data)
        self.assertEqual(plant.full_scientific_name, "Orchidaceae cattleya")
    
    def test_plant_location_property(self):
        """Test location property."""
        plant = Plant.objects.create(**self.plant_data)
        self.assertEqual(plant.location, "Vivero Principal/Mesa 1/Pared A")
    
    def test_plant_unique_constraint(self):
        """Test unique constraint on plant location."""
        Plant.objects.create(**self.plant_data)
        with self.assertRaises(IntegrityError):
            Plant.objects.create(**self.plant_data)
    
    def test_plant_clean_method(self):
        """Test plant clean method formatting."""
        plant = Plant(**self.plant_data)
        plant.genus = ' orchidaceae '
        plant.species = ' CATTLEYA '
        plant.clean()
        self.assertEqual(plant.genus, 'Orchidaceae')
        self.assertEqual(plant.species, 'cattleya')


class PollinationTypeModelTest(TestCase):
    """Test cases for PollinationType model."""
    
    def test_self_pollination_type_creation(self):
        """Test Self pollination type creation."""
        pollination_type = PollinationType.objects.create(
            name='Self',
            description='Autopolinización de la misma planta'
        )
        self.assertEqual(pollination_type.name, 'Self')
        self.assertFalse(pollination_type.requires_father_plant)
        self.assertFalse(pollination_type.allows_different_species)
        self.assertEqual(pollination_type.maturation_days, 120)
    
    def test_sibling_pollination_type_creation(self):
        """Test Sibling pollination type creation."""
        pollination_type = PollinationType.objects.create(
            name='Sibling',
            description='Polinización entre plantas hermanas'
        )
        self.assertEqual(pollination_type.name, 'Sibling')
        self.assertTrue(pollination_type.requires_father_plant)
        self.assertFalse(pollination_type.allows_different_species)
    
    def test_hybrid_pollination_type_creation(self):
        """Test Híbrido pollination type creation."""
        pollination_type = PollinationType.objects.create(
            name='Híbrido',
            description='Hibridación entre especies diferentes'
        )
        self.assertEqual(pollination_type.name, 'Híbrido')
        self.assertTrue(pollination_type.requires_father_plant)
        self.assertTrue(pollination_type.allows_different_species)
    
    def test_pollination_type_str_representation(self):
        """Test pollination type string representation."""
        pollination_type = PollinationType.objects.create(
            name='Self',
            description='Autopolinización'
        )
        expected = "Self - Autopolinización"
        self.assertEqual(str(pollination_type), expected)
    
    def test_pollination_type_unique_constraint(self):
        """Test unique constraint on pollination type name."""
        PollinationType.objects.create(name='Self', description='Test')
        with self.assertRaises(IntegrityError):
            PollinationType.objects.create(name='Self', description='Test 2')


class ClimateConditionModelTest(TestCase):
    """Test cases for ClimateCondition model."""
    
    def test_climate_condition_creation(self):
        """Test climate condition creation."""
        climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.5,
            humidity=60,
            wind_speed=5.0,
            notes='Condiciones ideales para polinización'
        )
        self.assertEqual(climate.weather, 'Soleado')
        self.assertEqual(climate.temperature, 25.5)
        self.assertEqual(climate.humidity, 60)
        self.assertEqual(climate.wind_speed, 5.0)
    
    def test_climate_condition_str_representation(self):
        """Test climate condition string representation."""
        climate = ClimateCondition.objects.create(
            weather='Nublado',
            temperature=20.0
        )
        expected = "Nublado - 20.0°C"
        self.assertEqual(str(climate), expected)
    
    def test_climate_condition_without_temperature(self):
        """Test climate condition string without temperature."""
        climate = ClimateCondition.objects.create(weather='Lluvioso')
        self.assertEqual(str(climate), "Lluvioso")
    
    def test_climate_condition_humidity_validation(self):
        """Test humidity validation."""
        climate = ClimateCondition(weather='Soleado', humidity=150)
        with self.assertRaises(ValidationError):
            climate.clean()
        
        climate.humidity = -10
        with self.assertRaises(ValidationError):
            climate.clean()
    
    def test_climate_condition_wind_speed_validation(self):
        """Test wind speed validation."""
        climate = ClimateCondition(weather='Soleado', wind_speed=-5.0)
        with self.assertRaises(ValidationError):
            climate.clean()


class PollinationRecordModelTest(TestCase):
    """Test cases for PollinationRecord model."""
    
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
    
    def test_self_pollination_record_creation(self):
        """Test Self pollination record creation."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        self.assertEqual(record.pollination_type.name, 'Self')
        self.assertIsNone(record.father_plant)
        self.assertIsNotNone(record.estimated_maturation_date)
        self.assertFalse(record.maturation_confirmed)
    
    def test_sibling_pollination_record_creation(self):
        """Test Sibling pollination record creation."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.sibling_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            father_plant=self.father_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=3
        )
        self.assertEqual(record.pollination_type.name, 'Sibling')
        self.assertIsNotNone(record.father_plant)
        self.assertIsNotNone(record.estimated_maturation_date)
    
    def test_estimated_maturation_date_calculation(self):
        """Test automatic calculation of estimated maturation date."""
        pollination_date = date.today()
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=pollination_date,
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        expected_date = pollination_date + timedelta(days=120)
        self.assertEqual(record.estimated_maturation_date, expected_date)
    
    def test_future_date_validation(self):
        """Test validation of future pollination dates."""
        future_date = date.today() + timedelta(days=1)
        record = PollinationRecord(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=future_date,
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        with self.assertRaises(ValidationError):
            record.clean()
    
    def test_self_pollination_validation(self):
        """Test Self pollination validation rules."""
        # Should not allow father plant for Self pollination
        record = PollinationRecord(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            father_plant=self.father_plant,  # This should cause validation error
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        with self.assertRaises(ValidationError):
            record.clean()
    
    def test_sibling_pollination_validation(self):
        """Test Sibling pollination validation rules."""
        # Should require father plant for Sibling pollination
        record = PollinationRecord(
            responsible=self.user,
            pollination_type=self.sibling_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            # father_plant=None,  # This should cause validation error
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        with self.assertRaises(ValidationError):
            record.clean()
    
    def test_hybrid_pollination_validation(self):
        """Test Híbrido pollination validation rules."""
        # Should require father plant for Hybrid pollination
        record = PollinationRecord(
            responsible=self.user,
            pollination_type=self.hybrid_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            # father_plant=None,  # This should cause validation error
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        with self.assertRaises(ValidationError):
            record.clean()
    
    def test_pollination_record_str_representation(self):
        """Test pollination record string representation."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        expected = f"Self - Orchidaceae cattleya - {date.today()}"
        self.assertEqual(str(record), expected)
    
    def test_is_maturation_overdue(self):
        """Test maturation overdue check."""
        past_date = date.today() - timedelta(days=150)
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=past_date,
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        self.assertTrue(record.is_maturation_overdue())
    
    def test_days_to_maturation(self):
        """Test days to maturation calculation."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        self.assertEqual(record.days_to_maturation(), 120)
    
    def test_confirm_maturation(self):
        """Test maturation confirmation."""
        record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        confirmation_date = date.today()
        record.confirm_maturation(confirmation_date)
        
        self.assertTrue(record.maturation_confirmed)
        self.assertEqual(record.maturation_confirmed_date, confirmation_date)
        self.assertTrue(record.is_successful)
