from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import PollinationRecord, PollinationType, Plant, ClimateCondition
from core.validators import (
    DateValidators, DuplicateValidators, PollinationValidators,
    NumericValidators
)
from core.exceptions import (
    ValidationError as CustomValidationError,
    PlantCompatibilityError, DuplicateRecordError, FutureDateError
)


class PollinationService:
    """
    Service class for pollination business logic.
    Handles calculations and operations related to pollination records.
    """
    
    @staticmethod
    def calculate_maturation_date(pollination_date, pollination_type):
        """
        Calculate estimated maturation date based on pollination date and type.
        
        Args:
            pollination_date (date): Date when pollination was performed
            pollination_type (PollinationType): Type of pollination
            
        Returns:
            date: Estimated maturation date
        """
        if not isinstance(pollination_date, date):
            raise ValueError("pollination_date must be a date object")
        
        if not isinstance(pollination_type, PollinationType):
            raise ValueError("pollination_type must be a PollinationType instance")
        
        return pollination_date + timedelta(days=pollination_type.maturation_days)
    
    @staticmethod
    def get_maturation_status(pollination_record):
        """
        Get the maturation status of a pollination record.
        
        Args:
            pollination_record (PollinationRecord): The pollination record to check
            
        Returns:
            dict: Status information including days remaining, overdue status, etc.
        """
        if not pollination_record.estimated_maturation_date:
            return {
                'status': 'unknown',
                'days_remaining': None,
                'is_overdue': False,
                'message': 'Fecha de maduración no calculada'
            }
        
        today = date.today()
        days_remaining = (pollination_record.estimated_maturation_date - today).days
        
        if pollination_record.maturation_confirmed:
            return {
                'status': 'confirmed',
                'days_remaining': 0,
                'is_overdue': False,
                'message': f'Maduración confirmada el {pollination_record.maturation_confirmed_date}'
            }
        
        if days_remaining > 7:
            return {
                'status': 'pending',
                'days_remaining': days_remaining,
                'is_overdue': False,
                'message': f'Faltan {days_remaining} días para la maduración estimada'
            }
        elif days_remaining > 0:
            return {
                'status': 'approaching',
                'days_remaining': days_remaining,
                'is_overdue': False,
                'message': f'Maduración próxima en {days_remaining} días'
            }
        elif days_remaining == 0:
            return {
                'status': 'due_today',
                'days_remaining': 0,
                'is_overdue': False,
                'message': 'Maduración estimada para hoy'
            }
        else:
            return {
                'status': 'overdue',
                'days_remaining': days_remaining,
                'is_overdue': True,
                'message': f'Maduración vencida hace {abs(days_remaining)} días'
            }
    
    @staticmethod
    def get_records_by_maturation_status(user=None, status_filter=None):
        """
        Get pollination records filtered by maturation status.
        
        Args:
            user (CustomUser, optional): Filter by responsible user
            status_filter (str, optional): Filter by status ('pending', 'approaching', 'overdue', etc.)
            
        Returns:
            QuerySet: Filtered pollination records
        """
        queryset = PollinationRecord.objects.select_related(
            'responsible', 'pollination_type', 'mother_plant', 'father_plant', 'new_plant'
        ).order_by('-pollination_date')
        
        if user:
            queryset = queryset.filter(responsible=user)
        
        if status_filter:
            today = date.today()
            
            if status_filter == 'pending':
                # More than 7 days remaining
                queryset = queryset.filter(
                    estimated_maturation_date__gt=today + timedelta(days=7),
                    maturation_confirmed=False
                )
            elif status_filter == 'approaching':
                # 1-7 days remaining
                queryset = queryset.filter(
                    estimated_maturation_date__gt=today,
                    estimated_maturation_date__lte=today + timedelta(days=7),
                    maturation_confirmed=False
                )
            elif status_filter == 'due_today':
                # Due today
                queryset = queryset.filter(
                    estimated_maturation_date=today,
                    maturation_confirmed=False
                )
            elif status_filter == 'overdue':
                # Past due date
                queryset = queryset.filter(
                    estimated_maturation_date__lt=today,
                    maturation_confirmed=False
                )
            elif status_filter == 'confirmed':
                # Already confirmed
                queryset = queryset.filter(maturation_confirmed=True)
        
        return queryset
    
    @staticmethod
    @transaction.atomic
    def confirm_maturation(pollination_record, confirmed_date=None, is_successful=True):
        """
        Confirm maturation of a pollination record.
        
        Args:
            pollination_record (PollinationRecord): Record to confirm
            confirmed_date (date, optional): Date of confirmation (defaults to today)
            is_successful (bool): Whether the pollination was successful
            
        Returns:
            PollinationRecord: Updated record
        """
        if pollination_record.maturation_confirmed:
            raise ValidationError("Esta polinización ya ha sido confirmada como madura")
        
        confirmation_date = confirmed_date or date.today()
        
        pollination_record.maturation_confirmed = True
        pollination_record.maturation_confirmed_date = confirmation_date
        pollination_record.is_successful = is_successful
        pollination_record.save()
        
        return pollination_record
    
    @staticmethod
    def get_success_statistics(user=None, date_from=None, date_to=None):
        """
        Get success statistics for pollination records.
        
        Args:
            user (CustomUser, optional): Filter by responsible user
            date_from (date, optional): Start date for filtering
            date_to (date, optional): End date for filtering
            
        Returns:
            dict: Statistics including success rate, total records, etc.
        """
        queryset = PollinationRecord.objects.all()
        
        if user:
            queryset = queryset.filter(responsible=user)
        
        if date_from:
            queryset = queryset.filter(pollination_date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(pollination_date__lte=date_to)
        
        total_records = queryset.count()
        confirmed_records = queryset.filter(maturation_confirmed=True).count()
        successful_records = queryset.filter(is_successful=True).count()
        overdue_records = queryset.filter(
            estimated_maturation_date__lt=date.today(),
            maturation_confirmed=False
        ).count()
        
        success_rate = (successful_records / confirmed_records * 100) if confirmed_records > 0 else 0
        confirmation_rate = (confirmed_records / total_records * 100) if total_records > 0 else 0
        
        return {
            'total_records': total_records,
            'confirmed_records': confirmed_records,
            'successful_records': successful_records,
            'overdue_records': overdue_records,
            'success_rate': round(success_rate, 2),
            'confirmation_rate': round(confirmation_rate, 2),
            'pending_confirmation': total_records - confirmed_records
        }


class ValidationService:
    """
    Service class for pollination validation logic.
    Handles validation rules specific to different pollination types.
    """
    
    @staticmethod
    def validate_pollination_data(data):
        """
        Validate pollination data before creating a record.
        
        Args:
            data (dict): Pollination data to validate
            
        Returns:
            dict: Validation result with errors if any
        """
        errors = {}
        
        try:
            # Validate required fields
            required_fields = [
                'responsible', 'pollination_type', 'pollination_date',
                'mother_plant', 'new_plant', 'climate_condition', 'capsules_quantity'
            ]
            
            for field in required_fields:
                if not data.get(field):
                    errors[field] = f'El campo {field} es requerido'
            
            # Validate date is not in the future using custom validator
            pollination_date = data.get('pollination_date')
            if pollination_date:
                try:
                    DateValidators.validate_not_future_date(pollination_date, "fecha de polinización")
                except ValidationError as e:
                    errors['pollination_date'] = str(e.message)
            
            # Validate capsules quantity using custom validator
            capsules_quantity = data.get('capsules_quantity')
            if capsules_quantity:
                try:
                    NumericValidators.validate_positive_integer(capsules_quantity, "cantidad de cápsulas")
                except ValidationError as e:
                    errors['capsules_quantity'] = str(e.message)
            
            # Validate plant relationships using custom validator
            pollination_type = data.get('pollination_type')
            mother_plant = data.get('mother_plant')
            father_plant = data.get('father_plant')
            
            if pollination_type and mother_plant:
                try:
                    PollinationValidators.validate_plant_compatibility(
                        mother_plant, father_plant, pollination_type
                    )
                except ValidationError as e:
                    errors['plant_compatibility'] = str(e.message)
            
            # Validate new plant compatibility
            new_plant = data.get('new_plant')
            if pollination_type and mother_plant and new_plant:
                try:
                    PollinationValidators.validate_new_plant_compatibility(
                        mother_plant, father_plant, new_plant, pollination_type
                    )
                except ValidationError as e:
                    errors['new_plant'] = str(e.message)
            
            # Check for duplicate records
            if all(data.get(field) for field in ['responsible', 'pollination_date', 'mother_plant', 'pollination_type']):
                try:
                    DuplicateValidators.validate_pollination_duplicate(
                        data['responsible'], data['pollination_date'],
                        data['mother_plant'], data.get('father_plant'),
                        data['pollination_type']
                    )
                except ValidationError as e:
                    errors['duplicate'] = str(e.message)
        
        except Exception as e:
            errors['general'] = f'Error de validación: {str(e)}'
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def _validate_plant_relationships(data):
        """
        Validate plant relationships based on pollination type.
        
        Args:
            data (dict): Pollination data
            
        Returns:
            dict: Validation errors for plant relationships
        """
        errors = {}
        pollination_type = data.get('pollination_type')
        mother_plant = data.get('mother_plant')
        father_plant = data.get('father_plant')
        new_plant = data.get('new_plant')
        
        if not pollination_type or not mother_plant:
            return errors
        
        pollination_type_name = pollination_type.name if hasattr(pollination_type, 'name') else str(pollination_type)
        
        # Self pollination validation
        if pollination_type_name == 'Self':
            if father_plant:
                errors['father_plant'] = 'La autopolinización no requiere planta padre'
            
            if mother_plant and new_plant:
                if (mother_plant.genus != new_plant.genus or 
                    mother_plant.species != new_plant.species):
                    errors['new_plant'] = 'En autopolinización, la planta nueva debe ser de la misma especie que la madre'
        
        # Sibling pollination validation
        elif pollination_type_name == 'Sibling':
            if not father_plant:
                errors['father_plant'] = 'La polinización entre hermanos requiere planta padre'
            
            if mother_plant and father_plant and new_plant:
                # All plants must be the same species
                if not (mother_plant.genus == father_plant.genus == new_plant.genus and
                        mother_plant.species == father_plant.species == new_plant.species):
                    errors['plants'] = 'En polinización entre hermanos, todas las plantas deben ser de la misma especie'
        
        # Hybrid pollination validation
        elif pollination_type_name == 'Híbrido':
            if not father_plant:
                errors['father_plant'] = 'La hibridación requiere planta padre'
            
            if mother_plant and father_plant:
                # For hybrids, different species are recommended
                if (mother_plant.genus == father_plant.genus and
                    mother_plant.species == father_plant.species):
                    errors['father_plant'] = 'Para hibridación, se recomienda usar especies diferentes'
        
        return errors
    
    @staticmethod
    def validate_plant_compatibility(mother_plant, father_plant, pollination_type):
        """
        Validate compatibility between plants for a specific pollination type.
        
        Args:
            mother_plant (Plant): Mother plant
            father_plant (Plant): Father plant (can be None for Self)
            pollination_type (PollinationType): Type of pollination
            
        Returns:
            dict: Validation result
        """
        errors = []
        
        if pollination_type.name == 'Self':
            if father_plant:
                errors.append('La autopolinización no requiere planta padre')
        
        elif pollination_type.name == 'Sibling':
            if not father_plant:
                errors.append('La polinización entre hermanos requiere planta padre')
            elif (mother_plant.genus != father_plant.genus or 
                  mother_plant.species != father_plant.species):
                errors.append('Para polinización entre hermanos, las plantas deben ser de la misma especie')
        
        elif pollination_type.name == 'Híbrido':
            if not father_plant:
                errors.append('La hibridación requiere planta padre')
            elif (mother_plant.genus == father_plant.genus and 
                  mother_plant.species == father_plant.species):
                errors.append('Para hibridación, se recomienda usar especies diferentes')
        
        return {
            'is_compatible': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def validate_maturation_confirmation(pollination_record, confirmed_date=None):
        """
        Validate maturation confirmation data.
        
        Args:
            pollination_record (PollinationRecord): Record to confirm
            confirmed_date (date, optional): Confirmation date
            
        Returns:
            dict: Validation result
        """
        errors = []
        
        if pollination_record.maturation_confirmed:
            errors.append('Esta polinización ya ha sido confirmada como madura')
        
        confirmation_date = confirmed_date or date.today()
        
        if confirmation_date < pollination_record.pollination_date:
            errors.append('La fecha de confirmación no puede ser anterior a la fecha de polinización')
        
        if confirmation_date > date.today():
            errors.append('La fecha de confirmación no puede ser futura')
        
        # Check if confirmation is too early (less than 30 days after pollination)
        min_confirmation_date = pollination_record.pollination_date + timedelta(days=30)
        if confirmation_date < min_confirmation_date:
            errors.append(f'La confirmación es muy temprana. Se recomienda esperar al menos hasta {min_confirmation_date}')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }