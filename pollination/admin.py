from django.contrib import admin
from .models import Plant, PollinationType, ClimateCondition, PollinationRecord


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    """Admin configuration for Plant model."""
    list_display = ['genus', 'species', 'vivero', 'mesa', 'pared', 'is_active', 'created_at']
    list_filter = ['genus', 'species', 'vivero', 'is_active', 'created_at']
    search_fields = ['genus', 'species', 'vivero', 'mesa', 'pared']
    ordering = ['genus', 'species', 'vivero', 'mesa', 'pared']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Botánica', {
            'fields': ('genus', 'species')
        }),
        ('Ubicación', {
            'fields': ('vivero', 'mesa', 'pared')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PollinationType)
class PollinationTypeAdmin(admin.ModelAdmin):
    """Admin configuration for PollinationType model."""
    list_display = ['name', 'get_name_display', 'requires_father_plant', 'allows_different_species', 'maturation_days']
    list_filter = ['name', 'requires_father_plant', 'allows_different_species']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description')
        }),
        ('Configuración', {
            'fields': ('requires_father_plant', 'allows_different_species', 'maturation_days')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ClimateCondition)
class ClimateConditionAdmin(admin.ModelAdmin):
    """Admin configuration for ClimateCondition model."""
    list_display = ['weather', 'temperature', 'humidity', 'wind_speed', 'created_at']
    list_filter = ['weather', 'created_at']
    search_fields = ['weather', 'notes']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Condiciones Climáticas', {
            'fields': ('weather', 'temperature', 'humidity', 'wind_speed')
        }),
        ('Observaciones', {
            'fields': ('notes',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PollinationRecord)
class PollinationRecordAdmin(admin.ModelAdmin):
    """Admin configuration for PollinationRecord model."""
    list_display = [
        'pollination_date', 'responsible', 'pollination_type', 
        'mother_plant', 'father_plant', 'capsules_quantity', 
        'maturation_confirmed', 'created_at'
    ]
    list_filter = [
        'pollination_type', 'pollination_date', 'maturation_confirmed', 
        'is_successful', 'responsible', 'created_at'
    ]
    search_fields = [
        'responsible__username', 'mother_plant__genus', 'mother_plant__species',
        'father_plant__genus', 'father_plant__species', 'observations'
    ]
    ordering = ['-pollination_date', '-created_at']
    readonly_fields = [
        'estimated_maturation_date', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'pollination_date'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('responsible', 'pollination_type', 'pollination_date')
        }),
        ('Plantas Involucradas', {
            'fields': ('mother_plant', 'father_plant', 'new_plant')
        }),
        ('Condiciones y Detalles', {
            'fields': ('climate_condition', 'capsules_quantity', 'observations')
        }),
        ('Seguimiento', {
            'fields': (
                'estimated_maturation_date', 'is_successful', 
                'maturation_confirmed', 'maturation_confirmed_date'
            )
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'responsible', 'pollination_type', 'mother_plant', 
            'father_plant', 'new_plant', 'climate_condition'
        )
