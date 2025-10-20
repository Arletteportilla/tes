"""
Custom validators for the pollination and germination system.
Provides reusable validation functions for dates, duplicates, and business rules.
"""

from datetime import date, datetime
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import models


class DateValidators:
    """Validators for date-related fields."""
    
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
                _(f"La {field_name} no puede ser una fecha futura. Fecha máxima permitida: {today}"),
                code='future_date_not_allowed'
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
                _(f"La {start_field_name} no puede ser posterior a la {end_field_name}"),
                code='invalid_date_range'
            )
    
    @staticmethod
    def validate_minimum_date_difference(start_date, end_date, min_days, field_name="fecha"):
        """
        Validate minimum difference between two dates.
        
        Args:
            start_date: Start date
            end_date: End date
            min_days: Minimum days difference required
            field_name: Field name for error messages
            
        Raises:
            ValidationError: If difference is less than minimum
        """
        if not start_date or not end_date:
            return
            
        # Convert datetime to date if necessary
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
            
        difference = (end_date - start_date).days
        if difference < min_days:
            raise ValidationError(
                _(f"La {field_name} debe tener al menos {min_days} días de diferencia"),
                code='insufficient_date_difference'
            )


class DuplicateValidators:
    """Validators for duplicate record detection."""
    
    @staticmethod
    def validate_unique_combination(model_class, fields_dict, exclude_id=None, error_message=None):
        """
        Validate that a combination of fields is unique.
        
        Args:
            model_class: Django model class to check
            fields_dict: Dictionary of field names and values
            exclude_id: ID to exclude from the check (for updates)
            error_message: Custom error message
            
        Raises:
            ValidationError: If a duplicate record exists
        """
        queryset = model_class.objects.filter(**fields_dict)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
            
        if queryset.exists():
            if not error_message:
                field_names = ", ".join(fields_dict.keys())
                error_message = _(f"Ya existe un registro con los mismos valores para: {field_names}")
            
            raise ValidationError(error_message, code='duplicate_record')
    
    @staticmethod
    def validate_pollination_duplicate(responsible, pollination_date, mother_plant, father_plant, 
                                     pollination_type, exclude_id=None):
        """
        Validate duplicate pollination records with enhanced logic.
        
        Args:
            responsible: User responsible for pollination
            pollination_date: Date of pollination
            mother_plant: Mother plant instance
            father_plant: Father plant instance (can be None)
            pollination_type: Type of pollination
            exclude_id: ID to exclude from check
            
        Raises:
            ValidationError: If duplicate pollination exists
        """
        from pollination.models import PollinationRecord
        
        filters = {
            'responsible': responsible,
            'pollination_date': pollination_date,
            'mother_plant': mother_plant,
            'pollination_type': pollination_type
        }
        
        # Include father plant in filter if provided
        if father_plant:
            filters['father_plant'] = father_plant
        else:
            filters['father_plant__isnull'] = True
        
        queryset = PollinationRecord.objects.filter(**filters)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
            
        if queryset.exists():
            existing_record = queryset.first()
            error_message = _(
                f"Ya existe un registro de polinización {pollination_type.name} "
                f"para {mother_plant.full_scientific_name} en la fecha {pollination_date} "
                f"por el usuario {responsible.username}"
            )
            raise ValidationError(error_message, code='duplicate_pollination')
    
    @staticmethod
    def validate_germination_duplicate(responsible, germination_date, plant, seed_source, exclude_id=None):
        """
        Validate duplicate germination records with enhanced logic.
        
        Args:
            responsible: User responsible for germination
            germination_date: Date of germination
            plant: Plant instance
            seed_source: Seed source instance
            exclude_id: ID to exclude from check
            
        Raises:
            ValidationError: If duplicate germination exists
        """
        from germination.models import GerminationRecord
        
        filters = {
            'responsible': responsible,
            'germination_date': germination_date,
            'plant': plant,
            'seed_source': seed_source
        }
        
        queryset = GerminationRecord.objects.filter(**filters)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
            
        if queryset.exists():
            existing_record = queryset.first()
            error_message = _(
                f"Ya existe un registro de germinación para {plant.full_scientific_name} "
                f"con fuente '{seed_source.name}' en la fecha {germination_date} "
                f"por el usuario {responsible.username}"
            )
            raise ValidationError(error_message, code='duplicate_germination')
    
    @staticmethod
    def validate_plant_duplicate(genus, species, vivero, mesa, pared, exclude_id=None):
        """
        Validate duplicate plant records based on location and species.
        
        Args:
            genus: Plant genus
            species: Plant species
            vivero: Vivero name
            mesa: Mesa name
            pared: Pared name
            exclude_id: ID to exclude from check
            
        Raises:
            ValidationError: If duplicate plant exists
        """
        from pollination.models import Plant
        
        filters = {
            'genus': genus,
            'species': species,
            'vivero': vivero,
            'mesa': mesa,
            'pared': pared
        }
        
        queryset = Plant.objects.filter(**filters)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
            
        if queryset.exists():
            error_message = _(
                f"Ya existe una planta {genus} {species} "
                f"en la ubicación {vivero}/{mesa}/{pared}"
            )
            raise ValidationError(error_message, code='duplicate_plant')
    
    @staticmethod
    def validate_user_duplicate(username=None, email=None, exclude_id=None):
        """
        Validate duplicate user records.
        
        Args:
            username: Username to check
            email: Email to check
            exclude_id: ID to exclude from check
            
        Raises:
            ValidationError: If duplicate user exists
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        errors = []
        
        if username:
            queryset = User.objects.filter(username=username)
            if exclude_id:
                queryset = queryset.exclude(id=exclude_id)
            if queryset.exists():
                errors.append(_("Ya existe un usuario con este nombre de usuario"))
        
        if email:
            queryset = User.objects.filter(email=email)
            if exclude_id:
                queryset = queryset.exclude(id=exclude_id)
            if queryset.exists():
                errors.append(_("Ya existe un usuario con este correo electrónico"))
        
        if errors:
            raise ValidationError(errors, code='duplicate_user')
    
    @staticmethod
    def validate_seed_source_duplicate(name, source_type, exclude_id=None):
        """
        Validate duplicate seed source records.
        
        Args:
            name: Seed source name
            source_type: Type of seed source
            exclude_id: ID to exclude from check
            
        Raises:
            ValidationError: If duplicate seed source exists
        """
        from germination.models import SeedSource
        
        filters = {
            'name': name,
            'source_type': source_type
        }
        
        queryset = SeedSource.objects.filter(**filters)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
            
        if queryset.exists():
            error_message = _(
                f"Ya existe una fuente de semillas '{name}' "
                f"del tipo '{source_type}'"
            )
            raise ValidationError(error_message, code='duplicate_seed_source')


class PollinationValidators:
    """Validators specific to pollination business rules."""
    
    @staticmethod
    def validate_plant_compatibility(mother_plant, father_plant, pollination_type):
        """
        Validate plant compatibility based on pollination type with enhanced logic.
        
        Args:
            mother_plant: Mother plant instance
            father_plant: Father plant instance (can be None for Self type)
            pollination_type: Type of pollination (Self, Sibling, Híbrido)
            
        Raises:
            ValidationError: If plants are not compatible for the pollination type
        """
        if not mother_plant:
            raise ValidationError(
                _("La planta madre es obligatoria"),
                code='missing_mother_plant'
            )
            
        pollination_type_name = pollination_type.name if hasattr(pollination_type, 'name') else str(pollination_type)
        
        if pollination_type_name == "Self":
            if father_plant and father_plant != mother_plant:
                raise ValidationError(
                    _("Para autopolinización, la planta padre debe ser la misma que la madre o no especificarse"),
                    code='invalid_self_pollination'
                )
        
        elif pollination_type_name == "Sibling":
            if not father_plant:
                raise ValidationError(
                    _("Para polinización Sibling, la planta padre es obligatoria"),
                    code='missing_father_plant_sibling'
                )
            
            # Validate that plants are not the same physical plant
            if mother_plant.id == father_plant.id:
                raise ValidationError(
                    _("Para polinización Sibling, la planta madre y padre deben ser plantas físicamente diferentes"),
                    code='same_physical_plant_sibling'
                )
            
            # For Sibling, both plants should be from the same species
            if mother_plant.species != father_plant.species or mother_plant.genus != father_plant.genus:
                raise ValidationError(
                    _("Para polinización Sibling, ambas plantas deben ser de la misma especie"),
                    code='incompatible_plants_sibling'
                )
        
        elif pollination_type_name == "Híbrido":
            if not father_plant:
                raise ValidationError(
                    _("Para hibridación, la planta padre es obligatoria"),
                    code='missing_father_plant_hybrid'
                )
            
            # Validate that plants are not the same physical plant
            if mother_plant.id == father_plant.id:
                raise ValidationError(
                    _("Para hibridación, la planta madre y padre deben ser plantas físicamente diferentes"),
                    code='same_physical_plant_hybrid'
                )
            
            # For Híbrido, plants should be from different species but same genus is recommended
            if (mother_plant.genus == father_plant.genus and 
                mother_plant.species == father_plant.species):
                raise ValidationError(
                    _("Para hibridación, se recomienda usar especies diferentes"),
                    code='same_species_hybrid'
                )
        
        else:
            raise ValidationError(
                _("Tipo de polinización no válido"),
                code='invalid_pollination_type'
            )
    
    @staticmethod
    def validate_new_plant_compatibility(mother_plant, father_plant, new_plant, pollination_type):
        """
        Validate that the new plant is compatible with the pollination type.
        
        Args:
            mother_plant: Mother plant instance
            father_plant: Father plant instance (can be None)
            new_plant: New plant instance
            pollination_type: Type of pollination
            
        Raises:
            ValidationError: If new plant is not compatible
        """
        if not new_plant:
            raise ValidationError(
                _("La planta nueva es obligatoria"),
                code='missing_new_plant'
            )
        
        # Validate that new plant is not the same as mother or father
        if new_plant.id == mother_plant.id:
            raise ValidationError(
                _("La planta nueva debe ser diferente a la planta madre"),
                code='new_plant_same_as_mother'
            )
        
        if father_plant and new_plant.id == father_plant.id:
            raise ValidationError(
                _("La planta nueva debe ser diferente a la planta padre"),
                code='new_plant_same_as_father'
            )
        
        pollination_type_name = pollination_type.name if hasattr(pollination_type, 'name') else str(pollination_type)
        
        if pollination_type_name == "Self":
            # New plant should be same species as mother
            if (new_plant.genus != mother_plant.genus or 
                new_plant.species != mother_plant.species):
                raise ValidationError(
                    _("En autopolinización, la planta nueva debe ser de la misma especie que la madre"),
                    code='incompatible_new_plant_self'
                )
        
        elif pollination_type_name == "Sibling":
            # New plant should be same species as both parents
            if (new_plant.genus != mother_plant.genus or 
                new_plant.species != mother_plant.species):
                raise ValidationError(
                    _("En polinización Sibling, la planta nueva debe ser de la misma especie que los padres"),
                    code='incompatible_new_plant_sibling'
                )
        
        elif pollination_type_name == "Híbrido":
            # For hybrid, new plant should be compatible with expected hybrid result
            # This is more flexible but should at least be from the same genus
            if new_plant.genus not in [mother_plant.genus, father_plant.genus]:
                raise ValidationError(
                    _("En hibridación, la planta nueva debe ser del mismo género que al menos uno de los padres"),
                    code='incompatible_new_plant_hybrid'
                )
    
    @staticmethod
    def validate_pollination_timing(pollination_date, mother_plant, father_plant=None):
        """
        Validate timing constraints for pollination.
        
        Args:
            pollination_date: Date of pollination
            mother_plant: Mother plant instance
            father_plant: Father plant instance (optional)
            
        Raises:
            ValidationError: If timing is not appropriate
        """
        from datetime import date, timedelta
        
        # Check if there are recent pollinations on the same plant
        from pollination.models import PollinationRecord
        
        # Look for pollinations in the last 30 days on the same mother plant
        recent_date = pollination_date - timedelta(days=30)
        recent_pollinations = PollinationRecord.objects.filter(
            mother_plant=mother_plant,
            pollination_date__gte=recent_date,
            pollination_date__lt=pollination_date
        )
        
        if recent_pollinations.exists():
            last_pollination = recent_pollinations.order_by('-pollination_date').first()
            days_since = (pollination_date - last_pollination.pollination_date).days
            
            if days_since < 7:
                raise ValidationError(
                    _(f"La planta madre fue polinizada hace solo {days_since} días. "
                      f"Se recomienda esperar al menos 7 días entre polinizaciones"),
                    code='pollination_too_frequent'
                )
    
    @staticmethod
    def validate_capsules_quantity(capsules_quantity, mother_plant, pollination_type):
        """
        Validate capsules quantity based on plant and pollination type.
        
        Args:
            capsules_quantity: Number of capsules
            mother_plant: Mother plant instance
            pollination_type: Type of pollination
            
        Raises:
            ValidationError: If quantity is not appropriate
        """
        if capsules_quantity <= 0:
            raise ValidationError(
                _("La cantidad de cápsulas debe ser mayor a cero"),
                code='invalid_capsules_quantity'
            )
        
        # Set reasonable limits based on plant genus
        max_capsules = 50  # Default maximum
        
        if hasattr(mother_plant, 'genus'):
            genus_limits = {
                'Orchidaceae': 20,
                'Cattleya': 15,
                'Dendrobium': 25,
                'Phalaenopsis': 10,
            }
            max_capsules = genus_limits.get(mother_plant.genus, max_capsules)
        
        if capsules_quantity > max_capsules:
            raise ValidationError(
                _(f"La cantidad de cápsulas ({capsules_quantity}) excede el máximo "
                  f"recomendado para {mother_plant.genus} ({max_capsules})"),
                code='excessive_capsules_quantity'
            )
    
    @staticmethod
    def validate_climate_conditions(climate_condition, pollination_type):
        """
        Validate climate conditions are appropriate for pollination type.
        
        Args:
            climate_condition: ClimateCondition instance
            pollination_type: Type of pollination
            
        Raises:
            ValidationError: If conditions are not suitable
        """
        if not climate_condition:
            raise ValidationError(
                _("Las condiciones climáticas son obligatorias"),
                code='missing_climate_condition'
            )
        
        # Validate climate type is appropriate
        valid_climates = ['I', 'W', 'C', 'IW', 'IC']
        if climate_condition.climate not in valid_climates:
            raise ValidationError(
                _(f"El tipo de clima '{climate_condition.climate}' no es válido"),
                code='invalid_climate_type'
            )
        
        # Provide recommendations based on climate type
        climate_recommendations = {
            'C': 'Clima frío - Ideal para especies de montaña y algunas orquídeas',
            'IC': 'Clima intermedio frío - Bueno para la mayoría de especies templadas',
            'I': 'Clima intermedio - Condiciones estándar para la mayoría de especies',
            'IW': 'Clima intermedio caliente - Ideal para especies subtropicales',
            'W': 'Clima caliente - Perfecto para especies tropicales'
        }
        
        # Log recommendation for the selected climate
        import logging
        logger = logging.getLogger('core.validators')
        logger.info(f"Clima seleccionado: {climate_condition.get_climate_display()} - "
                   f"{climate_recommendations.get(climate_condition.climate, 'Sin recomendación')}")


class GerminationValidators:
    """Validators specific to germination business rules."""
    
    @staticmethod
    def validate_seedling_quantity(seeds_planted, seedlings_germinated):
        """
        Validate that seedlings germinated doesn't exceed seeds planted.
        
        Args:
            seeds_planted: Number of seeds planted
            seedlings_germinated: Number of seedlings that germinated
            
        Raises:
            ValidationError: If seedlings exceed seeds planted
        """
        if seedlings_germinated > seeds_planted:
            raise ValidationError(
                _("Las plántulas germinadas no pueden exceder las semillas sembradas"),
                code='excessive_seedlings'
            )
        
        # Validate reasonable germination rates
        if seeds_planted > 0:
            germination_rate = (seedlings_germinated / seeds_planted) * 100
            if germination_rate > 100:
                raise ValidationError(
                    _("La tasa de germinación no puede exceder el 100%"),
                    code='impossible_germination_rate'
                )
    
    @staticmethod
    def validate_transplant_date(germination_date, transplant_date):
        """
        Validate transplant date is after germination date.
        
        Args:
            germination_date: Date of germination
            transplant_date: Date of transplant
            
        Raises:
            ValidationError: If transplant date is invalid
        """
        if transplant_date < germination_date:
            raise ValidationError(
                _("La fecha de trasplante no puede ser anterior a la fecha de germinación"),
                code='invalid_transplant_date'
            )
        
        if transplant_date > date.today():
            raise ValidationError(
                _("La fecha de trasplante no puede ser futura"),
                code='future_transplant_date'
            )
        
        # Validate minimum time between germination and transplant
        days_difference = (transplant_date - germination_date).days
        if days_difference < 30:
            raise ValidationError(
                _(f"Debe transcurrir al menos 30 días entre germinación y trasplante "
                  f"(actual: {days_difference} días)"),
                code='transplant_too_early'
            )
    
    @staticmethod
    def validate_seed_source_compatibility(seed_source, plant):
        """
        Validate that seed source is compatible with the plant being germinated.
        
        Args:
            seed_source: SeedSource instance
            plant: Plant instance
            
        Raises:
            ValidationError: If seed source is not compatible
        """
        # If seed source comes from a pollination record, check compatibility
        if seed_source.pollination_record:
            pollination_record = seed_source.pollination_record
            
            # The plant being germinated should match the new plant from pollination
            if (plant.genus != pollination_record.new_plant.genus or 
                plant.species != pollination_record.new_plant.species):
                raise ValidationError(
                    _("La planta a germinar debe coincidir con la especie del registro de polinización"),
                    code='incompatible_seed_source'
                )
            
            # Check if the pollination was successful
            if not pollination_record.maturation_confirmed:
                raise ValidationError(
                    _("No se puede usar semillas de una polinización que no ha sido confirmada como exitosa"),
                    code='unconfirmed_pollination_source'
                )
    
    @staticmethod
    def validate_germination_conditions(germination_condition, plant):
        """
        Validate germination conditions are appropriate for the plant species.
        
        Args:
            germination_condition: GerminationCondition instance
            plant: Plant instance
            
        Raises:
            ValidationError: If conditions are not suitable
        """
        if not germination_condition:
            raise ValidationError(
                _("Las condiciones de germinación son obligatorias"),
                code='missing_germination_condition'
            )
        
        # Validate climate type is appropriate
        valid_climates = ['I', 'W', 'C', 'IW', 'IC']
        if germination_condition.climate not in valid_climates:
            raise ValidationError(
                _(f"El tipo de clima '{germination_condition.climate}' no es válido"),
                code='invalid_climate_type'
            )
        
        # Validate climate compatibility with plant genus
        genus_climate_recommendations = {
            'Orchidaceae': ['I', 'IW', 'IC'],  # Prefer intermediate climates
            'Cattleya': ['I', 'IW'],           # Prefer intermediate to warm
            'Dendrobium': ['I', 'IC'],         # Prefer intermediate to cool
            'Phalaenopsis': ['IW', 'W'],       # Prefer warm climates
            'Cactaceae': ['W', 'IW'],          # Prefer warm climates
            'Bromeliaceae': ['IW', 'W', 'I'],  # Flexible, prefer warm
        }
        
        recommended_climates = genus_climate_recommendations.get(plant.genus, ['I', 'IW', 'IC'])
        
        if germination_condition.climate not in recommended_climates:
            climate_names = [dict(germination_condition.CLIMATE_CHOICES)[c] for c in recommended_climates]
            raise ValidationError(
                _(f"El clima '{germination_condition.get_climate_display()}' no es óptimo para {plant.genus}. "
                  f"Se recomienda: {', '.join(climate_names)}"),
                code='suboptimal_climate_for_genus'
            )
        
        # Log successful validation
        import logging
        logger = logging.getLogger('core.validators')
        logger.info(f"Condiciones de germinación validadas: {germination_condition.get_climate_display()} "
                   f"para {plant.genus} {plant.species}")
    
    @staticmethod
    def validate_transplant_timing(germination_record, transplant_date=None):
        """
        Validate timing for transplant based on germination record.
        
        Args:
            germination_record: GerminationRecord instance
            transplant_date: Proposed transplant date (defaults to today)
            
        Raises:
            ValidationError: If timing is not appropriate
        """
        if transplant_date is None:
            transplant_date = date.today()
        
        # Check if already transplanted
        if germination_record.transplant_confirmed:
            raise ValidationError(
                _("Este registro ya ha sido marcado como trasplantado"),
                code='already_transplanted'
            )
        
        # Check minimum germination success
        if germination_record.seedlings_germinated == 0:
            raise ValidationError(
                _("No se puede trasplantar si no hay plántulas germinadas"),
                code='no_seedlings_to_transplant'
            )
        
        # Check if it's too early based on estimated date
        if germination_record.estimated_transplant_date:
            days_early = (germination_record.estimated_transplant_date - transplant_date).days
            if days_early > 14:  # More than 2 weeks early
                raise ValidationError(
                    _(f"Es muy temprano para trasplantar. Faltan {days_early} días "
                      f"para la fecha estimada ({germination_record.estimated_transplant_date})"),
                    code='transplant_too_early'
                )
    
    @staticmethod
    def validate_seed_viability(seed_source, germination_date):
        """
        Validate seed viability based on collection date and storage time.
        
        Args:
            seed_source: SeedSource instance
            germination_date: Date of germination attempt
            
        Raises:
            ValidationError: If seeds may not be viable
        """
        if seed_source.collection_date:
            days_stored = (germination_date - seed_source.collection_date).days
            
            # Different storage limits by source type
            storage_limits = {
                'Autopolinización': 365,  # 1 year
                'Sibling': 365,
                'Híbrido': 365,
                'Otra fuente': 730,  # 2 years for external sources
            }
            
            max_storage = storage_limits.get(seed_source.source_type, 365)
            
            if days_stored > max_storage * 1.5:  # 50% over limit - check this first
                raise ValidationError(
                    _(f"Las semillas están demasiado viejas ({days_stored} días) "
                      f"y probablemente no sean viables"),
                    code='seeds_not_viable'
                )
            elif days_stored > max_storage:
                raise ValidationError(
                    _(f"Las semillas han estado almacenadas por {days_stored} días, "
                      f"lo cual excede el tiempo máximo recomendado ({max_storage} días). "
                      f"La viabilidad puede estar comprometida"),
                    code='seeds_too_old'
                )


class NumericValidators:
    """Validators for numeric fields."""
    
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
                _(f"El campo {field_name} debe ser un número entero positivo"),
                code='invalid_positive_integer'
            )
    
    @staticmethod
    def validate_percentage(value, field_name):
        """
        Validate that a value is a valid percentage (0-100).
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            
        Raises:
            ValidationError: If the value is not a valid percentage
        """
        if value is None:
            return
            
        if not isinstance(value, (int, float)) or value < 0 or value > 100:
            raise ValidationError(
                _(f"El campo {field_name} debe ser un porcentaje válido (0-100)"),
                code='invalid_percentage'
            )
    
    @staticmethod
    def validate_temperature(value, field_name="temperatura"):
        """
        Validate temperature value is within reasonable range.
        
        Args:
            value: Temperature value to validate
            field_name: Name of the field for error messages
            
        Raises:
            ValidationError: If temperature is outside reasonable range
        """
        if value is None:
            return
            
        if value < -50 or value > 60:
            raise ValidationError(
                _(f"La {field_name} debe estar entre -50°C y 60°C"),
                code='invalid_temperature'
            )


class StringValidators:
    """Validators for string fields."""
    
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
                _(f"El campo {field_name} debe tener al menos {min_length} caracteres"),
                code='string_too_short'
            )
            
        if max_length and length > max_length:
            raise ValidationError(
                _(f"El campo {field_name} no puede tener más de {max_length} caracteres"),
                code='string_too_long'
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
                _(f"El campo {field_name} es obligatorio"),
                code='required_field'
            )


# Django field validators that can be used in model field definitions
def not_future_date_validator(value):
    """Django field validator for dates that cannot be in the future."""
    DateValidators.validate_not_future_date(value)


def positive_integer_validator(value):
    """Django field validator for positive integers."""
    NumericValidators.validate_positive_integer(value, "valor")


def percentage_validator(value):
    """Django field validator for percentage values."""
    NumericValidators.validate_percentage(value, "porcentaje")


def temperature_validator(value):
    """Django field validator for temperature values."""
    NumericValidators.validate_temperature(value)