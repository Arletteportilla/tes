"""
Tests for specific error handling and enhanced validators.
Tests the new duplicate validators and pollination-type-specific validators.
"""

from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .validators import (
    DuplicateValidators, PollinationValidators, GerminationValidators
)
from .exceptions import (
    DuplicateRecordError, PlantCompatibilityError, InvalidPollinationTypeError,
    SeedSourceCompatibilityError, InvalidSeedlingQuantityError
)

User = get_user_model()


class SpecificDuplicateValidatorsTest(TestCase):
    """Test cases for specific duplicate validators."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_validate_pollination_duplicate_detailed_message(self):
        """Test pollination duplicate validation with detailed error message."""
        from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord
        
        # Create test data
        plant1 = Plant.objects.create(
            genus='Cattleya',
            species='mossiae',
            vivero='Vivero Principal',
            mesa='Mesa A',
            pared='Pared 1'
        )
        
        plant2 = Plant.objects.create(
            genus='Cattleya',
            species='mossiae',
            vivero='Vivero Principal',
            mesa='Mesa B',
            pared='Pared 1'
        )
        
        pollination_type = PollinationType.objects.create(
            name='Sibling',
            description='Polinización entre hermanos'
        )
        
        climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0,
            humidity=65
        )
        
        # Create existing record
        test_date = date(2024, 3, 15)
        existing_record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=pollination_type,
            pollination_date=test_date,
            mother_plant=plant1,
            father_plant=plant2,
            new_plant=plant1,
            climate_condition=climate,
            capsules_quantity=5
        )
        
        # Test duplicate detection with detailed message
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_pollination_duplicate(
                self.user, test_date, plant1, plant2, pollination_type
            )
        
        error_message = str(cm.exception)
        self.assertIn('Sibling', error_message)
        self.assertIn('Cattleya mossiae', error_message)
        self.assertIn('2024-03-15', error_message)
        self.assertIn('testuser', error_message)
    
    def test_validate_germination_duplicate_detailed_message(self):
        """Test germination duplicate validation with detailed error message."""
        from pollination.models import Plant
        from germination.models import SeedSource, GerminationCondition, GerminationRecord
        
        # Create test data
        plant = Plant.objects.create(
            genus='Dendrobium',
            species='nobile',
            vivero='Vivero Secundario',
            mesa='Mesa C',
            pared='Pared 2'
        )
        
        seed_source = SeedSource.objects.create(
            name='Semillas Premium',
            source_type='Híbrido',
            description='Semillas de alta calidad'
        )
        
        germination_condition = GerminationCondition.objects.create(
            climate='Invernadero',
            substrate='Musgo sphagnum',
            location='Sección A - Invernadero Principal'
        )
        
        # Create existing record
        test_date = date(2024, 4, 10)
        existing_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=test_date,
            plant=plant,
            seed_source=seed_source,
            germination_condition=germination_condition,
            seeds_planted=20,
            seedlings_germinated=15
        )
        
        # Test duplicate detection with detailed message
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_germination_duplicate(
                self.user, test_date, plant, seed_source
            )
        
        error_message = str(cm.exception)
        self.assertIn('Dendrobium nobile', error_message)
        self.assertIn('Semillas Premium', error_message)
        self.assertIn('2024-04-10', error_message)
        self.assertIn('testuser', error_message)
    
    def test_validate_plant_duplicate_location_specific(self):
        """Test plant duplicate validation with location-specific error."""
        from pollination.models import Plant
        
        # Create existing plant
        existing_plant = Plant.objects.create(
            genus='Phalaenopsis',
            species='amabilis',
            vivero='Vivero Especializado',
            mesa='Mesa Premium',
            pared='Pared Norte'
        )
        
        # Test duplicate detection
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_plant_duplicate(
                'Phalaenopsis', 'amabilis', 'Vivero Especializado', 'Mesa Premium', 'Pared Norte'
            )
        
        error_message = str(cm.exception)
        self.assertIn('Phalaenopsis amabilis', error_message)
        self.assertIn('Vivero Especializado/Mesa Premium/Pared Norte', error_message)
    
    def test_validate_user_duplicate_multiple_fields(self):
        """Test user duplicate validation with multiple field conflicts."""
        # Create another user with different username but same email
        User.objects.create_user(
            username='anotheruser',
            email='test@example.com',  # Same email
            password='testpass123'
        )
        
        # Test username duplicate
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_user_duplicate(username='testuser')
        
        errors = cm.exception.messages
        self.assertTrue(any('nombre de usuario' in error for error in errors))
        
        # Test email duplicate
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_user_duplicate(email='test@example.com')
        
        errors = cm.exception.messages
        self.assertTrue(any('correo electrónico' in error for error in errors))
    
    def test_validate_seed_source_duplicate_type_specific(self):
        """Test seed source duplicate validation with type-specific error."""
        from germination.models import SeedSource
        
        # Create existing seed source
        existing_source = SeedSource.objects.create(
            name='Fuente Especial',
            source_type='Autopolinización',
            description='Fuente de semillas de autopolinización'
        )
        
        # Test duplicate detection
        with self.assertRaises(ValidationError) as cm:
            DuplicateValidators.validate_seed_source_duplicate(
                'Fuente Especial', 'Autopolinización'
            )
        
        error_message = str(cm.exception)
        self.assertIn('Fuente Especial', error_message)
        self.assertIn('Autopolinización', error_message)


class SpecificPollinationValidatorsTest(TestCase):
    """Test cases for specific pollination validators."""
    
    def setUp(self):
        """Set up test data."""
        from pollination.models import Plant, PollinationType
        
        self.user = User.objects.create_user(
            username='pollinator',
            email='pollinator@example.com',
            password='testpass123'
        )
        
        # Create plants with specific characteristics
        self.orchid_cattleya_1 = Plant.objects.create(
            genus='Cattleya',
            species='mossiae',
            vivero='Vivero A',
            mesa='Mesa 1',
            pared='Pared A'
        )
        
        self.orchid_cattleya_2 = Plant.objects.create(
            genus='Cattleya',
            species='mossiae',
            vivero='Vivero A',
            mesa='Mesa 2',
            pared='Pared A'
        )
        
        self.orchid_dendrobium = Plant.objects.create(
            genus='Dendrobium',
            species='nobile',
            vivero='Vivero B',
            mesa='Mesa 1',
            pared='Pared B'
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
    
    def test_validate_pollination_timing_with_recent_pollination(self):
        """Test pollination timing validation with recent pollination history."""
        from pollination.models import ClimateCondition, PollinationRecord
        
        climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=24.0,
            humidity=60
        )
        
        # Create recent pollination (5 days ago)
        recent_date = date.today() - timedelta(days=5)
        PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.self_type,
            pollination_date=recent_date,
            mother_plant=self.orchid_cattleya_1,
            new_plant=self.orchid_cattleya_2,
            climate_condition=climate,
            capsules_quantity=3
        )
        
        # Test validation for new pollination too soon
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_pollination_timing(
                date.today(), self.orchid_cattleya_1
            )
        
        self.assertEqual(cm.exception.code, 'pollination_too_frequent')
        error_message = str(cm.exception)
        self.assertIn('5 días', error_message)
        self.assertIn('7 días', error_message)
    
    def test_validate_capsules_quantity_genus_specific_limits(self):
        """Test capsules quantity validation with genus-specific limits."""
        # Test Cattleya limit (should be 15)
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_capsules_quantity(
                20, self.orchid_cattleya_1, self.self_type
            )
        
        self.assertEqual(cm.exception.code, 'excessive_capsules_quantity')
        error_message = str(cm.exception)
        self.assertIn('20', error_message)
        self.assertIn('Cattleya', error_message)
        self.assertIn('15', error_message)
        
        # Test Dendrobium limit (should be 25)
        # This should not raise an error
        try:
            PollinationValidators.validate_capsules_quantity(
                20, self.orchid_dendrobium, self.self_type
            )
        except ValidationError:
            self.fail("Dendrobium should allow 20 capsules")
    
    def test_validate_climate_conditions_comprehensive(self):
        """Test comprehensive climate conditions validation."""
        from pollination.models import ClimateCondition
        
        # Test suboptimal humidity
        climate_low_humidity = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0,
            humidity=30  # Too low
        )
        
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_climate_conditions(
                climate_low_humidity, self.self_type
            )
        
        self.assertEqual(cm.exception.code, 'suboptimal_humidity')
        error_message = str(cm.exception)
        self.assertIn('30%', error_message)
        self.assertIn('40-80%', error_message)
        
        # Test high temperature
        climate_high_temp = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=40.0,  # Too high
            humidity=65
        )
        
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_climate_conditions(
                climate_high_temp, self.self_type
            )
        
        self.assertEqual(cm.exception.code, 'suboptimal_temperature')
        error_message = str(cm.exception)
        self.assertIn('40.0°C', error_message)
        self.assertIn('15-35°C', error_message)
    
    def test_validate_new_plant_compatibility_hybrid_genus_check(self):
        """Test new plant compatibility for hybrid with genus validation."""
        from pollination.models import Plant
        
        # Create a plant from completely different genus
        different_genus_plant = Plant.objects.create(
            genus='Vanilla',  # Different genus
            species='planifolia',
            vivero='Vivero C',
            mesa='Mesa 1',
            pared='Pared C'
        )
        
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_new_plant_compatibility(
                self.orchid_cattleya_1,  # Cattleya
                self.orchid_dendrobium,  # Dendrobium
                different_genus_plant,   # Vanilla
                self.hybrid_type
            )
        
        self.assertEqual(cm.exception.code, 'incompatible_new_plant_hybrid')
        error_message = str(cm.exception)
        self.assertIn('mismo género', error_message)


class SpecificGerminationValidatorsTest(TestCase):
    """Test cases for specific germination validators."""
    
    def setUp(self):
        """Set up test data."""
        from pollination.models import Plant
        from germination.models import SeedSource, GerminationCondition
        
        self.user = User.objects.create_user(
            username='germinator',
            email='germinator@example.com',
            password='testpass123'
        )
        
        self.orchid_plant = Plant.objects.create(
            genus='Cattleya',
            species='trianae',
            vivero='Vivero Germinación',
            mesa='Mesa G1',
            pared='Pared G1'
        )
        
        self.seed_source = SeedSource.objects.create(
            name='Semillas Cattleya Premium',
            source_type='Sibling',
            collection_date=date.today() - timedelta(days=30)
        )
        
        self.germination_condition = GerminationCondition.objects.create(
            climate='Laboratorio',
            substrate='Turba',
            location='Lab A - Sección Orquídeas',
            temperature=24.0,
            humidity=75,
            light_hours=12
        )
    
    def test_validate_germination_conditions_genus_specific_temperature(self):
        """Test germination conditions validation with genus-specific temperature ranges."""
        from germination.models import GerminationCondition
        
        # Test temperature too low for Cattleya (should be 20-26°C)
        cold_condition = GerminationCondition.objects.create(
            climate='Controlado',
            substrate='Turba',
            location='Test Location',
            temperature=15.0  # Too low for Cattleya
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_germination_conditions(
                cold_condition, self.orchid_plant
            )
        
        self.assertEqual(cm.exception.code, 'suboptimal_germination_temperature')
        error_message = str(cm.exception)
        self.assertIn('15.0°C', error_message)
        self.assertIn('Cattleya', error_message)
        self.assertIn('20-26°C', error_message)
    
    def test_validate_seed_viability_source_type_specific(self):
        """Test seed viability validation with source-type-specific limits."""
        from germination.models import SeedSource
        
        # Test external source with longer storage limit
        external_source = SeedSource.objects.create(
            name='Semillas Externas',
            source_type='Otra fuente',
            external_supplier='Proveedor Internacional',
            collection_date=date.today() - timedelta(days=500)  # 500 days old
        )
        
        # Should not raise error for external source (limit is 730 days)
        try:
            GerminationValidators.validate_seed_viability(
                external_source, date.today()
            )
        except ValidationError:
            self.fail("External source should allow longer storage")
        
        # Test internal source with shorter limit
        internal_source = SeedSource.objects.create(
            name='Semillas Internas',
            source_type='Autopolinización',
            collection_date=date.today() - timedelta(days=400)  # 400 days old
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_seed_viability(
                internal_source, date.today()
            )
        
        self.assertEqual(cm.exception.code, 'seeds_too_old')
        error_message = str(cm.exception)
        self.assertIn('400 días', error_message)
        self.assertIn('365 días', error_message)
    
    def test_validate_transplant_timing_early_warning(self):
        """Test transplant timing validation with early warning system."""
        from germination.models import GerminationRecord
        
        # Create record with estimated transplant date in future
        future_transplant_date = date.today() + timedelta(days=20)
        record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today() - timedelta(days=70),
            estimated_transplant_date=future_transplant_date,
            plant=self.orchid_plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=15,
            seedlings_germinated=12
        )
        
        # Test transplanting too early (more than 14 days before estimated date)
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_transplant_timing(record, date.today())
        
        self.assertEqual(cm.exception.code, 'transplant_too_early')
        error_message = str(cm.exception)
        self.assertIn('20 días', error_message)
        self.assertIn('muy temprano', error_message)
    
    def test_validate_germination_conditions_comprehensive_ranges(self):
        """Test comprehensive germination conditions validation with all parameters."""
        from germination.models import GerminationCondition
        
        # Test humidity too high
        high_humidity_condition = GerminationCondition.objects.create(
            climate='Invernadero',
            substrate='Vermiculita',
            location='Test Location',
            temperature=24.0,
            humidity=95,  # Too high
            light_hours=12
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_germination_conditions(
                high_humidity_condition, self.orchid_plant
            )
        
        self.assertEqual(cm.exception.code, 'suboptimal_germination_humidity')
        error_message = str(cm.exception)
        self.assertIn('95%', error_message)
        self.assertIn('60-90%', error_message)
        
        # Test light hours too low
        low_light_condition = GerminationCondition.objects.create(
            climate='Controlado',
            substrate='Turba',
            location='Test Location',
            temperature=24.0,
            humidity=75,
            light_hours=6  # Too low
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_germination_conditions(
                low_light_condition, self.orchid_plant
            )
        
        self.assertEqual(cm.exception.code, 'suboptimal_light_hours')
        error_message = str(cm.exception)
        self.assertIn('6h', error_message)
        self.assertIn('8-16h', error_message)


class ErrorIntegrationTest(TestCase):
    """Integration tests for error handling across validators."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123'
        )
    
    def test_multiple_validation_errors_pollination(self):
        """Test handling multiple validation errors in pollination."""
        from pollination.models import Plant, PollinationType, ClimateCondition
        
        # Create plants
        plant1 = Plant.objects.create(
            genus='Cattleya', species='mossiae',
            vivero='V1', mesa='M1', pared='P1'
        )
        
        plant2 = Plant.objects.create(
            genus='Dendrobium', species='nobile',  # Different genus
            vivero='V1', mesa='M2', pared='P1'
        )
        
        sibling_type = PollinationType.objects.create(
            name='Sibling', description='Test'
        )
        
        # Test plant compatibility (should fail for different genus in Sibling)
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_plant_compatibility(
                plant1, plant2, sibling_type
            )
        
        self.assertEqual(cm.exception.code, 'incompatible_plants_sibling')
        
        # Test capsules quantity (should fail for excessive amount)
        with self.assertRaises(ValidationError) as cm:
            PollinationValidators.validate_capsules_quantity(
                100, plant1, sibling_type
            )
        
        self.assertEqual(cm.exception.code, 'excessive_capsules_quantity')
    
    def test_multiple_validation_errors_germination(self):
        """Test handling multiple validation errors in germination."""
        from pollination.models import Plant
        from germination.models import SeedSource, GerminationCondition
        
        plant = Plant.objects.create(
            genus='Cattleya', species='trianae',
            vivero='V1', mesa='M1', pared='P1'
        )
        
        # Test seed viability (very old seeds)
        old_seed_source = SeedSource.objects.create(
            name='Very Old Seeds',
            source_type='Autopolinización',
            collection_date=date.today() - timedelta(days=700)  # Way too old (365 * 1.5 = 547.5)
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_seed_viability(
                old_seed_source, date.today()
            )
        
        self.assertEqual(cm.exception.code, 'seeds_not_viable')
        
        # Test germination conditions (bad temperature)
        bad_condition = GerminationCondition.objects.create(
            climate='Controlado',
            substrate='Turba',
            location='Test',
            temperature=10.0  # Too low for Cattleya
        )
        
        with self.assertRaises(ValidationError) as cm:
            GerminationValidators.validate_germination_conditions(
                bad_condition, plant
            )
        
        self.assertEqual(cm.exception.code, 'suboptimal_germination_temperature')