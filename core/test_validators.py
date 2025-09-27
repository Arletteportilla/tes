"""
Tests for custom validators in the core module.
"""

from datetime import date, datetime, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .validators import (
    DateValidators, DuplicateValidators, PollinationValidators,
    GerminationValidators, NumericValidators, StringValidators,
    not_future_date_validator, positive_integer_validator,
    percentage_validator, temperature_validator
)

User = get_user_model()


class DateValidatorsTest(TestCase):
    """Test cases for date validators."""
    
    def test_validate_not_future_date_valid(self):
        """Test that past and present dates are valid."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Should not raise exception
        DateValidators.validate_not_future_date(today)
        DateValidators.validate_not_future_date(yesterday)
        DateValidators.validate_not_future_date(None)  # None should be allowed
    
    def test_validate_not_future_date_invalid(self):
        """Test that future dates raise ValidationError."""
        tomorrow = date.today() + timedelta(days=1)
        
        with self.assertRaises(ValidationError) as cm:
            DateValidators.validate_not_future_date(tomorrow)
        
        self.assertEqual(cm.exception.code, 'future_date_not_allowed')
        self.assertIn('no puede ser una fecha futura', str(cm.exception))
    
    def test_validate_not_future_date_with_datetime(self):
        """Test that datetime objects are properly converted."""
        future_datetime = datetime.now() + timedelta(days=1)
        
        with self.assertRaises(ValidationError):
            DateValidators.validate_not_future_date(future_datetime)
    
    def test_validate_date_range_valid(self):
        """Test valid date ranges."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Should not raise exception
        DateValidators.validate_date_range(start_date, end_date)
        DateValidators.validate_date_range(start_date, start_date)  # Same date
        DateValidators.validate_date_range(None, end_date)  # None values
        DateValidators.validate_date_range(start_date, None)
    
    def test_validate_date_range_invalid(self):
        """Test invalid date ranges."""
        start_date = date(2024, 1, 31)
        end_date = date(2024, 1, 1)
        
        with self.assertRaises(ValidationError) as cm:
            DateValidators.validate_date_range(start_date, end_date)
        
        self.assertEqual(cm.exception.code, 'invalid_date_range')
    
    def test_validate_minimum_date_difference_valid(self):
        """Test valid date differences."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 8)  # 7 days difference
        
        # Should not raise exception
        DateValidators.validate_minimum_date_difference(start_date, end_date, 7)
        DateValidators.validate_minimum_date_difference(start_date, end_date, 5)
    
    def test_validate_minimum_date_difference_invalid(self):
        """Test insufficient date differences."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)  # 4 days difference
        
        with self.assertRaises(ValidationError) as cm:
            DateValidators.validate_minimum_date_difference(start_date, end_date, 7)
        
        self.assertEqual(cm.exception.code, 'insufficient_date_difference')


