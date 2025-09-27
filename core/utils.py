from datetime import date, datetime
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ValidationUtils:
    """
    Utility class for shared validation functions across the application.
    Provides common validation methods for dates, duplicates, and business rules.
    """
    
    @staticmethod
    def validate_not_future_date(value, field_name="fecha"):
        """
        Validate that a date is not in the future.
        
        Args:
            value: Date or datetime object to validate
            field_name: Name of the field for error messages
            
        Raises:
            ValidationError: If the date is in the future
        """
        if not value:
            return
            
        # Convert datetime to date if necessary
        if isinstance(value, datetime):
            value = value.date()
            
        today = date.today()
        if value > today:
            raise ValidationError(
                _(f"La {field_name} no puede ser una fecha futura. Fecha máxima permitida: {today}")
            )
    
    @staticmethod
    def validate_required_field(value, field_name):
        """
        Validate that a required field has a value.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            
        Raises:
            ValidationError: If the field is empty or None
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(
                _(f"El campo {field_name} es obligatorio")
            )
    
    @staticmethod
    def validate_positive_integer(value, field_name):
        """
        Validate that a value is a positive integer.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            
        Raises:
            ValidationError: If the value is not a positive integer
        """
        if value is None:
            return
            
        if not isinstance(value, int) or value <= 0:
            raise ValidationError(
                _(f"El campo {field_name} debe ser un número entero positivo")
            )
    
    @staticmethod
    def validate_duplicate_record(model_class, exclude_id=None, **kwargs):
        """
        Validate that a record with the given parameters doesn't already exist.
        
        Args:
            model_class: Django model class to check
            exclude_id: ID to exclude from the check (for updates)
            **kwargs: Field values to check for duplicates
            
        Raises:
            ValidationError: If a duplicate record exists
        """
        queryset = model_class.objects.filter(**kwargs)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
            
        if queryset.exists():
            field_names = ", ".join(kwargs.keys())
            raise ValidationError(
                _(f"Ya existe un registro con los mismos valores para: {field_names}")
            )
    
    @staticmethod
    def validate_date_range(start_date, end_date, start_field_name="fecha inicio", end_field_name="fecha fin"):
        """
        Validate that start date is before or equal to end date.
        
        Args:
            start_date: Start date to validate
            end_date: End date to validate
            start_field_name: Name of the start date field for error messages
            end_field_name: Name of the end date field for error messages
            
        Raises:
            ValidationError: If start date is after end date
        """
        if not start_date or not end_date:
            return
            
        # Convert datetime to date if necessary
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
            
        if start_date > end_date:
            raise ValidationError(
                _(f"La {start_field_name} no puede ser posterior a la {end_field_name}")
            )
    
    @staticmethod
    def validate_plant_compatibility(mother_plant, father_plant, pollination_type):
        """
        Validate plant compatibility based on pollination type.
        
        Args:
            mother_plant: Mother plant instance
            father_plant: Father plant instance (can be None for Self type)
            pollination_type: Type of pollination (Self, Sibling, Híbrido)
            
        Raises:
            ValidationError: If plants are not compatible for the pollination type
        """
        if not mother_plant:
            raise ValidationError(_("La planta madre es obligatoria"))
            
        if pollination_type == "Self":
            if father_plant and father_plant != mother_plant:
                raise ValidationError(
                    _("Para autopolinización, la planta padre debe ser la misma que la madre o no especificarse")
                )
        
        elif pollination_type == "Sibling":
            if not father_plant:
                raise ValidationError(_("Para polinización Sibling, la planta padre es obligatoria"))
            
            # For Sibling, both plants should be from the same progeny (same species)
            if mother_plant.species != father_plant.species:
                raise ValidationError(
                    _("Para polinización Sibling, ambas plantas deben ser de la misma especie")
                )
        
        elif pollination_type == "Híbrido":
            if not father_plant:
                raise ValidationError(_("Para hibridación, la planta padre es obligatoria"))
            
            # For Híbrido, plants can be from different species (no restriction)
            pass
        
        else:
            raise ValidationError(_("Tipo de polinización no válido"))
    
    @staticmethod
    def validate_string_length(value, field_name, min_length=None, max_length=None):
        """
        Validate string length constraints.
        
        Args:
            value: String value to validate
            field_name: Name of the field for error messages
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            
        Raises:
            ValidationError: If string length is outside allowed range
        """
        if not value:
            return
            
        length = len(value.strip())
        
        if min_length and length < min_length:
            raise ValidationError(
                _(f"El campo {field_name} debe tener al menos {min_length} caracteres")
            )
            
        if max_length and length > max_length:
            raise ValidationError(
                _(f"El campo {field_name} no puede tener más de {max_length} caracteres")
            )