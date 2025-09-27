from django.contrib import admin
from .models import SeedSource, GerminationCondition, GerminationRecord


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


@admin.register(GerminationCondition)
class GerminationConditionAdmin(admin.ModelAdmin):
    """Admin configuration for GerminationCondition model."""
    list_display = [
        'climate', 'substrate', 'location', 'temperature', 
        'humidity', 'light_hours', 'created_at'
    ]
    list_filter = ['climate', 'substrate', 'created_at']
    search_fields = ['location', 'substrate_details', 'notes']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Condiciones Básicas', {
            'fields': ('climate', 'substrate', 'location')
        }),
        ('Parámetros Ambientales', {
            'fields': ('temperature', 'humidity', 'light_hours')
        }),
        ('Detalles Adicionales', {
            'fields': ('substrate_details', 'notes')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


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
            'fields': ('seed_source', 'germination_condition')
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
            'responsible', 'plant', 'seed_source', 'germination_condition'
        )
    
    def germination_rate(self, obj):
        """Display germination rate in admin."""
        return f"{obj.germination_rate()}%"
    germination_rate.short_description = "Tasa de Germinación"
    
    def transplant_status(self, obj):
        """Display transplant status in admin."""
        status_map = {
            'pending': '⏳ Pendiente',
            'approaching': '⚠️ Próximo',
            'overdue': '🔴 Vencido',
            'confirmed': '✅ Confirmado',
            'unknown': '❓ Desconocido'
        }
        return status_map.get(obj.transplant_status, obj.transplant_status)
    transplant_status.short_description = "Estado de Trasplante"
    
    def days_to_transplant(self, obj):
        """Display days to transplant in admin."""
        days = obj.days_to_transplant()
        if days is None:
            return "N/A"
        elif days < 0:
            return f"{abs(days)} días vencido"
        else:
            return f"{days} días restantes"
    days_to_transplant.short_description = "Días para Trasplante"
    
    def is_transplant_overdue(self, obj):
        """Display overdue status in admin."""
        return "🔴 Sí" if obj.is_transplant_overdue() else "✅ No"
    is_transplant_overdue.short_description = "¿Vencido?"
