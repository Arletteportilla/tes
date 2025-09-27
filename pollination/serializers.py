from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Plant, PollinationType, ClimateCondition, PollinationRecord
from .services import ValidationService
from authentication.serializers import UserSerializer


class PlantSerializer(serializers.ModelSerializer):
    """Serializer for Plant model."""
    
    full_scientific_name = serializers.ReadOnlyField()
    location = serializers.ReadOnlyField()
    
    class Meta:
        model = Plant
        fields = [
            'id', 'genus', 'species', 'vivero', 'mesa', 'pared',
            'is_active', 'full_scientific_name', 'location',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        """Custom validation for Plant data."""
        # Check for duplicate plant location
        genus = data.get('genus')
        species = data.get('species')
        vivero = data.get('vivero')
        mesa = data.get('mesa')
        pared = data.get('pared')
        
        if all([genus, species, vivero, mesa, pared]):
            queryset = Plant.objects.filter(
                genus=genus,
                species=species,
                vivero=vivero,
                mesa=mesa,
                pared=pared
            )
            
            # Exclude current instance if updating
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError(
                    "Ya existe una planta con esta ubicación específica."
                )
        
        return data


class PollinationTypeSerializer(serializers.ModelSerializer):
    """Serializer for PollinationType model."""
    
    display_name = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = PollinationType
        fields = [
            'id', 'name', 'display_name', 'description',
            'requires_father_plant', 'allows_different_species',
            'maturation_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ClimateConditionSerializer(serializers.ModelSerializer):
    """Serializer for ClimateCondition model."""
    
    class Meta:
        model = ClimateCondition
        fields = [
            'id', 'weather', 'temperature', 'humidity',
            'wind_speed', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_humidity(self, value):
        """Validate humidity is within valid range."""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError(
                "La humedad debe estar entre 0 y 100%."
            )
        return value
    
    def validate_wind_speed(self, value):
        """Validate wind speed is not negative."""
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "La velocidad del viento no puede ser negativa."
            )
        return value


class PollinationRecordSerializer(serializers.ModelSerializer):
    """Serializer for PollinationRecord model."""
    
    # Nested serializers for read operations
    responsible_detail = UserSerializer(source='responsible', read_only=True)
    pollination_type_detail = PollinationTypeSerializer(source='pollination_type', read_only=True)
    mother_plant_detail = PlantSerializer(source='mother_plant', read_only=True)
    father_plant_detail = PlantSerializer(source='father_plant', read_only=True)
    new_plant_detail = PlantSerializer(source='new_plant', read_only=True)
    climate_condition_detail = ClimateConditionSerializer(source='climate_condition', read_only=True)
    
    # Computed fields
    days_to_maturation = serializers.SerializerMethodField()
    maturation_status = serializers.SerializerMethodField()
    is_maturation_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = PollinationRecord
        fields = [
            'id', 'responsible', 'responsible_detail',
            'pollination_type', 'pollination_type_detail',
            'pollination_date', 'estimated_maturation_date',
            'mother_plant', 'mother_plant_detail',
            'father_plant', 'father_plant_detail',
            'new_plant', 'new_plant_detail',
            'climate_condition', 'climate_condition_detail',
            'capsules_quantity', 'observations',
            'is_successful', 'maturation_confirmed', 'maturation_confirmed_date',
            'days_to_maturation', 'maturation_status', 'is_maturation_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'estimated_maturation_date', 'created_at', 'updated_at'
        ]
    
    def get_days_to_maturation(self, obj):
        """Get days remaining to maturation."""
        return obj.days_to_maturation()
    
    def get_maturation_status(self, obj):
        """Get maturation status information."""
        from .services import PollinationService
        return PollinationService.get_maturation_status(obj)
    
    def get_is_maturation_overdue(self, obj):
        """Check if maturation is overdue."""
        return obj.is_maturation_overdue()
    
    def validate(self, data):
        """Custom validation for PollinationRecord data."""
        # Basic validation first
        if not data.get('responsible'):
            data['responsible'] = self.context['request'].user if 'request' in self.context else None
        
        # Use ValidationService for comprehensive validation
        validation_result = ValidationService.validate_pollination_data(data)
        
        if not validation_result['is_valid']:
            raise serializers.ValidationError(validation_result['errors'])
        
        return data
    
    def validate_pollination_date(self, value):
        """Validate pollination date is not in the future."""
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError(
                "La fecha de polinización no puede ser futura."
            )
        return value
    
    def validate_capsules_quantity(self, value):
        """Validate capsules quantity is positive."""
        if value < 1:
            raise serializers.ValidationError(
                "La cantidad de cápsulas debe ser mayor a 0."
            )
        return value


class PollinationRecordCreateSerializer(PollinationRecordSerializer):
    """Specialized serializer for creating pollination records."""
    
    class Meta(PollinationRecordSerializer.Meta):
        # Exclude detail fields for creation to avoid confusion
        fields = [
            'id', 'pollination_type', 'pollination_date',
            'mother_plant', 'father_plant', 'new_plant',
            'climate_condition', 'capsules_quantity', 'observations'
        ]


class PollinationRecordUpdateSerializer(serializers.ModelSerializer):
    """Specialized serializer for updating pollination records."""
    
    class Meta:
        model = PollinationRecord
        fields = [
            'observations', 'is_successful', 
            'maturation_confirmed', 'maturation_confirmed_date'
        ]
    
    def validate_maturation_confirmed_date(self, value):
        """Validate maturation confirmation date."""
        if value:
            from datetime import date
            if value > date.today():
                raise serializers.ValidationError(
                    "La fecha de confirmación no puede ser futura."
                )
            
            # Check against pollination date if available
            if self.instance and value < self.instance.pollination_date:
                raise serializers.ValidationError(
                    "La fecha de confirmación no puede ser anterior a la fecha de polinización."
                )
        
        return value
    
    def validate(self, data):
        """Custom validation for update data."""
        if self.instance:
            # Use ValidationService for maturation confirmation validation
            if data.get('maturation_confirmed') and not self.instance.maturation_confirmed:
                from .services import ValidationService
                validation_result = ValidationService.validate_maturation_confirmation(
                    self.instance, 
                    data.get('maturation_confirmed_date')
                )
                
                if not validation_result['is_valid']:
                    raise serializers.ValidationError(validation_result['errors'])
        
        return data


class MaturationConfirmationSerializer(serializers.Serializer):
    """Serializer for maturation confirmation action."""
    
    confirmed_date = serializers.DateField(required=False)
    is_successful = serializers.BooleanField(default=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_confirmed_date(self, value):
        """Validate confirmation date."""
        if value:
            from datetime import date
            if value > date.today():
                raise serializers.ValidationError(
                    "La fecha de confirmación no puede ser futura."
                )
        return value


class PollinationStatisticsSerializer(serializers.Serializer):
    """Serializer for pollination statistics."""
    
    total_records = serializers.IntegerField()
    confirmed_records = serializers.IntegerField()
    successful_records = serializers.IntegerField()
    overdue_records = serializers.IntegerField()
    success_rate = serializers.FloatField()
    confirmation_rate = serializers.FloatField()
    pending_confirmation = serializers.IntegerField()
    
    # Optional filters used for statistics
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    responsible = serializers.IntegerField(required=False)


class PlantCompatibilitySerializer(serializers.Serializer):
    """Serializer for plant compatibility validation."""
    
    mother_plant_id = serializers.IntegerField()
    father_plant_id = serializers.IntegerField(required=False, allow_null=True)