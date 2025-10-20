"""
Serializers for the germination module.
Handles data serialization and validation for API endpoints.
"""

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from datetime import date

from .models import GerminationRecord, SeedSource, GerminationCondition
from .services import GerminationValidationService
from pollination.models import Plant
from authentication.models import CustomUser


class GerminationConditionSerializer(serializers.ModelSerializer):
    """
    Serializer for GerminationCondition model.
    Handles environmental conditions during germination.
    """
    
    climate_display = serializers.CharField(source='get_climate_display', read_only=True)
    temperature_range = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    
    class Meta:
        model = GerminationCondition
        fields = [
            'id', 'climate', 'climate_display', 'substrate', 'location', 
            'temperature_range', 'description', 'substrate_details', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'climate_display', 'temperature_range', 'description']


class SeedSourceSerializer(serializers.ModelSerializer):
    """
    Serializer for SeedSource model.
    Handles seed source information and validation.
    """
    pollination_record_details = serializers.SerializerMethodField()
    
    class Meta:
        model = SeedSource
        fields = [
            'id', 'name', 'source_type', 'description', 'pollination_record',
            'pollination_record_details', 'external_supplier', 'collection_date',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'pollination_record_details']
    
    def get_pollination_record_details(self, obj):
        """Get details of the related pollination record if exists."""
        if obj.pollination_record:
            return {
                'id': obj.pollination_record.id,
                'pollination_type': obj.pollination_record.pollination_type.name,
                'pollination_date': obj.pollination_record.pollination_date,
                'mother_plant': str(obj.pollination_record.mother_plant),
                'estimated_maturation_date': obj.pollination_record.estimated_maturation_date
            }
        return None
    
    def validate(self, data):
        """Custom validation using the validation service."""
        is_valid, errors = GerminationValidationService.validate_seed_source(data)
        
        if not is_valid:
            raise serializers.ValidationError({
                'non_field_errors': errors
            })
        
        return data


class GerminationRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for GerminationRecord model.
    Handles complete germination record data with nested relationships.
    """
    responsible_name = serializers.CharField(source='responsible.get_full_name', read_only=True)
    plant_details = serializers.SerializerMethodField()
    seed_source_details = serializers.SerializerMethodField()
    germination_condition_details = serializers.SerializerMethodField()
    transplant_status = serializers.CharField(read_only=True)
    germination_rate = serializers.SerializerMethodField()
    days_to_transplant = serializers.SerializerMethodField()
    transplant_recommendations = serializers.SerializerMethodField()
    
    class Meta:
        model = GerminationRecord
        fields = [
            'id', 'responsible', 'responsible_name', 'germination_date',
            'estimated_transplant_date', 'plant', 'plant_details',
            'seed_source', 'seed_source_details', 'germination_condition',
            'germination_condition_details', 'seeds_planted', 'seedlings_germinated',
            'transplant_days', 'is_successful', 'transplant_confirmed',
            'transplant_confirmed_date', 'observations', 'transplant_status',
            'germination_rate', 'days_to_transplant', 'transplant_recommendations',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'responsible', 'responsible_name', 'estimated_transplant_date', 'plant_details',
            'seed_source_details', 'germination_condition_details', 'transplant_status',
            'germination_rate', 'days_to_transplant', 'transplant_recommendations',
            'created_at', 'updated_at'
        ]
    
    def get_plant_details(self, obj):
        """Get plant details."""
        return {
            'id': obj.plant.id,
            'full_scientific_name': obj.plant.full_scientific_name,
            'location': obj.plant.location,
            'genus': obj.plant.genus,
            'species': obj.plant.species
        }
    
    def get_seed_source_details(self, obj):
        """Get seed source details."""
        return {
            'id': obj.seed_source.id,
            'name': obj.seed_source.name,
            'source_type': obj.seed_source.source_type,
            'source_type_display': obj.seed_source.get_source_type_display()
        }
    
    def get_germination_condition_details(self, obj):
        """Get germination condition details."""
        return {
            'id': obj.germination_condition.id,
            'climate': obj.germination_condition.climate,
            'substrate': obj.germination_condition.substrate,
            'location': obj.germination_condition.location,
            'temperature': obj.germination_condition.temperature,
            'humidity': obj.germination_condition.humidity
        }
    
    def get_germination_rate(self, obj):
        """Get germination success rate."""
        return obj.germination_rate()
    
    def get_days_to_transplant(self, obj):
        """Get days remaining to transplant."""
        return obj.days_to_transplant()
    
    def get_transplant_recommendations(self, obj):
        """Get transplant recommendations."""
        from .services import GerminationService
        return GerminationService.get_transplant_recommendations(obj)
    
    def validate(self, data):
        """Custom validation using the validation service."""
        # Add IDs for validation
        validation_data = data.copy()
        if 'seed_source' in data:
            validation_data['seed_source'] = data['seed_source'].id
        if 'plant' in data:
            validation_data['plant'] = data['plant'].id
        
        # For update operations, merge with existing data
        if self.instance:
            # For updates, merge with existing instance data
            validation_data['responsible'] = self.instance.responsible.id
            
            # Fill in missing fields from existing instance for validation
            if 'seeds_planted' not in validation_data:
                validation_data['seeds_planted'] = self.instance.seeds_planted
            if 'seedlings_germinated' not in validation_data:
                validation_data['seedlings_germinated'] = self.instance.seedlings_germinated
            if 'transplant_days' not in validation_data:
                validation_data['transplant_days'] = self.instance.transplant_days
            if 'germination_date' not in validation_data:
                validation_data['germination_date'] = self.instance.germination_date
            if 'plant' not in validation_data:
                validation_data['plant'] = self.instance.plant.id
            if 'seed_source' not in validation_data:
                validation_data['seed_source'] = self.instance.seed_source.id
        elif 'responsible' in data:
            validation_data['responsible'] = data['responsible'].id
        else:
            # Skip validation that requires responsible for create operations
            # The responsible will be set in perform_create
            basic_validation_data = {k: v for k, v in validation_data.items() 
                                   if k not in ['responsible']}
            is_valid, errors = GerminationValidationService.validate_germination_record(basic_validation_data)
            
            if not is_valid:
                # Filter out errors that require responsible field
                filtered_errors = [e for e in errors if 'responsable' not in e.lower()]
                if filtered_errors:
                    raise serializers.ValidationError({
                        'non_field_errors': filtered_errors
                    })
            return data
        
        is_valid, errors = GerminationValidationService.validate_germination_record(validation_data)
        
        if not is_valid:
            raise serializers.ValidationError({
                'non_field_errors': errors
            })
        
        # Check for duplicates only if we have all required data
        if all(key in validation_data for key in ['germination_date', 'plant', 'seed_source', 'responsible']):
            instance_id = self.instance.id if self.instance else None
            is_duplicate = GerminationValidationService.check_duplicate_germination(
                germination_date=data.get('germination_date'),
                plant_id=validation_data['plant'],
                seed_source_id=validation_data['seed_source'],
                responsible_id=validation_data['responsible'],
                exclude_id=instance_id
            )
            
            if is_duplicate:
                raise serializers.ValidationError({
                    'non_field_errors': ['Ya existe un registro de germinación similar']
                })
        
        return data


class GerminationRecordCreateSerializer(GerminationRecordSerializer):
    """
    Specialized serializer for creating germination records.
    Includes additional validation and automatic field population.
    """
    
    def create(self, validated_data):
        """Create germination record with automatic date calculation."""
        from .services import GerminationService
        
        # Calculate estimated transplant date if not provided
        if not validated_data.get('estimated_transplant_date'):
            validated_data['estimated_transplant_date'] = GerminationService.calculate_transplant_date(
                germination_date=validated_data['germination_date'],
                plant=validated_data['plant'],
                custom_days=validated_data.get('transplant_days')
            )
        
        return super().create(validated_data)


class GerminationRecordUpdateSerializer(GerminationRecordSerializer):
    """
    Specialized serializer for updating germination records.
    Allows partial updates and handles status changes.
    """
    
    def update(self, instance, validated_data):
        """Update germination record with business logic."""
        # If transplant is being confirmed, validate the date
        if validated_data.get('transplant_confirmed') and not instance.transplant_confirmed:
            confirmed_date = validated_data.get('transplant_confirmed_date', date.today())
            if confirmed_date < instance.germination_date:
                raise serializers.ValidationError({
                    'transplant_confirmed_date': 'La fecha de trasplante no puede ser anterior a la germinación'
                })
        
        return super().update(instance, validated_data)


class GerminationStatisticsSerializer(serializers.Serializer):
    """
    Serializer for germination statistics data.
    Used for reporting and analytics endpoints.
    """
    total_records = serializers.IntegerField()
    total_seeds_planted = serializers.IntegerField()
    total_seedlings_germinated = serializers.IntegerField()
    average_germination_rate = serializers.FloatField()
    success_rate = serializers.FloatField()
    
    # Optional breakdown by time period
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
    
    # Optional breakdown by plant type
    by_genus = serializers.DictField(required=False)
    by_species = serializers.DictField(required=False)


class TransplantRecommendationSerializer(serializers.Serializer):
    """
    Serializer for transplant recommendations.
    Used for alert and notification endpoints.
    """
    germination_record_id = serializers.IntegerField()
    plant_name = serializers.CharField()
    germination_date = serializers.DateField()
    estimated_transplant_date = serializers.DateField()
    days_remaining = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField()
    action_required = serializers.BooleanField()
    urgency = serializers.CharField(required=False)


class SeedSourceListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for seed source listings.
    Used in dropdown selections and list views.
    """
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    
    class Meta:
        model = SeedSource
        fields = [
            'id', 'name', 'source_type', 'source_type_display',
            'external_supplier', 'is_active'
        ]


class GerminationConditionListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for germination condition listings.
    Used in dropdown selections and list views.
    """
    climate_display = serializers.CharField(source='get_climate_display', read_only=True)
    substrate_display = serializers.CharField(source='get_substrate_display', read_only=True)
    temperature_range = serializers.CharField(read_only=True)
    
    class Meta:
        model = GerminationCondition
        fields = [
            'id', 'climate', 'climate_display', 'substrate', 'substrate_display',
            'location', 'temperature_range'
        ]