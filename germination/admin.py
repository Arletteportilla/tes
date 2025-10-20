from django.contrib import admin
from .models import (
    SeedSource, GerminationSetup, GerminationRecord
)
from core.models import ClimateCondition


@admin.register(SeedSource)
class SeedSourceAdmin(admin.ModelAdmin):
    """Admin configuration for SeedSource model."""
    list_display = [
        'name', 'source_type', 'external_supplier', 
        'collection_date', 'is_active', 'created_at'
    ]
    list_filter = ['source_type', 'is_active', 'collection_date', 'created_at']
    search_fields = ['name', 'description', 'external_supplier']
    ordering = ['-created_at', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'source_type', 'description')
        }),
        ('Origen Interno', {
            'fields': ('pollination_record',),
            'classes': ('collapse',)
        }),
        ('Origen Externo', {
            'fields': ('external_supplier', 'collection_date'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('pollination_record')


@admin.register(GerminationSetup)
class GerminationSetupAdmin(admin.ModelAdmin):
    """Admin configuration for GerminationSetup model."""
    list_display = [
        'climate_display', 'temperature_range', 'created_at'
    ]
    list_filter = ['climate_condition__climate', 'created_at']
    search_fields = ['setup_notes']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'temperature_range', 'climate_description']
    
    fieldsets = (
        ('Condición Climática', {
            'fields': ('climate_condition', 'temperature_range', 'climate_description')
        }),
        ('Detalles Adicionales', {
            'fields': ('setup_notes',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def climate_display(self, obj):
        """Display climate name in admin."""
        return obj.climate_display
    climate_display.short_description = "Clima"
    
    def temperature_range(self, obj):
        """Display temperature range in admin."""
        return obj.temperature_range
    temperature_range.short_description = "Rango de Temperatura"


@admin.register(GerminationRecord)
class GerminationRecordAdmin(admin.ModelAdmin):
    """Admin configuration for GerminationRecord model."""
    list_display = [
        'germination_date', 'responsible', 'plant', 'seed_source',
        'seeds_planted', 'seedlings_germinated', 'germination_rate',
        'transplant_status', 'transplant_confirmed', 'created_at'
    ]
    list_filter = [
        'germination_date', 'transplant_confirmed', 'is_successful',
        'responsible', 'plant__genus', 'plant__species', 'created_at'
    ]
    search_fields = [
        'responsible__username', 'plant__genus', 'plant__species',
        'seed_source__name', 'observations'
    ]
    ordering = ['-germination_date', '-created_at']
    readonly_fields = [
        'estimated_transplant_date', 'germination_rate', 'transplant_status',
        'days_to_transplant', 'is_transplant_overdue', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'germination_date'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('responsible', 'germination_date', 'plant')
        }),
        ('Origen y Condiciones', {
            'fields': ('seed_source', 'germination_setup')
        }),
        ('Cantidades', {
            'fields': ('seeds_planted', 'seedlings_germinated', 'transplant_days')
        }),
        ('Seguimiento de Trasplante', {
            'fields': (
                'estimated_transplant_date', 'transplant_confirmed', 
                'transplant_confirmed_date', 'is_successful'
            )
        }),
        ('Métricas Calculadas', {
            'fields': (
                'germination_rate', 'transplant_status', 
                'days_to_transplant', 'is_transplant_overdue'
            ),
            'classes': ('collapse',)
        }),
        ('Observaciones', {
            'fields': ('observations',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'responsible', 'plant', 'seed_source', 'germination_setup'
        )
    
    def germination_rate(self, obj):
        """Display germination rate in admin."""
        try:
            return f"{obj.germination_rate()}%"
        except (TypeError, ZeroDivisionError, AttributeError):
            return "N/A"
    germination_rate.short_description = "Tasa de Germinación"
    
    def transplant_status(self, obj):
        """Display transplant status in admin."""
        try:
            status_map = {
                'pending': '⏳ Pendiente',
                'approaching': '⚠️ Próximo',
                'overdue': '🔴 Vencido',
                'confirmed': '✅ Confirmado',
                'unknown': '❓ Desconocido'
            }
            return status_map.get(obj.transplant_status, obj.transplant_status)
        except (AttributeError, TypeError):
            return "❓ Desconocido"
    transplant_status.short_description = "Estado de Trasplante"
    
    def days_to_transplant(self, obj):
        """Display days to transplant in admin."""
        try:
            days = obj.days_to_transplant()
            if days is None:
                return "N/A"
            elif days < 0:
                return f"{abs(days)} días vencido"
            else:
                return f"{days} días restantes"
        except (AttributeError, TypeError):
            return "N/A"
    days_to_transplant.short_description = "Días para Trasplante"
    
    def is_transplant_overdue(self, obj):
        """Display overdue status in admin."""
        try:
            return "🔴 Sí" if obj.is_transplant_overdue() else "✅ No"
        except (AttributeError, TypeError):
            return "❓ N/A"
    is_transplant_overdue.short_description = "¿Vencido?"