class DuplicateValidatorsTest(TestCase):
    """Test cases for duplicate validators."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_validate_unique_combination_valid(self):
        """Test unique combination validation with no duplicates."""
        # Should not raise exception when no duplicates exist
        DuplicateValidators.validate_unique_combination(
            User, 
            {'username': 'newuser', 'email': 'new@example.com'}
        )
    
    def test_validate_unique_combination_duplicate(self):
        """Test unique combination validation with duplicates."""
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_unique_combination(
                User,
                {'username': 'testuser'}
            )
        
        self.assertEqual(cm.exception.code, 'duplicate_record')
    
    def test_validate_unique_combination_exclude_id(self):
        """Test unique combination validation excluding specific ID."""
        # Should not raise exception when excluding the existing record
        DuplicateValidators.validate_unique_combination(
            User,
            {'username': 'testuser'},
            exclude_id=self.user.id
        )
    
    def test_validate_pollination_duplicate_enhanced(self):
        """Test enhanced pollination duplicate validation."""
        from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord
        
        # Create test data
        plant1 = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero1',
            mesa='Mesa1',
            pared='Pared1'
        )
        
        plant2 = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero1',
            mesa='Mesa2',
            pared='Pared1'
        )
        
        pollination_type = PollinationType.objects.create(
            name='Sibling',
            description='Test'
        )
        
        climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0
        )
        
        # Create existing record
        existing_record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=pollination_type,
            pollination_date=date.today(),
            mother_plant=plant1,
            father_plant=plant2,
            new_plant=plant1,
            climate_condition=climate,
            capsules_quantity=5
        )
        
        # Test duplicate detection
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_pollination_duplicate(
                self.user, date.today(), plant1, plant2, pollination_type
            )
        
        self.assertEqual(cm.exception.code, 'duplicate_pollination')
        self.assertIn('Sibling', str(cm.exception))
        self.assertIn('cattleya', str(cm.exception))
    
    def test_validate_germination_duplicate_enhanced(self):
        """Test enhanced germination duplicate validation."""
        from pollination.models import Plant
        from germination.models import SeedSource, GerminationCondition, GerminationRecord
        
        # Create test data
        plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero1',
            mesa='Mesa1',
            pared='Pared1'
        )
        
        seed_source = SeedSource.objects.create(
            name='Test Source',
            source_type='Otra fuente',
            external_supplier='Test Supplier'
        )
        
        germination_condition = GerminationCondition.objects.create(
            climate='Controlado',
            substrate='Turba',
            location='Test Location'
        )
        
        # Create existing record
        existing_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today(),
            plant=plant,
            seed_source=seed_source,
            germination_condition=germination_condition,
            seeds_planted=10
        )
        
        # Test duplicate detection
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_germination_duplicate(
                self.user, date.today(), plant, seed_source
            )
        
        self.assertEqual(cm.exception.code, 'duplicate_germination')
        self.assertIn('cattleya', str(cm.exception))
        self.assertIn('Test Source', str(cm.exception))
    
    def test_validate_plant_duplicate(self):
        """Test plant duplicate validation."""
        from pollination.models import Plant
        
        # Create existing plant
        existing_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero1',
            mesa='Mesa1',
            pared='Pared1'
        )
        
        # Test duplicate detection
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_plant_duplicate(
                'Orchidaceae', 'cattleya', 'Vivero1', 'Mesa1', 'Pared1'
            )
        
        self.assertEqual(cm.exception.code, 'duplicate_plant')
        self.assertIn('Orchidaceae cattleya', str(cm.exception))
        self.assertIn('Vivero1/Mesa1/Pared1', str(cm.exception))
    
    def test_validate_user_duplicate(self):
        """Test user duplicate validation."""
        # Test username duplicate
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_user_duplicate(username='testuser')
        
        self.assertEqual(cm.exception.code, 'duplicate_user')
        
        # Test email duplicate
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_user_duplicate(email='test@example.com')
        
        self.assertEqual(cm.exception.code, 'duplicate_user')
    
    def test_validate_seed_source_duplicate(self):
        """Test seed source duplicate validation."""
        from germination.models import SeedSource
        
        # Create existing seed source
        existing_source = SeedSource.objects.create(
            name='Test Source',
            source_type='Otra fuente',
            external_supplier='Test Supplier'
        )
        
        # Test duplicate detection
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_seed_source_duplicate(
                'Test Source', 'Otra fuente'
            )
        
        self.assertEqual(cm.exception.code, 'duplicate_seed_source')
        self.assertIn('Test Source', str(cm.exception))
        self.assertIn('Otra fuente', str(cm.exception))


class PollinationValidatorsTest(TestCase):
    """Test cases for pollination validators."""
    
    def setUp(self):
        """Set up test data."""
        from pollination.models import Plant, PollinationType
        
        self.plant1 = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero1',
            mesa='Mesa1',
            pared='Pared1'
        )
        
        self.plant2 = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero1',
            mesa='Mesa2',
            pared='Pared1'
        )
        
        self.plant3 = Plant.objects.create(
            genus='Orchidaceae',
            species='laelia',
            vivero='Vivero1',
            mesa='Mesa3',
            pared='Pared1'
        )
        
        self.self_type, _ = PollinationType.objects.get_or_create(
            name='Self',
            defaults={'description': 'Autopolinización'}
        )
        
        self.sibling_type, _ = PollinationType.objects.get_or_create(
            name='Sibling',
            defaults={'description': 'Polinización entre hermanos'}
        )
        
        self.hybrid_type, _ = PollinationType.objects.get_or_create(
            name='Híbrido',
            defaults={'description': 'Hibridación'}
        )
    
    def test_validate_plant_compatibility_self_valid(self):
        """Test valid self pollination."""
        # Should not raise exception
        PollinationValidators.validate_plant_compatibility(
            self.plant1, None, self.self_type
        )
        PollinationValidators.validate_plant_compatibility(
            self.plant1, self.plant1, self.self_type
        )
    
    def test_validate_plant_compatibility_self_invalid(self):
        """Test invalid self pollination."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_plant_compatibility(
                self.plant1, self.plant2, self.self_type
            )
        
        self.assertEqual(cm.exception.code, 'invalid_self_pollination')
    
    def test_validate_plant_compatibility_sibling_valid(self):
        """Test valid sibling pollination."""
        # Should not raise exception
        PollinationValidators.validate_plant_compatibility(
            self.plant1, self.plant2, self.sibling_type
        )
    
    def test_validate_plant_compatibility_sibling_no_father(self):
        """Test sibling pollination without father plant."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_plant_compatibility(
                self.plant1, None, self.sibling_type
            )
        
        self.assertEqual(cm.exception.code, 'missing_father_plant_sibling')
    
    def test_validate_plant_compatibility_sibling_different_species(self):
        """Test sibling pollination with different species."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_plant_compatibility(
                self.plant1, self.plant3, self.sibling_type
            )
        
        self.assertEqual(cm.exception.code, 'incompatible_plants_sibling')
    
    def test_validate_plant_compatibility_hybrid_valid(self):
        """Test valid hybrid pollination."""
        # Should not raise exception
        PollinationValidators.validate_plant_compatibility(
            self.plant1, self.plant3, self.hybrid_type
        )
    
    def test_validate_plant_compatibility_hybrid_no_father(self):
        """Test hybrid pollination without father plant."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_plant_compatibility(
                self.plant1, None, self.hybrid_type
            )
        
        self.assertEqual(cm.exception.code, 'missing_father_plant_hybrid')
    
    def test_validate_plant_compatibility_hybrid_same_species(self):
        """Test hybrid pollination with same species."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_plant_compatibility(
                self.plant1, self.plant2, self.hybrid_type
            )
        
        self.assertEqual(cm.exception.code, 'same_species_hybrid')
    
    def test_validate_plant_compatibility_no_mother(self):
        """Test validation without mother plant."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_plant_compatibility(
                None, self.plant2, self.self_type
            )
        
        self.assertEqual(cm.exception.code, 'missing_mother_plant')
    
    def test_validate_plant_compatibility_sibling_same_physical_plant(self):
        """Test sibling pollination with same physical plant."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_plant_compatibility(
                self.plant1, self.plant1, self.sibling_type
            )
        
        self.assertEqual(cm.exception.code, 'same_physical_plant_sibling')
    
    def test_validate_plant_compatibility_hybrid_same_physical_plant(self):
        """Test hybrid pollination with same physical plant."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_plant_compatibility(
                self.plant1, self.plant1, self.hybrid_type
            )
        
        self.assertEqual(cm.exception.code, 'same_physical_plant_hybrid')
    
    def test_validate_new_plant_compatibility_same_as_mother(self):
        """Test new plant same as mother validation."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_new_plant_compatibility(
                self.plant1, self.plant2, self.plant1, self.sibling_type
            )
        
        self.assertEqual(cm.exception.code, 'new_plant_same_as_mother')
    
    def test_validate_new_plant_compatibility_same_as_father(self):
        """Test new plant same as father validation."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_new_plant_compatibility(
                self.plant1, self.plant2, self.plant2, self.sibling_type
            )
        
        self.assertEqual(cm.exception.code, 'new_plant_same_as_father')
    
    def test_validate_pollination_timing_too_frequent(self):
        """Test pollination timing validation for frequent pollinations."""
        from pollination.models import PollinationRecord, ClimateCondition
        
        climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0
        )
        
        # Create recent pollination
        recent_date = date.today() - timedelta(days=3)
        PollinationRecord.objects.create(
            responsible=User.objects.create_user('user2', 'user2@test.com', 'pass'),
            pollination_type=self.self_type,
            pollination_date=recent_date,
            mother_plant=self.plant1,
            new_plant=self.plant2,
            climate_condition=climate,
            capsules_quantity=5
        )
        
        # Test validation for new pollination too soon
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_pollination_timing(
                date.today(), self.plant1
            )
        
        self.assertEqual(cm.exception.code, 'pollination_too_frequent')
    
    def test_validate_capsules_quantity_invalid(self):
        """Test capsules quantity validation with invalid values."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_capsules_quantity(
                0, self.plant1, self.self_type
            )
        
        self.assertEqual(cm.exception.code, 'invalid_capsules_quantity')
    
    def test_validate_capsules_quantity_excessive(self):
        """Test capsules quantity validation with excessive values."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_capsules_quantity(
                100, self.plant1, self.self_type
            )
        
        self.assertEqual(cm.exception.code, 'excessive_capsules_quantity')
    
    def test_validate_climate_conditions_missing(self):
        """Test climate conditions validation when missing."""
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_climate_conditions(
                None, self.self_type
            )
        
        self.assertEqual(cm.exception.code, 'missing_climate_condition')
    
    def test_validate_climate_conditions_suboptimal_temperature(self):
        """Test climate conditions validation with suboptimal temperature."""
        from pollination.models import ClimateCondition
        
        climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=10.0  # Too low
        )
        
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_climate_conditions(
                climate, self.self_type
            )
        
        self.assertEqual(cm.exception.code, 'suboptimal_temperature')
    
    def test_validate_climate_conditions_unsuitable_weather(self):
        """Test climate conditions validation with unsuitable weather."""
        from pollination.models import ClimateCondition
        
        climate = ClimateCondition.objects.create(
            weather='Lluvioso',
            temperature=25.0
        )
        
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_climate_conditions(
                climate, self.self_type
            )
        
        self.assertEqual(cm.exception.code, 'unsuitable_weather')


class GerminationValidatorsTest(TestCase):
    """Test cases for germination validators."""
    
    def test_validate_seedling_quantity_valid(self):
        """Test valid seedling quantities."""
        # Should not raise exception
        GerminationValidators.validate_seedling_quantity(10, 8)
        GerminationValidators.validate_seedling_quantity(10, 10)
        GerminationValidators.validate_seedling_quantity(10, 0)
    
    def test_validate_seedling_quantity_invalid(self):
        """Test invalid seedling quantities."""
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_seedling_quantity(10, 15)
        
        self.assertEqual(cm.exception.code, 'excessive_seedlings')
    
    def test_validate_transplant_date_valid(self):
        """Test valid transplant dates."""
        germination_date = date(2024, 1, 1)
        transplant_date = date(2024, 2, 1)  # 31 days later
        
        # Should not raise exception
        GerminationValidators.validate_transplant_date(germination_date, transplant_date)
    
    def test_validate_transplant_date_before_germination(self):
        """Test transplant date before germination."""
        germination_date = date(2024, 2, 1)
        transplant_date = date(2024, 1, 1)
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_transplant_date(germination_date, transplant_date)
        
        self.assertEqual(cm.exception.code, 'invalid_transplant_date')
    
    def test_validate_transplant_date_future(self):
        """Test future transplant date."""
        germination_date = date.today() - timedelta(days=30)
        transplant_date = date.today() + timedelta(days=1)
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_transplant_date(germination_date, transplant_date)
        
        self.assertEqual(cm.exception.code, 'future_transplant_date')
    
    def test_validate_transplant_date_too_early(self):
        """Test transplant date too early after germination."""
        germination_date = date.today() - timedelta(days=10)
        transplant_date = date.today()
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_transplant_date(germination_date, transplant_date)
        
        self.assertEqual(cm.exception.code, 'transplant_too_early')
    
    def test_validate_seedling_quantity_impossible_rate(self):
        """Test seedling quantity validation with impossible germination rate."""
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_seedling_quantity(10, 15)
        
        self.assertEqual(cm.exception.code, 'excessive_seedlings')
    
    def test_validate_seed_source_compatibility_unconfirmed_pollination(self):
        """Test seed source compatibility with unconfirmed pollination."""
        from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord
        from germination.models import SeedSource
        
        # Create pollination record (unconfirmed)
        plant = Plant.objects.create(
            genus='Test', species='test', vivero='V', mesa='M', pared='P'
        )
        
        pollination_type = PollinationType.objects.create(
            name='Self', description='Test'
        )
        
        climate = ClimateCondition.objects.create(
            weather='Soleado', temperature=25.0
        )
        
        pollination_record = PollinationRecord.objects.create(
            responsible=User.objects.create_user('user3', 'user3@test.com', 'pass'),
            pollination_type=pollination_type,
            pollination_date=date.today() - timedelta(days=100),
            mother_plant=plant,
            new_plant=plant,
            climate_condition=climate,
            capsules_quantity=5,
            maturation_confirmed=False  # Not confirmed
        )
        
        seed_source = SeedSource.objects.create(
            name='Test Source',
            source_type='Autopolinización',
            pollination_record=pollination_record
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_seed_source_compatibility(seed_source, plant)
        
        self.assertEqual(cm.exception.code, 'unconfirmed_pollination_source')
    
    def test_validate_germination_conditions_suboptimal_temperature(self):
        """Test germination conditions validation with suboptimal temperature."""
        from pollination.models import Plant
        from germination.models import GerminationCondition
        
        plant = Plant.objects.create(
            genus='Orchidaceae', species='test', vivero='V', mesa='M', pared='P'
        )
        
        condition = GerminationCondition.objects.create(
            climate='Controlado',
            substrate='Turba',
            location='Test',
            temperature=10.0  # Too low for Orchidaceae
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_germination_conditions(condition, plant)
        
        self.assertEqual(cm.exception.code, 'suboptimal_germination_temperature')
    
    def test_validate_transplant_timing_already_transplanted(self):
        """Test transplant timing validation for already transplanted record."""
        from pollination.models import Plant
        from germination.models import SeedSource, GerminationCondition, GerminationRecord
        
        plant = Plant.objects.create(
            genus='Test', species='test', vivero='V', mesa='M', pared='P'
        )
        
        seed_source = SeedSource.objects.create(
            name='Test', source_type='Otra fuente', external_supplier='Supplier'
        )
        
        condition = GerminationCondition.objects.create(
            climate='Controlado', substrate='Turba', location='Test'
        )
        
        record = GerminationRecord.objects.create(
            responsible=User.objects.create_user('user4', 'user4@test.com', 'pass'),
            germination_date=date.today() - timedelta(days=60),
            plant=plant,
            seed_source=seed_source,
            germination_condition=condition,
            seeds_planted=10,
            seedlings_germinated=8,
            transplant_confirmed=True  # Already transplanted
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_transplant_timing(record)
        
        self.assertEqual(cm.exception.code, 'already_transplanted')
    
    def test_validate_transplant_timing_no_seedlings(self):
        """Test transplant timing validation with no seedlings."""
        from pollination.models import Plant
        from germination.models import SeedSource, GerminationCondition, GerminationRecord
        
        plant = Plant.objects.create(
            genus='Test', species='test', vivero='V', mesa='M', pared='P'
        )
        
        seed_source = SeedSource.objects.create(
            name='Test', source_type='Otra fuente', external_supplier='Supplier'
        )
        
        condition = GerminationCondition.objects.create(
            climate='Controlado', substrate='Turba', location='Test'
        )
        
        record = GerminationRecord.objects.create(
            responsible=User.objects.create_user('user5', 'user5@test.com', 'pass'),
            germination_date=date.today() - timedelta(days=60),
            plant=plant,
            seed_source=seed_source,
            germination_condition=condition,
            seeds_planted=10,
            seedlings_germinated=0  # No seedlings
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_transplant_timing(record)
        
        self.assertEqual(cm.exception.code, 'no_seedlings_to_transplant')
    
    def test_validate_seed_viability_too_old(self):
        """Test seed viability validation with old seeds."""
        from germination.models import SeedSource
        
        old_date = date.today() - timedelta(days=400)  # Over 1 year
        seed_source = SeedSource.objects.create(
            name='Old Seeds',
            source_type='Autopolinización',
            collection_date=old_date
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_seed_viability(seed_source, date.today())
        
        self.assertEqual(cm.exception.code, 'seeds_too_old')
    
    def test_validate_seed_viability_not_viable(self):
        """Test seed viability validation with very old seeds."""
        from germination.models import SeedSource
        
        very_old_date = date.today() - timedelta(days=600)  # Way over limit (365 * 1.5 = 547.5)
        seed_source = SeedSource.objects.create(
            name='Very Old Seeds',
            source_type='Autopolinización',
            collection_date=very_old_date
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_seed_viability(seed_source, date.today())
        
        self.assertEqual(cm.exception.code, 'seeds_not_viable')


class NumericValidatorsTest(TestCase):
    """Test cases for numeric validators."""
    
    def test_validate_positive_integer_valid(self):
        """Test valid positive integers."""
        # Should not raise exception
        NumericValidators.validate_positive_integer(1, "test")
        NumericValidators.validate_positive_integer(100, "test")
        NumericValidators.validate_positive_integer(None, "test")  # None allowed
    
    def test_validate_positive_integer_invalid(self):
        """Test invalid positive integers."""
        with self.assertRaises(ValidationError) as cm:
            NumericValidators.validate_positive_integer(0, "test")
        
        self.assertEqual(cm.exception.code, 'invalid_positive_integer')
        
        with self.assertRaises(ValidationError):
            NumericValidators.validate_positive_integer(-1, "test")
        
        with self.assertRaises(ValidationError):
            NumericValidators.validate_positive_integer("not_int", "test")
    
    def test_validate_percentage_valid(self):
        """Test valid percentages."""
        # Should not raise exception
        NumericValidators.validate_percentage(0, "test")
        NumericValidators.validate_percentage(50, "test")
        NumericValidators.validate_percentage(100, "test")
        NumericValidators.validate_percentage(50.5, "test")
        NumericValidators.validate_percentage(None, "test")
    
    def test_validate_percentage_invalid(self):
        """Test invalid percentages."""
        with self.assertRaises(ValidationError) as cm:
            NumericValidators.validate_percentage(-1, "test")
        
        self.assertEqual(cm.exception.code, 'invalid_percentage')
        
        with self.assertRaises(ValidationError):
            NumericValidators.validate_percentage(101, "test")
    
    def test_validate_temperature_valid(self):
        """Test valid temperatures."""
        # Should not raise exception
        NumericValidators.validate_temperature(20)
        NumericValidators.validate_temperature(-10)
        NumericValidators.validate_temperature(50)
        NumericValidators.validate_temperature(None)
    
    def test_validate_temperature_invalid(self):
        """Test invalid temperatures."""
        with self.assertRaises(ValidationError) as cm:
            NumericValidators.validate_temperature(-60)
        
        self.assertEqual(cm.exception.code, 'invalid_temperature')
        
        with self.assertRaises(ValidationError):
            NumericValidators.validate_temperature(70)


class StringValidatorsTest(TestCase):
    """Test cases for string validators."""
    
    def test_validate_string_length_valid(self):
        """Test valid string lengths."""
        # Should not raise exception
        StringValidators.validate_string_length("test", "field", min_length=2, max_length=10)
        StringValidators.validate_string_length("", "field")  # Empty allowed if no min
        StringValidators.validate_string_length(None, "field")  # None allowed
    
    def test_validate_string_length_too_short(self):
        """Test string too short."""
        with self.assertRaises(ValidationError) as cm:
            StringValidators.validate_string_length("a", "field", min_length=3)
        
        self.assertEqual(cm.exception.code, 'string_too_short')
    
    def test_validate_string_length_too_long(self):
        """Test string too long."""
        with self.assertRaises(ValidationError) as cm:
            StringValidators.validate_string_length("toolongstring", "field", max_length=5)
        
        self.assertEqual(cm.exception.code, 'string_too_long')
    
    def test_validate_required_field_valid(self):
        """Test valid required fields."""
        # Should not raise exception
        StringValidators.validate_required_field("test", "field")
        StringValidators.validate_required_field("  test  ", "field")  # Whitespace trimmed
    
    def test_validate_required_field_invalid(self):
        """Test invalid required fields."""
        with self.assertRaises(ValidationError) as cm:
            StringValidators.validate_required_field(None, "field")
        
        self.assertEqual(cm.exception.code, 'required_field')
        
        with self.assertRaises(ValidationError):
            StringValidators.validate_required_field("", "field")
        
        with self.assertRaises(ValidationError):
            StringValidators.validate_required_field("   ", "field")


class DjangoFieldValidatorsTest(TestCase):
    """Test cases for Django field validators."""
    
    def test_not_future_date_validator(self):
        """Test Django field validator for future dates."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Should not raise exception
        not_future_date_validator(today)
        
        # Should raise exception
        with self.assertRaises(ValidationError):
            not_future_date_validator(tomorrow)
    
    def test_positive_integer_validator(self):
        """Test Django field validator for positive integers."""
        # Should not raise exception
        positive_integer_validator(5)
        
        # Should raise exception
        with self.assertRaises(ValidationError):
            positive_integer_validator(0)
    
    def test_percentage_validator(self):
        """Test Django field validator for percentages."""
        # Should not raise exception
        percentage_validator(50)
        
        # Should raise exception
        with self.assertRaises(ValidationError):
            percentage_validator(150)
    
    def test_temperature_validator(self):
        """Test Django field validator for temperatures."""
        # Should not raise exception
        temperature_validator(25.5)
        
        # Should raise exception
        with self.assertRaises(ValidationError):
            temperature_validator(-60)