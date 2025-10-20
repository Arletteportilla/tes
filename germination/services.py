"""
Business logic services for the germination module.
Handles calculations, validations, and complex operations.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from django.core.exceptions import ValidationError
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone

from .models import GerminationRecord, SeedSource, GerminationCondition
from pollination.models import Plant, PollinationRecord
from core.validators import (
    DateValidators, DuplicateValidators, GerminationValidators,
    NumericValidators
)
from core.exceptions import (
    ValidationError as CustomValidationError,
    GerminationError, SeedSourceCompatibilityError,
    InvalidSeedlingQuantityError, FutureDateError
)


class GerminationService:
    """
    Service class for germination business logic.
    Handles date calculations, transplant estimations, and germination analytics.
    """
    
    # Default transplant days by plant type (can be overridden)
    DEFAULT_TRANSPLANT_DAYS = {
        'Orchidaceae': 120,  # Orchids typically need more time
        'Bromeliaceae': 90,  # Bromeliads
        'Cactaceae': 60,     # Cacti
        'default': 90        # Default for other families
    }
    
    @classmethod
    def calculate_transplant_date(cls, germination_date: date, plant: Plant, 
                                custom_days: Optional[int] = None) -> date:
        """
        Calculate estimated transplant date based on germination date and plant type.
        
        Args:
            germination_date: Date when germination occurred
            plant: Plant instance to determine species-specific timing
            custom_days: Optional custom number of days to override defaults
            
        Returns:
            Estimated transplant date
        """
        if custom_days:
            days_to_add = custom_days
        else:
            # Try to get species-specific timing
            plant_family = plant.genus
            days_to_add = cls.DEFAULT_TRANSPLANT_DAYS.get(
                plant_family, 
                cls.DEFAULT_TRANSPLANT_DAYS['default']
            )
        
        return germination_date + timedelta(days=days_to_add)
    
    @classmethod
    def get_transplant_recommendations(cls, germination_record: GerminationRecord) -> Dict:
        """
        Get transplant recommendations based on current status and conditions.
        
        Args:
            germination_record: GerminationRecord instance
            
        Returns:
            Dictionary with recommendations and status information
        """
        today = date.today()
        estimated_date = germination_record.estimated_transplant_date
        
        if not estimated_date:
            return {
                'status': 'no_estimate',
                'message': 'No hay fecha estimada de trasplante',
                'action_required': False
            }
        
        days_remaining = (estimated_date - today).days
        
        if germination_record.transplant_confirmed:
            return {
                'status': 'completed',
                'message': f'Trasplante confirmado el {germination_record.transplant_confirmed_date}',
                'action_required': False
            }
        
        if days_remaining < 0:
            return {
                'status': 'overdue',
                'message': f'Trasplante vencido hace {abs(days_remaining)} días',
                'action_required': True,
                'urgency': 'high'
            }
        elif days_remaining <= 7:
            return {
                'status': 'approaching',
                'message': f'Trasplante en {days_remaining} días',
                'action_required': True,
                'urgency': 'medium'
            }
        elif days_remaining <= 14:
            return {
                'status': 'upcoming',
                'message': f'Trasplante en {days_remaining} días',
                'action_required': False,
                'urgency': 'low'
            }
        else:
            return {
                'status': 'pending',
                'message': f'Trasplante estimado en {days_remaining} días',
                'action_required': False
            }
    
    @classmethod
    def calculate_germination_statistics(cls, records: List[GerminationRecord]) -> Dict:
        """
        Calculate germination statistics for a set of records.
        
        Args:
            records: List of GerminationRecord instances
            
        Returns:
            Dictionary with statistical information
        """
        if not records:
            return {
                'total_records': 0,
                'total_seeds_planted': 0,
                'total_seedlings_germinated': 0,
                'average_germination_rate': 0,
                'success_rate': 0
            }
        
        total_seeds = sum(record.seeds_planted for record in records)
        total_seedlings = sum(record.seedlings_germinated for record in records)
        successful_records = len([r for r in records if r.is_successful])
        
        avg_germination_rate = (total_seedlings / total_seeds * 100) if total_seeds > 0 else 0
        success_rate = (successful_records / len(records) * 100) if records else 0
        
        return {
            'total_records': len(records),
            'total_seeds_planted': total_seeds,
            'total_seedlings_germinated': total_seedlings,
            'average_germination_rate': round(avg_germination_rate, 2),
            'success_rate': round(success_rate, 2)
        }
    
    @classmethod
    def get_pending_transplants(cls, user=None, days_ahead: int = 30) -> List[GerminationRecord]:
        """
        Get germination records with pending transplants within specified days.
        
        Args:
            user: Optional user to filter records
            days_ahead: Number of days ahead to look for pending transplants
            
        Returns:
            List of GerminationRecord instances with pending transplants
        """
        end_date = date.today() + timedelta(days=days_ahead)
        
        queryset = GerminationRecord.objects.filter(
            transplant_confirmed=False,
            estimated_transplant_date__lte=end_date
        ).select_related('plant', 'responsible', 'seed_source')
        
        if user:
            queryset = queryset.filter(responsible=user)
        
        return list(queryset.order_by('estimated_transplant_date'))
    
    @classmethod
    def get_overdue_transplants(cls, user=None) -> List[GerminationRecord]:
        """
        Get germination records with overdue transplants.
        
        Args:
            user: Optional user to filter records
            
        Returns:
            List of GerminationRecord instances with overdue transplants
        """
        today = date.today()
        
        queryset = GerminationRecord.objects.filter(
            transplant_confirmed=False,
            estimated_transplant_date__lt=today
        ).select_related('plant', 'responsible', 'seed_source')
        
        if user:
            queryset = queryset.filter(responsible=user)
        
        return list(queryset.order_by('estimated_transplant_date'))


class GerminationValidationService:
    """
    Service class for germination-specific validations.
    Handles business rule validations and data integrity checks.
    """
    
    @classmethod
    def validate_germination_record(cls, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate germination record data according to business rules.
        
        Args:
            data: Dictionary with germination record data
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Validate germination date using custom validator
            germination_date = data.get('germination_date')
            if germination_date:
                try:
                    DateValidators.validate_not_future_date(germination_date, "fecha de germinación")
                except ValidationError as e:
                    errors.append(str(e.message))
            
            # Validate seed quantities using custom validators
            seeds_planted = data.get('seeds_planted', 0)
            seedlings_germinated = data.get('seedlings_germinated', 0)
            
            try:
                NumericValidators.validate_positive_integer(seeds_planted, "semillas sembradas")
            except ValidationError as e:
                errors.append(str(e.message))
            
            try:
                GerminationValidators.validate_seedling_quantity(seeds_planted, seedlings_germinated)
            except ValidationError as e:
                errors.append(str(e.message))
            
            # Validate transplant days
            transplant_days = data.get('transplant_days', 0)
            try:
                NumericValidators.validate_positive_integer(transplant_days, "días de trasplante")
                if transplant_days > 365:
                    errors.append('Los días de trasplante no pueden exceder un año')
            except ValidationError as e:
                errors.append(str(e.message))
            
            # Validate seed source compatibility using custom validator
            seed_source_id = data.get('seed_source')
            plant_id = data.get('plant')
            
            if seed_source_id and plant_id:
                try:
                    seed_source = SeedSource.objects.get(id=seed_source_id)
                    plant = Plant.objects.get(id=plant_id)
                    
                    # Use custom validator for seed source compatibility
                    try:
                        GerminationValidators.validate_seed_source_compatibility(seed_source, plant)
                    except ValidationError as e:
                        errors.append(str(e.message))
                        
                except (SeedSource.DoesNotExist, Plant.DoesNotExist):
                    errors.append('Fuente de semillas o planta no válida')
        
        except Exception as e:
            errors.append(f'Error de validación: {str(e)}')
        
        return len(errors) == 0, errors
    
    @classmethod
    def _validate_plant_seed_compatibility(cls, plant: Plant, 
                                         pollination: PollinationRecord) -> bool:
        """
        Validate that the plant is compatible with the seed source from pollination.
        
        Args:
            plant: Plant instance for germination
            pollination: PollinationRecord that produced the seeds
            
        Returns:
            True if compatible, False otherwise
        """
        # For self-pollination, plant should match the mother plant
        if pollination.pollination_type.name == 'Self':
            return (plant.genus == pollination.mother_plant.genus and 
                   plant.species == pollination.mother_plant.species)
        
        # For sibling pollination, plant should match parent species
        elif pollination.pollination_type.name == 'Sibling':
            return (plant.genus == pollination.mother_plant.genus and 
                   plant.species == pollination.mother_plant.species)
        
        # For hybrid pollination, more flexible validation
        elif pollination.pollination_type.name == 'Híbrido':
            # Plant should be related to either parent (at least same genus)
            return (plant.genus == pollination.mother_plant.genus or 
                   (pollination.father_plant and 
                    plant.genus == pollination.father_plant.genus))
        
        return True  # Default to valid for unknown types
    
    @classmethod
    def validate_seed_source(cls, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate seed source data according to business rules.
        
        Args:
            data: Dictionary with seed source data
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            source_type = data.get('source_type')
            pollination_record_id = data.get('pollination_record')
            external_supplier = data.get('external_supplier')
            collection_date = data.get('collection_date')
            
            # Validate collection date using custom validator
            if collection_date:
                try:
                    DateValidators.validate_not_future_date(collection_date, "fecha de recolección")
                except ValidationError as e:
                    errors.append(str(e.message))
            
            # Validate source type requirements
            if source_type in ['Autopolinización', 'Sibling', 'Híbrido']:
                if not pollination_record_id and not external_supplier:
                    errors.append(
                        'Se requiere un registro de polinización o proveedor externo '
                        'para este tipo de fuente'
                    )
            
            if source_type == 'Otra fuente' and not external_supplier:
                errors.append('Se requiere especificar el proveedor externo')
            
            # Validate pollination record exists and is mature enough
            if pollination_record_id:
                try:
                    pollination = PollinationRecord.objects.get(id=pollination_record_id)
                    if pollination.estimated_maturation_date > date.today():
                        errors.append(
                            'El registro de polinización aún no ha alcanzado la maduración'
                        )
                except PollinationRecord.DoesNotExist:
                    errors.append('Registro de polinización no válido')
        
        except Exception as e:
            errors.append(f'Error de validación: {str(e)}')
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_germination_condition(cls, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate germination condition data according to business rules.
        
        Args:
            data: Dictionary with germination condition data
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Validate climate type
            climate = data.get('climate')
            valid_climates = ['I', 'W', 'C', 'IW', 'IC']
            
            if climate and climate not in valid_climates:
                errors.append(f'Tipo de clima inválido. Opciones válidas: {", ".join(valid_climates)}')
            
            # Validate required fields using string validator
            required_fields = [
                ('climate', 'tipo de clima'),
                ('substrate', 'tipo de sustrato'),
                ('location', 'ubicación')
            ]
            
            for field, field_name in required_fields:
                try:
                    from core.validators import StringValidators
                    StringValidators.validate_required_field(data.get(field), field_name)
                except ValidationError as e:
                    errors.append(str(e.message))
        
        except Exception as e:
            errors.append(f'Error de validación: {str(e)}')
        
        return len(errors) == 0, errors
    
    @classmethod
    def check_duplicate_germination(cls, germination_date: date, plant_id: int, 
                                  seed_source_id: int, responsible_id: int,
                                  exclude_id: Optional[int] = None) -> bool:
        """
        Check if a similar germination record already exists.
        
        Args:
            germination_date: Date of germination
            plant_id: Plant ID
            seed_source_id: Seed source ID
            responsible_id: Responsible user ID
            exclude_id: Optional ID to exclude from check (for updates)
            
        Returns:
            True if duplicate exists, False otherwise
        """
        queryset = GerminationRecord.objects.filter(
            germination_date=germination_date,
            plant_id=plant_id,
            seed_source_id=seed_source_id,
            responsible_id=responsible_id
        )
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        
        return queryset.exists()