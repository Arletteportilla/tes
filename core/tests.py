from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import models
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from .models import BaseModel, PermissionMixin
from .utils import ValidationUtils


User = get_user_model()


class TestBaseModel(TestCase):
    """Test cases for BaseModel abstract model."""
    
    def setUp(self):
        """Create a concrete model for testing BaseModel."""
        class TestModel(BaseModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'core'
        
        self.TestModel = TestModel
    
    def test_base_model_has_timestamps(self):
        """Test that BaseModel includes created_at and updated_at fields."""
        # Check that the fields exist
        self.assertTrue(hasattr(self.TestModel, 'created_at'))
        self.assertTrue(hasattr(self.TestModel, 'updated_at'))
        
        # Check field types
        created_field = self.TestModel._meta.get_field('created_at')
        updated_field = self.TestModel._meta.get_field('updated_at')
        
        self.assertIsInstance(created_field, models.DateTimeField)
        self.assertIsInstance(updated_field, models.DateTimeField)
        
        # Check auto_now settings
        self.assertTrue(created_field.auto_now_add)
        self.assertTrue(updated_field.auto_now)
    
    def test_base_model_str_method(self):
        """Test BaseModel __str__ method."""
        # Create a mock instance
        instance = Mock()
        instance.__class__.__name__ = 'TestModel'
        instance.pk = 123
        
        # Test the __str__ method
        result = BaseModel.__str__(instance)
        self.assertEqual(result, "TestModel - 123")


class TestPermissionMixin(TestCase):
    """Test cases for PermissionMixin."""
    
    def setUp(self):
        """Set up test data."""
        self.user = Mock()
        self.user.is_authenticated = True
        self.user.is_superuser = False
        
        # Mock role
        self.mock_role = Mock()
        self.mock_role.name = 'Polinizador'
        self.user.role = self.mock_role
    
    def test_has_role_permission_unauthenticated_user(self):
        """Test permission check for unauthenticated user."""
        self.user.is_authenticated = False
        result = PermissionMixin.has_role_permission(self.user, 'Polinizador')
        self.assertFalse(result)
    
    def test_has_role_permission_none_user(self):
        """Test permission check for None user."""
        result = PermissionMixin.has_role_permission(None, 'Polinizador')
        self.assertFalse(result)
    
    def test_has_role_permission_superuser(self):
        """Test permission check for superuser."""
        self.user.is_superuser = True
        result = PermissionMixin.has_role_permission(self.user, 'AnyRole')
        self.assertTrue(result)
    
    def test_has_role_permission_fallback_behavior(self):
        """Test permission check fallback when authentication models don't exist."""
        # Since authentication models don't exist yet, should return False
        result = PermissionMixin.has_role_permission(self.user, 'Polinizador')
        self.assertFalse(result)
        
        # Non-matching role should also return False
        result = PermissionMixin.has_role_permission(self.user, 'Administrador')
        self.assertFalse(result)
    
    def test_has_module_permission_fallback_behavior(self):
        """Test module permission fallback when authentication models don't exist."""
        # Since authentication models don't exist yet, should return False
        result = PermissionMixin.has_module_permission(self.user, 'pollination')
        self.assertFalse(result)
        
        result = PermissionMixin.has_module_permission(self.user, 'reports')
        self.assertFalse(result)
    
    def test_can_delete_record_fallback_behavior(self):
        """Test delete record permission fallback when authentication models don't exist."""
        # Since authentication models don't exist yet, should return False
        result = PermissionMixin.can_delete_record(self.user)
        self.assertFalse(result)
    
    def test_can_generate_reports_fallback_behavior(self):
        """Test generate reports permission fallback when authentication models don't exist."""
        # Since authentication models don't exist yet, should return False
        result = PermissionMixin.can_generate_reports(self.user)
        self.assertFalse(result)
    
    def test_permission_methods_with_superuser(self):
        """Test that superuser bypasses all permission checks."""
        self.user.is_superuser = True
        
        # All permission methods should return True for superuser
        self.assertTrue(PermissionMixin.has_role_permission(self.user, 'AnyRole'))
        self.assertTrue(PermissionMixin.has_module_permission(self.user, 'any_module'))
        self.assertTrue(PermissionMixin.can_delete_record(self.user))
        self.assertTrue(PermissionMixin.can_generate_reports(self.user))


class TestValidationUtils(TestCase):
    """Test cases for ValidationUtils."""
    
    def test_validate_not_future_date_valid_date(self):
        """Test validation with valid (past/present) date."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Should not raise exception
        ValidationUtils.validate_not_future_date(today)
        ValidationUtils.validate_not_future_date(yesterday)
    
    def test_validate_not_future_date_future_date(self):
        """Test validation with future date."""
        tomorrow = date.today() + timedelta(days=1)
        
        with self.assertRaises(ValidationError) as context:
            ValidationUtils.validate_not_future_date(tomorrow)
        
        self.assertIn("no puede ser una fecha futura", str(context.exception))
    
    def test_validate_not_future_date_datetime(self):
        """Test validation with datetime object."""
        future_datetime = datetime.now() + timedelta(days=1)
        
        with self.assertRaises(ValidationError):
            ValidationUtils.validate_not_future_date(future_datetime)
    
    def test_validate_not_future_date_none_value(self):
        """Test validation with None value."""
        # Should not raise exception
        ValidationUtils.validate_not_future_date(None)
    
    def test_validate_required_field_valid_value(self):
        """Test required field validation with valid value."""
        # Should not raise exception
        ValidationUtils.validate_required_field("valid value", "test_field")
        ValidationUtils.validate_required_field(123, "test_field")
    
    def test_validate_required_field_empty_values(self):
        """Test required field validation with empty values."""
        empty_values = [None, "", "   ", "\t\n"]
        
        for empty_value in empty_values:
            with self.assertRaises(ValidationError) as context:
                ValidationUtils.validate_required_field(empty_value, "test_field")
            
            self.assertIn("es obligatorio", str(context.exception))
    
    def test_validate_positive_integer_valid_values(self):
        """Test positive integer validation with valid values."""
        # Should not raise exception
        ValidationUtils.validate_positive_integer(1, "test_field")
        ValidationUtils.validate_positive_integer(100, "test_field")
    
    def test_validate_positive_integer_invalid_values(self):
        """Test positive integer validation with invalid values."""
        invalid_values = [0, -1, -100, "string", 1.5]
        
        for invalid_value in invalid_values:
            with self.assertRaises(ValidationError) as context:
                ValidationUtils.validate_positive_integer(invalid_value, "test_field")
            
            self.assertIn("número entero positivo", str(context.exception))
    
    def test_validate_positive_integer_none_value(self):
        """Test positive integer validation with None value."""
        # Should not raise exception
        ValidationUtils.validate_positive_integer(None, "test_field")
    
    def test_validate_duplicate_record(self):
        """Test duplicate record validation."""
        # Mock model class
        mock_model = Mock()
        mock_queryset = Mock()
        mock_model.objects.filter.return_value = mock_queryset
        mock_queryset.exclude.return_value = mock_queryset
        
        # Test with existing record
        mock_queryset.exists.return_value = True
        with self.assertRaises(ValidationError) as context:
            ValidationUtils.validate_duplicate_record(mock_model, name="test")
        
        self.assertIn("Ya existe un registro", str(context.exception))
        
        # Test with no existing record
        mock_queryset.exists.return_value = False
        # Should not raise exception
        ValidationUtils.validate_duplicate_record(mock_model, name="test")
    
    def test_validate_date_range_valid_range(self):
        """Test date range validation with valid range."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Should not raise exception
        ValidationUtils.validate_date_range(start_date, end_date)
        
        # Same dates should be valid
        ValidationUtils.validate_date_range(start_date, start_date)
    
    def test_validate_date_range_invalid_range(self):
        """Test date range validation with invalid range."""
        start_date = date(2024, 1, 31)
        end_date = date(2024, 1, 1)
        
        with self.assertRaises(ValidationError) as context:
            ValidationUtils.validate_date_range(start_date, end_date)
        
        self.assertIn("no puede ser posterior", str(context.exception))
    
    def test_validate_date_range_none_values(self):
        """Test date range validation with None values."""
        # Should not raise exception
        ValidationUtils.validate_date_range(None, None)
        ValidationUtils.validate_date_range(date.today(), None)
        ValidationUtils.validate_date_range(None, date.today())
    
    def test_validate_plant_compatibility_self_pollination(self):
        """Test plant compatibility for self pollination."""
        mother_plant = Mock()
        mother_plant.species = "species_a"
        
        # Valid self pollination (same plant)
        ValidationUtils.validate_plant_compatibility(mother_plant, mother_plant, "Self")
        
        # Valid self pollination (no father plant)
        ValidationUtils.validate_plant_compatibility(mother_plant, None, "Self")
        
        # Invalid self pollination (different plants)
        father_plant = Mock()
        father_plant.species = "species_a"
        with self.assertRaises(ValidationError):
            ValidationUtils.validate_plant_compatibility(mother_plant, father_plant, "Self")
    
    def test_validate_plant_compatibility_sibling_pollination(self):
        """Test plant compatibility for sibling pollination."""
        mother_plant = Mock()
        mother_plant.species = "species_a"
        
        father_plant = Mock()
        father_plant.species = "species_a"
        
        # Valid sibling pollination (same species)
        ValidationUtils.validate_plant_compatibility(mother_plant, father_plant, "Sibling")
        
        # Invalid sibling pollination (no father plant)
        with self.assertRaises(ValidationError):
            ValidationUtils.validate_plant_compatibility(mother_plant, None, "Sibling")
        
        # Invalid sibling pollination (different species)
        father_plant.species = "species_b"
        with self.assertRaises(ValidationError):
            ValidationUtils.validate_plant_compatibility(mother_plant, father_plant, "Sibling")
    
    def test_validate_plant_compatibility_hybrid_pollination(self):
        """Test plant compatibility for hybrid pollination."""
        mother_plant = Mock()
        mother_plant.species = "species_a"
        
        father_plant = Mock()
        father_plant.species = "species_b"
        
        # Valid hybrid pollination (different species)
        ValidationUtils.validate_plant_compatibility(mother_plant, father_plant, "Híbrido")
        
        # Valid hybrid pollination (same species)
        father_plant.species = "species_a"
        ValidationUtils.validate_plant_compatibility(mother_plant, father_plant, "Híbrido")
        
        # Invalid hybrid pollination (no father plant)
        with self.assertRaises(ValidationError):
            ValidationUtils.validate_plant_compatibility(mother_plant, None, "Híbrido")
    
    def test_validate_plant_compatibility_no_mother_plant(self):
        """Test plant compatibility with no mother plant."""
        with self.assertRaises(ValidationError):
            ValidationUtils.validate_plant_compatibility(None, None, "Self")
    
    def test_validate_plant_compatibility_invalid_type(self):
        """Test plant compatibility with invalid pollination type."""
        mother_plant = Mock()
        
        with self.assertRaises(ValidationError):
            ValidationUtils.validate_plant_compatibility(mother_plant, None, "InvalidType")
    
    def test_validate_string_length_valid_strings(self):
        """Test string length validation with valid strings."""
        # Should not raise exception
        ValidationUtils.validate_string_length("test", "field", min_length=2, max_length=10)
        ValidationUtils.validate_string_length("hello world", "field", max_length=20)
        ValidationUtils.validate_string_length("ab", "field", min_length=2)
    
    def test_validate_string_length_invalid_strings(self):
        """Test string length validation with invalid strings."""
        # Too short
        with self.assertRaises(ValidationError):
            ValidationUtils.validate_string_length("a", "field", min_length=2)
        
        # Too long
        with self.assertRaises(ValidationError):
            ValidationUtils.validate_string_length("very long string", "field", max_length=5)
    
    def test_validate_string_length_none_value(self):
        """Test string length validation with None value."""
        # Should not raise exception
        ValidationUtils.validate_string_length(None, "field", min_length=2, max_length=10)
